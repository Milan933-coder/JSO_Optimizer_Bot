# =============================================================================
# routes/talentscout_chat.py
# TalentScout - Chat Route (multi-provider)
# =============================================================================

import base64
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from coding_round.payloads import serialize_coding_round
from coding_round.session_flow import (
    is_start_coding_round_intent,
    start_coding_round_for_session,
)
from models.schemas import (
    CVIntakeResponse,
    MessageRequest,
    MessageResponse,
    StartRequest,
    StartResponse,
    VoiceMessageResponse,
)
from prompts.talentscout_prompts import (
    GREETING_MESSAGE,
    INFO_COLLECTION_SYSTEM_PROMPT,
    INFO_NOT_PROVIDED_RESPONSE,
    SESSION_TERMINATED_MESSAGE,
    VOLUNTARY_EXIT_MESSAGE,
    build_closing_message,
    build_coding_round_reminder,
    build_coding_round_timeout_message,
    build_interview_opener,
    build_interview_system_prompt,
    build_question_generation_prompt,
    is_exit_intent,
)
from services.ai_service import (
    chat_completion,
    extract_text_from_pdf_bytes,
    json_completion,
    summarize_cv_text_with_model,
    synthesize_speech_elevenlabs,
    transcribe_audio_whisper,
)
from services.conversation_manager import (
    ConversationPhase,
    delete_session,
    get_or_create_session,
)
from services.recommendation_service import (
    generate_recommendations_from_github,
    is_recommendation_request,
)

router = APIRouter()


DEFAULT_ELEVENLABS_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"
DEFAULT_ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"


@router.post("/start", response_model=StartResponse)
async def start_session(request: StartRequest):
    try:
        await chat_completion(
            provider=request.provider,
            api_key=request.api_key,
            system_prompt="You are a helpful assistant.",
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=5,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid API key or provider error: {str(exc)}",
        ) from exc

    session_id = str(uuid.uuid4())
    session = get_or_create_session(session_id)
    session.add_message("assistant", GREETING_MESSAGE)

    return StartResponse(
        session_id=session_id,
        reply=GREETING_MESSAGE,
        phase=session.phase.value,
        coding_round=None,
    )


def _strip_llm_question(text: str) -> str:
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    filtered = [sentence for sentence in sentences if not sentence.strip().endswith("?")]

    if not filtered:
        filtered = [sentences[0]] if sentences else ["Good answer!"]

    return " ".join(filtered).strip()


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


