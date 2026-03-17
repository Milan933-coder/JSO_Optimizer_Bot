# =============================================================================
# routes/talentscout_chat.py
# TalentScout â€” Chat Route (multi-provider)
# provider + api_key flow from frontend â†’ route â†’ ai_service
# =============================================================================

import base64
import uuid
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from models.schemas import (
    StartRequest,
    StartResponse,
    MessageRequest,
    MessageResponse,
    VoiceMessageResponse,
    CVIntakeResponse,
)
from services.conversation_manager import (
    get_or_create_session,
    delete_session,
    ConversationPhase,
)
from services.ai_service import (
    chat_completion,
    json_completion,
    transcribe_audio_whisper,
    synthesize_speech_elevenlabs,
    extract_text_from_pdf_bytes,
    summarize_cv_text_with_model,
)
from services.recommendation_service import (
    is_recommendation_request,
    generate_recommendations_from_github,
)
from prompts.talentscout_prompts import (
    GREETING_MESSAGE,
    INFO_COLLECTION_SYSTEM_PROMPT,
    INFO_NOT_PROVIDED_RESPONSE,
    SESSION_TERMINATED_MESSAGE,
    VOLUNTARY_EXIT_MESSAGE,
    build_interview_system_prompt,
    build_interview_opener,
    build_closing_message,
    build_question_generation_prompt,
    is_exit_intent,
)

router = APIRouter()


DEFAULT_ELEVENLABS_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"
DEFAULT_ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"


# â”€â”€â”€ /start â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/start", response_model=StartResponse)
async def start_session(request: StartRequest):
    """
    Create a new session. Frontend sends provider + api_key once here.
    Returns session_id + greeting message.
    """
    # Validate key works by making a tiny test call
    try:
        await chat_completion(
            provider      = request.provider,
            api_key       = request.api_key,
            system_prompt = "You are a helpful assistant.",
            messages      = [{"role": "user", "content": "Say OK"}],
            max_tokens    = 5,
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid API key or provider error: {str(e)}"
        )

    session_id = str(uuid.uuid4())
    session    = get_or_create_session(session_id)
    session.add_message("assistant", GREETING_MESSAGE)

    return StartResponse(
        session_id = session_id,
        reply      = GREETING_MESSAGE,
        phase      = session.phase.value,
    )


# â”€â”€â”€ /message â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _strip_llm_question(text: str) -> str:
    """
    Removes any question the LLM added to its acknowledgement.
    We only keep sentences that do NOT end with '?'
    """
    import re
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    
    # Keep only non-question sentences
    filtered = [s for s in sentences if not s.strip().endswith("?")]
    
    # If everything got stripped, keep the first sentence as fallback
    if not filtered:
        filtered = [sentences[0]] if sentences else ["Good answer!"]
    
    return " ".join(filtered).strip()
                                 
