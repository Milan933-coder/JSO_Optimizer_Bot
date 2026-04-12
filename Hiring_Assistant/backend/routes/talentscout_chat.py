# =============================================================================
# routes/talentscout_chat.py
# TalentScout - Chat Route (multi-provider)
# =============================================================================

import base64
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from config import (
    get_public_runtime_config,
    resolve_elevenlabs_api_key,
    resolve_elevenlabs_model_id,
    resolve_elevenlabs_voice_id,
    resolve_provider_api_key,
    resolve_whisper_api_key,
)
from coding_round.payloads import serialize_coding_round
from coding_round.session_flow import (
    is_start_coding_round_intent,
    start_coding_round_for_session,
)
from models.schemas import (
    CandidateInfoRequest,
    CVIntakeResponse,
    MessageRequest,
    MessageResponse,
    StopSessionRequest,
    StartRequest,
    StartResponse,
    VoiceMessageResponse,
)
from prompts.talentscout_prompts import (
    GREETING_MESSAGE,
    INFO_NOT_PROVIDED_RESPONSE,
    SESSION_TERMINATED_MESSAGE,
    VOLUNTARY_EXIT_MESSAGE,
    build_closing_message,
    build_coding_round_reminder,
    build_coding_round_timeout_message,
    build_deviation_warning,
    build_interview_opener,
)
from services.ai_service import chat_completion, extract_text_from_pdf_bytes, summarize_cv_text_with_model, synthesize_speech_elevenlabs, transcribe_audio_whisper
from services.conversation_manager import (
    ConversationPhase,
    create_session,
    delete_session,
    get_session,
)
from services.interview_agents import (
    append_final_assessment_to_reply,
    format_final_assessment_markdown,
    format_question_review_markdown,
    generate_interview_questions,
    review_interview_answer,
    summarize_interview_assessment,
)
from services.recommendation_service import (
    generate_recommendations_from_github,
    is_recommendation_request,
)

router = APIRouter()


def _require_session(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Please start a new session.",
        )
    return session


@router.get("/config")
async def get_runtime_config():
    return get_public_runtime_config()


@router.post("/start", response_model=StartResponse)
async def start_session(request: StartRequest):
    try:
        effective_api_key = resolve_provider_api_key(request.provider, request.api_key)
        await chat_completion(
            provider=request.provider,
            api_key=effective_api_key,
            system_prompt="You are a helpful assistant.",
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=5,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid API key or provider error: {str(exc)}",
        ) from exc

    session_id = str(uuid.uuid4())
    session = create_session(session_id)
    session.add_message("assistant", GREETING_MESSAGE)

    return StartResponse(
        session_id=session_id,
        reply=GREETING_MESSAGE,
        phase=session.phase.value,
        coding_round=None,
    )

def _build_message_response(session_id: str, session, reply: str, is_closed: bool | None = None) -> MessageResponse:
    return MessageResponse(
        session_id=session_id,
        reply=reply,
        phase=session.phase.value,
        is_closed=session.phase == ConversationPhase.CLOSED if is_closed is None else is_closed,
        coding_round=serialize_coding_round(session),
    )


def _expire_coding_round_if_needed(session, session_id: str) -> MessageResponse | None:
    if session.phase != ConversationPhase.CODING_ROUND:
        return None
    if not session.coding_round.problem or not session.coding_round.is_expired():
        return None

    timeout_reply = build_coding_round_timeout_message(session.candidate.to_dict())
    session.finish_coding_round(
        status="expired",
        reason="coding_time_limit",
        close_session=True,
    )
    session.add_message("assistant", timeout_reply)
    response = _build_message_response(session_id, session, timeout_reply, is_closed=True)
    delete_session(session_id)
    return response


async def _start_coding_round(session, session_id: str, acknowledgement: str) -> MessageResponse:
    final_reply, should_close = await start_coding_round_for_session(session, acknowledgement)
    response = _build_message_response(session_id, session, final_reply, is_closed=should_close)
    if should_close:
        delete_session(session_id)
    return response