@router.post("/message", response_model=MessageResponse)
async def chat(request: MessageRequest):
    session = get_or_create_session(request.session_id)
    user_msg = request.message
    provider = request.provider
    api_key = request.api_key

    if session.phase == ConversationPhase.CLOSED:
        return MessageResponse(
            session_id=request.session_id,
            reply="This session has ended. Please start a new session.",
            phase=session.phase.value,
            is_closed=True,
            coding_round=serialize_coding_round(session),
        )

    if is_exit_intent(user_msg):
        session.close("voluntary_exit")
        session.add_message("user", user_msg)
        session.add_message("assistant", VOLUNTARY_EXIT_MESSAGE)
        response = _build_message_response(request.session_id, session, VOLUNTARY_EXIT_MESSAGE, is_closed=True)
        delete_session(request.session_id)
        return response

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
        try:
            raw_reply, _ = await chat_completion(
                provider=provider,
                api_key=api_key,
                system_prompt=INFO_COLLECTION_SYSTEM_PROMPT,
                messages=session.get_history(),
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        markers = session.parse_markers(raw_reply)
        clean_reply = session.strip_markers(raw_reply)

        if markers["info_token_enabled"]:
            session.enable_info_token()

            try:
                info_dict = await json_completion(
                    provider=provider,
                    api_key=api_key,
                    system_prompt=_EXTRACTION_PROMPT,
                    user_message="Extract the candidate info from the conversation above: "
                    + str(session.get_history()),
                )
                _populate_candidate(session, info_dict)
            except Exception:
                pass

            try:
                question_payload = await json_completion(
                    provider=provider,
                    api_key=api_key,
                    system_prompt=build_question_generation_prompt(
                        tech_stack=session.candidate.tech_stack or "general software",
                        experience_years=session.candidate.years_experience or "unknown",
                        position=session.candidate.desired_position or "tech role",
                    ),
                    user_message="Generate the interview questions now.",
                )
                session.start_interview(question_payload.get("questions", []))
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Question generation failed: {exc}") from exc

            opener = build_interview_opener(session.candidate.to_dict())
            first_question = session.get_current_question()
            first_question_text = f"\n\n{first_question.question}" if first_question else ""
            final_reply = f"{clean_reply}\n\n{opener}{first_question_text}"
        else:
            final_reply = clean_reply if len(user_msg) >= 5 else INFO_NOT_PROVIDED_RESPONSE

        session.add_message("assistant", final_reply)
        return _build_message_response(request.session_id, session, final_reply)

    if session.phase == ConversationPhase.INTERVIEWING:
        current_question = session.get_current_question()
        if not current_question:
            closing = build_closing_message(session.candidate.to_dict())
            session.close("completed")
            session.add_message("assistant", closing)
            response = _build_message_response(request.session_id, session, closing, is_closed=True)
            delete_session(request.session_id)
            return response

        try:
            raw_reply, _ = await chat_completion(
                provider=provider,
                api_key=api_key,
                system_prompt=build_interview_system_prompt(
                    candidate_info=session.candidate.to_dict(),
                    deviation_count=session.deviation_count,
                ),
                messages=session.get_history(),
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        markers = session.parse_markers(raw_reply)
        clean_reply = session.strip_markers(raw_reply)

        if markers["deviation_count"] is not None:
            session.record_deviation()
            if session.is_deviation_limit_reached() or markers["session_terminated"]:
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

            session.add_message("assistant", clean_reply)
            return _build_message_response(request.session_id, session, clean_reply)

        session.advance_question()
        next_question = session.get_current_question()
        clean_reply = _strip_llm_question(clean_reply)

        if next_question:
            final_reply = f"{clean_reply}\n\n---\n{next_question.question}"
            session.add_message("assistant", final_reply)
            return _build_message_response(request.session_id, session, final_reply)

        return await _start_coding_round(session, request.session_id, clean_reply)

    raise HTTPException(status_code=500, detail="Unknown session state")


@router.post("/voice-message", response_model=VoiceMessageResponse)
async def voice_chat(
    session_id: str = Form(...),
    provider: str = Form(...),
    api_key: str = Form(...),
    elevenlabs_api_key: str = Form(...),
    audio_file: UploadFile = File(...),
    whisper_api_key: str | None = Form(default=None),
    elevenlabs_voice_id: str = Form(default=DEFAULT_ELEVENLABS_VOICE_ID),
    elevenlabs_model_id: str = Form(default=DEFAULT_ELEVENLABS_MODEL_ID),
):
    try:
        audio_bytes = await audio_file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to read audio file: {exc}") from exc

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="audio_file is empty")

    effective_whisper_key = (whisper_api_key or api_key).strip()
    if not effective_whisper_key:
        raise HTTPException(
            status_code=400,
            detail="A Whisper/OpenAI API key is required (whisper_api_key or api_key).",
        )

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
                api_key=api_key,
                message=transcript,
            )
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model response failed: {exc}") from exc

    try:
        speech_bytes, speech_mime = await synthesize_speech_elevenlabs(
            elevenlabs_api_key=elevenlabs_api_key,
            text=chat_response.reply,
            voice_id=elevenlabs_voice_id,
            model_id=elevenlabs_model_id,
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
        voice_id=elevenlabs_voice_id,
        audio_mime_type=speech_mime,
        audio_base64=base64.b64encode(speech_bytes).decode("ascii"),
    )


@router.post("/cv-intake", response_model=CVIntakeResponse)
async def cv_intake(
    session_id: str = Form(...),
    provider: str = Form(...),
    api_key: str = Form(...),
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
        extracted_text = extract_text_from_pdf_bytes(file_bytes)
        if not extracted_text:
            raise HTTPException(status_code=422, detail="Could not extract text from PDF CV.")
        profile_text = await summarize_cv_text_with_model(
            provider=provider,
            api_key=api_key,
            cv_text=extracted_text,
        )
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
            api_key=api_key,
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


_EXTRACTION_PROMPT = """
You are a data extractor. Read the conversation and extract candidate information.
Respond ONLY in this exact JSON format - use null for any field not found:
{
  "name":             "<string or null>",
  "email":            "<string or null>",
  "phone":            "<string or null>",
  "years_experience": "<string or null>",
  "desired_position": "<string or null>",
  "location":         "<string or null>",
  "tech_stack":       "<comma-separated technologies or null>"
}
"""


def _populate_candidate(session, info: dict):
    candidate = session.candidate
    candidate.name = info.get("name") or candidate.name
    candidate.email = info.get("email") or candidate.email
    candidate.phone = info.get("phone") or candidate.phone
    candidate.years_experience = info.get("years_experience") or candidate.years_experience
    candidate.desired_position = info.get("desired_position") or candidate.desired_position
    candidate.location = info.get("location") or candidate.location
    candidate.tech_stack = info.get("tech_stack") or candidate.tech_stack