@router.post("/message", response_model=MessageResponse)
async def chat(request: MessageRequest):
    """
    Main message handler. provider + api_key sent every request.
    """
    session    = get_or_create_session(request.session_id)
    user_msg   = request.message
    provider   = request.provider
    api_key    = request.api_key

    # â”€â”€ Guard: closed session â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if session.phase == ConversationPhase.CLOSED:
        return MessageResponse(
            session_id = request.session_id,
            reply      = "This session has ended. Please start a new session.",
            phase      = session.phase.value,
            is_closed  = True,
        )

    # â”€â”€ Voluntary exit â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if is_exit_intent(user_msg):
        session.close("voluntary_exit")
        session.add_message("user",      user_msg)
        session.add_message("assistant", VOLUNTARY_EXIT_MESSAGE)
        delete_session(request.session_id)
        return MessageResponse(
            session_id = request.session_id,
            reply      = VOLUNTARY_EXIT_MESSAGE,
            phase      = session.phase.value,
            is_closed  = True,
        )

    # Recommendation tool: use crawler_agent + selected LLM provider
    if is_recommendation_request(user_msg):
        session.add_message("user", user_msg)
        try:
            recommendation_reply = await generate_recommendations_from_github(
                user_message=user_msg,
                provider=provider,
                api_key=api_key,
            )
        except ValueError as e:
            recommendation_reply = str(e)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Recommendation tool failed: {e}")

        session.add_message("assistant", recommendation_reply)
        return MessageResponse(
            session_id=request.session_id,
            reply=recommendation_reply,
            phase=session.phase.value,
            is_closed=session.phase == ConversationPhase.CLOSED,
        )

    session.add_message("user", user_msg)

    # =========================================================================
    # PHASE 0 â€” Collect candidate info
    # =========================================================================
    if session.phase == ConversationPhase.INFO_PENDING:
        try:
            raw_reply, _ = await chat_completion(
                provider      = provider,
                api_key       = api_key,
                system_prompt = INFO_COLLECTION_SYSTEM_PROMPT,
                messages      = session.get_history(),
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))

        markers     = session.parse_markers(raw_reply)
        clean_reply = session.strip_markers(raw_reply)

        if markers["info_token_enabled"]:
            session.enable_info_token()

            # Extract candidate fields
            try:
                info_dict = await json_completion(
                    provider      = provider,
                    api_key       = api_key,
                    system_prompt = _EXTRACTION_PROMPT,
                    user_message  = "Extract the candidate info from the conversation above: "
                                    + str(session.get_history()),
                )
                _populate_candidate(session, info_dict)
            except Exception:
                pass

            # Generate questions
            try:
                q_result = await json_completion(
                    provider      = provider,
                    api_key       = api_key,
                    system_prompt = build_question_generation_prompt(
                        tech_stack       = session.candidate.tech_stack or "general software",
                        experience_years = session.candidate.years_experience or "unknown",
                        position         = session.candidate.desired_position or "tech role",
                    ),
                    user_message  = "Generate the interview questions now.",
                )
                session.start_interview(q_result.get("questions", []))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Question generation failed: {e}")

            opener      = build_interview_opener(session.candidate.to_dict())
            first_q     = session.get_current_question()
            first_q_txt = f"\n\n{first_q.question}" if first_q else ""
            final_reply = f"{clean_reply}\n\n{opener}{first_q_txt}"

        else:
            final_reply = clean_reply if len(user_msg) >= 5 else INFO_NOT_PROVIDED_RESPONSE

        session.add_message("assistant", final_reply)
        return MessageResponse(
            session_id = request.session_id,
            reply      = final_reply,
            phase      = session.phase.value,
        )

    # =========================================================================
    # PHASE 1 â€” Technical interview
    # =========================================================================
    if session.phase == ConversationPhase.INTERVIEWING:
        current_q = session.get_current_question()
        if not current_q:
            closing = build_closing_message(session.candidate.to_dict())
            session.close("completed")
            session.add_message("assistant", closing)
            delete_session(request.session_id)
            return MessageResponse(
                session_id = request.session_id,
                reply      = closing,
                phase      = session.phase.value,
                is_closed  = True,
            )

        try:
            raw_reply, _ = await chat_completion(
                provider      = provider,
                api_key       = api_key,
                system_prompt = build_interview_system_prompt(
                    candidate_info  = session.candidate.to_dict(),
                    deviation_count = session.deviation_count,
                ),
                messages      = session.get_history(),
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))

        markers     = session.parse_markers(raw_reply)
        clean_reply = session.strip_markers(raw_reply)

        # Deviation
        if markers["deviation_count"] is not None:
            session.record_deviation()
            if session.is_deviation_limit_reached() or markers["session_terminated"]:
                session.close("deviation_limit")
                session.add_message("assistant", SESSION_TERMINATED_MESSAGE)
                delete_session(request.session_id)
                return MessageResponse(
                    session_id = request.session_id,
                    reply      = SESSION_TERMINATED_MESSAGE,
                    phase      = session.phase.value,
                    is_closed  = True,
                )
            session.add_message("assistant", clean_reply)
            return MessageResponse(
                session_id = request.session_id,
                reply      = clean_reply,
                phase      = session.phase.value,
            )

        # Interview complete
        if markers["interview_complete"] or session.all_questions_answered():
            session.advance_question()
            closing     = build_closing_message(session.candidate.to_dict())
            final_reply = f"{clean_reply}\n\n{closing}"
            session.close("completed")
            session.add_message("assistant", final_reply)
            delete_session(request.session_id)
            return MessageResponse(
                session_id = request.session_id,
                reply      = final_reply,
                phase      = session.phase.value,
                is_closed  = True,
            )

        # Normal answer â†’ next question
        session.advance_question()
        next_q = session.get_current_question()

        # âœ… Strip any question the LLM sneaked into its reply
        clean_reply = _strip_llm_question(clean_reply)

        if next_q:
            final_reply = f"{clean_reply}\n\n---\n{next_q.question}"
        else:
            closing     = build_closing_message(session.candidate.to_dict())
            final_reply = f"{clean_reply}\n\n{closing}"
            session.close("completed")
            delete_session(request.session_id)
        session.add_message("assistant", final_reply)
        return MessageResponse(
            session_id = request.session_id,
            reply      = final_reply,
            phase      = session.phase.value,
            is_closed  = session.phase == ConversationPhase.CLOSED,
        )

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
    """
    Voice flow:
    1) Transcribe user audio via Whisper (OpenAI)
    2) Send transcript through the existing chat/session logic
    3) Convert assistant reply to speech using ElevenLabs
    """
    try:
        audio_bytes = await audio_file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unable to read audio file: {e}")

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
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Whisper transcription failed: {e}")

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
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Model response failed: {e}")

    try:
        speech_bytes, speech_mime = await synthesize_speech_elevenlabs(
            elevenlabs_api_key=elevenlabs_api_key,
            text=chat_response.reply,
            voice_id=elevenlabs_voice_id,
            model_id=elevenlabs_model_id,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ElevenLabs TTS failed: {e}")

    return VoiceMessageResponse(
        session_id=chat_response.session_id,
        transcript=transcript,
        detected_language=detected_language,
        reply=chat_response.reply,
        phase=chat_response.phase,
        is_closed=chat_response.is_closed,
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
    """
    Accept CV as PDF, extract plain text, and convert it into a structured candidate
    profile. The parsed profile is then fed into the existing chat flow.
    """
    filename = (cv_file.filename or "").lower()
    content_type = (cv_file.content_type or "").lower()

    if not (filename.endswith(".pdf") or content_type == "application/pdf"):
        raise HTTPException(status_code=400, detail="Only PDF CV files are supported.")

    try:
        file_bytes = await cv_file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unable to read cv_file: {e}")

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
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CV parsing failed: {e}")

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
    )


# â”€â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_EXTRACTION_PROMPT = """
You are a data extractor. Read the conversation and extract candidate information.
Respond ONLY in this exact JSON format â€” use null for any field not found:
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
    c = session.candidate
    c.name             = info.get("name")             or c.name
    c.email            = info.get("email")            or c.email
    c.phone            = info.get("phone")            or c.phone
    c.years_experience = info.get("years_experience") or c.years_experience
    c.desired_position = info.get("desired_position") or c.desired_position
    c.location         = info.get("location")         or c.location
    c.tech_stack       = info.get("tech_stack")       or c.tech_stack