def _stop_session(session_id: str, session, reply: str) -> MessageResponse:
    if session.phase == ConversationPhase.CODING_ROUND and session.coding_round.problem and not session.coding_round.completed:
        session.finish_coding_round(
            status="stopped",
            reason="manual_stop",
            close_session=False,
        )

    session.close("manual_stop")
    session.add_message("assistant", reply)
    response = MessageResponse(
        session_id=session_id,
        reply=reply,
        phase=session.phase.value,
        is_closed=True,
        coding_round=None,
    )
    delete_session(session_id)
    return response


def _candidate_summary_text(candidate_info: dict) -> str:
    return (
        "Candidate profile submitted via form:\n"
        f"- Full Name: {candidate_info.get('name', '')}\n"
        f"- Email Address: {candidate_info.get('email', '')}\n"
        f"- Phone Number: {candidate_info.get('phone', '')}\n"
        f"- Years of Experience: {candidate_info.get('years_experience', '')}\n"
        f"- Desired Position(s): {candidate_info.get('desired_position', '')}\n"
        f"- Current Location: {candidate_info.get('location', '')}\n"
        f"- Tech Stack: {candidate_info.get('tech_stack', '')}"
    )


async def _prepare_interview_from_candidate_info(session, provider: str, api_key: str) -> str:
    session.enable_info_token()

    try:
        questions = await generate_interview_questions(
            provider=provider,
            api_key=api_key,
            candidate_info=session.candidate.to_dict(),
        )
        session.start_interview(questions)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Question generation failed: {exc}") from exc

    opener = build_interview_opener(session.candidate.to_dict())
    first_question = session.get_current_question()
    first_question_text = f"\n\n{first_question.question}" if first_question else ""
    return f"{opener}{first_question_text}"


@router.post("/candidate-info", response_model=MessageResponse)
async def submit_candidate_info(request: CandidateInfoRequest):
    session = _require_session(request.session_id)
    try:
        effective_api_key = resolve_provider_api_key(request.provider, request.api_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if session.phase == ConversationPhase.CLOSED:
        return MessageResponse(
            session_id=request.session_id,
            reply="This session has ended. Please start a new session.",
            phase=session.phase.value,
            is_closed=True,
            coding_round=serialize_coding_round(session),
        )

    if session.phase != ConversationPhase.INFO_PENDING:
        raise HTTPException(status_code=409, detail="Candidate details have already been submitted for this session.")

    _populate_candidate(
        session,
        {
            "name": request.name,
            "email": request.email,
            "phone": request.phone,
            "years_experience": request.years_experience,
            "desired_position": request.desired_position,
            "location": request.location,
            "tech_stack": request.tech_stack,
        },
    )

    if not session.candidate.is_complete():
        raise HTTPException(status_code=422, detail="All candidate fields are required.")

    session.add_message("user", _candidate_summary_text(session.candidate.to_dict()))
    final_reply = await _prepare_interview_from_candidate_info(session, request.provider, effective_api_key)
    session.add_message("assistant", final_reply)
    return _build_message_response(request.session_id, session, final_reply)


@router.post("/stop", response_model=MessageResponse)
async def stop_session(request: StopSessionRequest):
    session = _require_session(request.session_id)

    if session.phase == ConversationPhase.CLOSED:
        return MessageResponse(
            session_id=request.session_id,
            reply="This session has already ended. Please start a new session if you want to continue.",
            phase=session.phase.value,
            is_closed=True,
            coding_round=None,
        )

    return _stop_session(request.session_id, session, VOLUNTARY_EXIT_MESSAGE)


@router.post("/message", response_model=MessageResponse)
async def chat(request: MessageRequest):
    session = _require_session(request.session_id)
    user_msg = request.message
    provider = request.provider
    try:
        api_key = resolve_provider_api_key(provider, request.api_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if session.phase == ConversationPhase.CLOSED:
        return MessageResponse(
            session_id=request.session_id,
            reply="This session has ended. Please start a new session.",
            phase=session.phase.value,
            is_closed=True,
            coding_round=serialize_coding_round(session),
        )

    if is_start_coding_round_intent(user_msg):
        session.add_message("user", user_msg)

        if session.phase == ConversationPhase.CODING_ROUND and session.coding_round.problem:
            reminder = build_coding_round_reminder(
                session.coding_round.problem,
                session.coding_round.attempts_left(),
                session.coding_round.remaining_seconds(),
            )
            session.add_message("assistant", reminder)
            return _build_message_response(request.session_id, session, reminder)

        if session.phase != ConversationPhase.INTERVIEWING:
            guidance = "The DSA round becomes available once the technical interview has started."
            session.add_message("assistant", guidance)
            return _build_message_response(request.session_id, session, guidance)

        return await _start_coding_round(
            session,
            request.session_id,
            "Understood. I'll start the DSA round now.",
        )

    if session.phase == ConversationPhase.CODING_ROUND:
        session.add_message("user", user_msg)
        timeout_response = _expire_coding_round_if_needed(session, request.session_id)
        if timeout_response is not None:
            return timeout_response

        reminder = build_coding_round_reminder(
            session.coding_round.problem or {},
            session.coding_round.attempts_left(),
            session.coding_round.remaining_seconds(),
        )
        session.add_message("assistant", reminder)
        return _build_message_response(request.session_id, session, reminder)

    if is_recommendation_request(user_msg):
        session.add_message("user", user_msg)
        try:
            recommendation_reply = await generate_recommendations_from_github(
                user_message=user_msg,
                provider=provider,
                api_key=api_key,
            )
        except ValueError as exc:
            recommendation_reply = str(exc)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Recommendation tool failed: {exc}") from exc

        session.add_message("assistant", recommendation_reply)
        return _build_message_response(request.session_id, session, recommendation_reply)

    session.add_message("user", user_msg)

    if session.phase == ConversationPhase.INFO_PENDING:
        final_reply = INFO_NOT_PROVIDED_RESPONSE
        session.add_message("assistant", final_reply)
        return _build_message_response(request.session_id, session, final_reply)

    if session.phase == ConversationPhase.INTERVIEWING:
        current_question = session.get_current_question()
        if not current_question:
            closing = append_final_assessment_to_reply(
                build_closing_message(session.candidate.to_dict()),
                session.final_interview_assessment,
            )
            session.close("completed")
            session.add_message("assistant", closing)
            response = _build_message_response(request.session_id, session, closing, is_closed=True)
            delete_session(request.session_id)
            return response

        try:
            review_payload = await review_interview_answer(
                provider=provider,
                api_key=api_key,
                question=current_question,
                answer=user_msg,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        if review_payload.get("is_deviation") or not review_payload.get("answered_question"):
            deviation_number = session.record_deviation()
            if session.is_deviation_limit_reached():
                session.close("deviation_limit")
                session.add_message("assistant", SESSION_TERMINATED_MESSAGE)
                response = _build_message_response(
                    request.session_id,
                    session,
                    SESSION_TERMINATED_MESSAGE,
                    is_closed=True,
                )
                delete_session(request.session_id)
                return response

            warning = review_payload.get("redirect_message", "").strip() or build_deviation_warning(
                deviation_number,
                current_question.question,
            )
            session.add_message("assistant", warning)
            return _build_message_response(request.session_id, session, warning)

        answer_review = session.record_answer_review(user_msg, review_payload)
        session.advance_question()
        next_question = session.get_current_question()
        review_reply = format_question_review_markdown(answer_review) if answer_review else "Thanks for the answer."

        if next_question:
            final_reply = f"{review_reply}\n\n---\n{next_question.question}"
            session.add_message("assistant", final_reply)
            return _build_message_response(request.session_id, session, final_reply)

        final_assessment_text = ""
        try:
            final_assessment_payload = await summarize_interview_assessment(
                provider=provider,
                api_key=api_key,
                candidate_info=session.candidate.to_dict(),
                questions=session.questions,
            )
            session.set_final_interview_assessment(final_assessment_payload)
            final_assessment_text = format_final_assessment_markdown(session.final_interview_assessment)
        except Exception:
            final_assessment_text = ""

        acknowledgement = "\n\n".join(part for part in [review_reply, final_assessment_text] if part)
        return await _start_coding_round(session, request.session_id, acknowledgement)

    raise HTTPException(status_code=500, detail="Unknown session state")


@router.post("/voice-message", response_model=VoiceMessageResponse)
async def voice_chat(
    session_id: str = Form(...),
    provider: str = Form(...),
    api_key: str | None = Form(default=None),
    elevenlabs_api_key: str | None = Form(default=None),
    audio_file: UploadFile = File(...),
    whisper_api_key: str | None = Form(default=None),
    elevenlabs_voice_id: str | None = Form(default=None),
    elevenlabs_model_id: str | None = Form(default=None),
):
    try:
        audio_bytes = await audio_file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to read audio file: {exc}") from exc

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="audio_file is empty")

    try:
        effective_provider_key = resolve_provider_api_key(provider, api_key)
        effective_whisper_key = resolve_whisper_api_key(
            provider,
            whisper_api_key,
            api_key,
        )
        effective_elevenlabs_key = resolve_elevenlabs_api_key(elevenlabs_api_key)
        effective_voice_id = resolve_elevenlabs_voice_id(elevenlabs_voice_id)
        effective_model_id = resolve_elevenlabs_model_id(elevenlabs_model_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        transcript, detected_language = await transcribe_audio_whisper(
            openai_api_key=effective_whisper_key,
            audio_bytes=audio_bytes,
            filename=audio_file.filename or "user-audio.webm",
            content_type=audio_file.content_type,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Whisper transcription failed: {exc}") from exc

    try:
        chat_response = await chat(
            MessageRequest(
                session_id=session_id,
                provider=provider,
                api_key=effective_provider_key,
                message=transcript,
            )
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model response failed: {exc}") from exc

    try:
        speech_bytes, speech_mime = await synthesize_speech_elevenlabs(
            elevenlabs_api_key=effective_elevenlabs_key,
            text=chat_response.reply,
            voice_id=effective_voice_id,
            model_id=effective_model_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ElevenLabs TTS failed: {exc}") from exc

    return VoiceMessageResponse(
        session_id=chat_response.session_id,
        transcript=transcript,
        detected_language=detected_language,
        reply=chat_response.reply,
        phase=chat_response.phase,
        is_closed=chat_response.is_closed,
        coding_round=chat_response.coding_round,
        voice_id=effective_voice_id,
        audio_mime_type=speech_mime,
        audio_base64=base64.b64encode(speech_bytes).decode("ascii"),
    )


@router.post("/cv-intake", response_model=CVIntakeResponse)
async def cv_intake(
    session_id: str = Form(...),
    provider: str = Form(...),
    api_key: str | None = Form(default=None),
    cv_file: UploadFile = File(...),
):
    filename = (cv_file.filename or "").lower()
    content_type = (cv_file.content_type or "").lower()

    if not (filename.endswith(".pdf") or content_type == "application/pdf"):
        raise HTTPException(status_code=400, detail="Only PDF CV files are supported.")

    try:
        file_bytes = await cv_file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to read cv_file: {exc}") from exc

    if not file_bytes:
        raise HTTPException(status_code=400, detail="cv_file is empty.")

    try:
        effective_api_key = resolve_provider_api_key(provider, api_key)
        extracted_text = extract_text_from_pdf_bytes(file_bytes)
        if not extracted_text:
            raise HTTPException(status_code=422, detail="Could not extract text from PDF CV.")
        profile_text = await summarize_cv_text_with_model(
            provider=provider,
            api_key=effective_api_key,
            cv_text=extracted_text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"CV parsing failed: {exc}") from exc

    if not profile_text.strip():
        raise HTTPException(status_code=422, detail="Model returned empty CV profile.")

    chat_response = await chat(
        MessageRequest(
            session_id=session_id,
            provider=provider,
            api_key=effective_api_key,
            message=profile_text.strip(),
        )
    )

    return CVIntakeResponse(
        session_id=chat_response.session_id,
        extracted_profile=profile_text.strip(),
        reply=chat_response.reply,
        phase=chat_response.phase,
        is_closed=chat_response.is_closed,
        coding_round=chat_response.coding_round,
    )

def _populate_candidate(session, info: dict):
    candidate = session.candidate
    candidate.name = info.get("name") or candidate.name
    candidate.email = info.get("email") or candidate.email
    candidate.phone = info.get("phone") or candidate.phone
    candidate.years_experience = info.get("years_experience") or candidate.years_experience
    candidate.desired_position = info.get("desired_position") or candidate.desired_position
    candidate.location = info.get("location") or candidate.location
    candidate.tech_stack = info.get("tech_stack") or candidate.tech_stack
