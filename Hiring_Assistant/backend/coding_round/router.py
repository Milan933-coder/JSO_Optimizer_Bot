from __future__ import annotations

from fastapi import APIRouter, HTTPException

from config import resolve_judge0_api_key, resolve_judge0_base_url
from coding_round.session_flow import start_coding_round_for_session
from coding_round.judge0_service import run_sample_case, submit_against_samples
from coding_round.payloads import serialize_coding_round
from models.schemas import (
    CodingRoundActionResponse,
    CodingRoundAttemptRequest,
    CodingRoundStartRequest,
    MessageResponse,
)
from prompts.talentscout_prompts import (
    build_coding_round_attempt_limit_message,
    build_coding_round_completion_message,
    build_coding_round_timeout_message,
)
from services.conversation_manager import ConversationPhase, delete_session, get_session
from services.interview_agents import append_final_assessment_to_reply

router = APIRouter()


def _require_session(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Please start a new session.",
        )
    return session


def _build_message_response(session_id: str, session, reply: str, is_closed: bool = False):
    return MessageResponse(
        session_id=session_id,
        reply=reply,
        phase=session.phase.value,
        is_closed=is_closed,
        coding_round=serialize_coding_round(session),
    )


def _build_action_response(session_id: str, session, action: str, result: dict, reply: str | None = None, is_closed: bool = False):
    return CodingRoundActionResponse(
        session_id=session_id,
        action=action,
        phase=session.phase.value,
        is_closed=is_closed,
        reply=reply,
        coding_round=serialize_coding_round(session),
        result=result,
    )


def _synthetic_result(action: str, verdict: str, total_samples: int = 0) -> dict:
    return {
        "mode": action,
        "passed": False,
        "verdict": verdict,
        "status_summary": verdict,
        "passed_samples": 0,
        "total_samples": total_samples,
        "sample_results": [],
    }


def _require_active_round(session):
    if session.phase != ConversationPhase.CODING_ROUND or not session.coding_round.problem:
        raise HTTPException(status_code=409, detail="No active coding round is available for this session.")
    if session.coding_round.completed:
        raise HTTPException(status_code=409, detail="This coding round has already ended.")


def _timeout_response(session, session_id: str, action: str) -> CodingRoundActionResponse:
    reply = append_final_assessment_to_reply(
        build_coding_round_timeout_message(session.candidate.to_dict()),
        session.final_interview_assessment,
    )
    result = _synthetic_result(action, "Coding round expired.", len((session.coding_round.problem or {}).get("samples", [])))
    session.finish_coding_round(status="expired", reason="coding_time_limit", close_session=True)
    session.add_message("assistant", reply)
    response = _build_action_response(session_id, session, action, result, reply=reply, is_closed=True)
    delete_session(session_id)
    return response


def _attempt_limit_response(session, session_id: str, action: str, result: dict) -> CodingRoundActionResponse:
    reply = append_final_assessment_to_reply(
        build_coding_round_attempt_limit_message(session.candidate.to_dict()),
        session.final_interview_assessment,
    )
    session.finish_coding_round(status="max_attempts_reached", reason="coding_max_attempts", close_session=True)
    session.add_message("assistant", reply)
    response = _build_action_response(session_id, session, action, result, reply=reply, is_closed=True)
    delete_session(session_id)
    return response


def _completion_response(session, session_id: str, action: str, result: dict) -> CodingRoundActionResponse:
    reply = append_final_assessment_to_reply(
        build_coding_round_completion_message(
            session.candidate.to_dict(),
            result.get("passed_samples", 0),
            result.get("total_samples", 0),
        ),
        session.final_interview_assessment,
    )
    session.finish_coding_round(status="accepted", reason="coding_completed", close_session=True)
    session.add_message("assistant", reply)
    response = _build_action_response(session_id, session, action, result, reply=reply, is_closed=True)
    delete_session(session_id)
    return response


@router.post("/start", response_model=MessageResponse)
async def start_coding_round(request: CodingRoundStartRequest):
    session = _require_session(request.session_id)

    if session.phase == ConversationPhase.CLOSED:
        raise HTTPException(status_code=409, detail="This session has already ended.")

    if session.phase == ConversationPhase.CODING_ROUND and session.coding_round.problem:
        return _build_message_response(
            request.session_id,
            session,
            "The coding round is already active. Please use the coding workspace.",
            is_closed=False,
        )

    if session.phase != ConversationPhase.INTERVIEWING:
        raise HTTPException(
            status_code=409,
            detail="The coding round can only be started after the technical interview begins.",
        )

    reply, should_close = await start_coding_round_for_session(
        session,
        "Starting the DSA round now.",
    )
    response = _build_message_response(
        request.session_id,
        session,
        reply,
        is_closed=should_close,
    )
    if should_close:
        delete_session(request.session_id)
    return response


@router.post("/run", response_model=CodingRoundActionResponse)
async def run_coding_round(request: CodingRoundAttemptRequest):
    session = _require_session(request.session_id)
    _require_active_round(session)

    if session.coding_round.is_expired():
        return _timeout_response(session, request.session_id, "run")
    if session.coding_round.attempts_left() <= 0:
        return _attempt_limit_response(
            session,
            request.session_id,
            "run",
            _synthetic_result("run", "No coding attempts remaining.", len(session.coding_round.problem.get("samples", []))),
        )

    samples = session.coding_round.problem.get("samples", [])
    if request.sample_index >= len(samples):
        raise HTTPException(status_code=400, detail="Requested sample index is out of range.")

    try:
        judge0_api_key = resolve_judge0_api_key(request.judge0_api_key)
        judge0_base_url = resolve_judge0_base_url(request.judge0_base_url)
        result = await run_sample_case(
            source_code=request.source_code,
            language_slug=request.language_slug,
            sample=samples[request.sample_index],
            sample_index=request.sample_index,
            judge0_api_key=judge0_api_key,
            judge0_base_url=judge0_base_url,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Judge0 execution failed: {exc}") from exc

    session.coding_round.record_attempt()
    session.coding_round.set_last_result(result)

    if session.coding_round.attempts_left() <= 0:
        return _attempt_limit_response(session, request.session_id, "run", result)

    return _build_action_response(request.session_id, session, "run", result)


@router.post("/submit", response_model=CodingRoundActionResponse)
async def submit_coding_round(request: CodingRoundAttemptRequest):
    session = _require_session(request.session_id)
    _require_active_round(session)

    if session.coding_round.is_expired():
        return _timeout_response(session, request.session_id, "submit")
    if session.coding_round.attempts_left() <= 0:
        return _attempt_limit_response(
            session,
            request.session_id,
            "submit",
            _synthetic_result("submit", "No coding attempts remaining.", len(session.coding_round.problem.get("samples", []))),
        )

    try:
        judge0_api_key = resolve_judge0_api_key(request.judge0_api_key)
        judge0_base_url = resolve_judge0_base_url(request.judge0_base_url)
        result = await submit_against_samples(
            source_code=request.source_code,
            language_slug=request.language_slug,
            samples=session.coding_round.problem.get("samples", []),
            judge0_api_key=judge0_api_key,
            judge0_base_url=judge0_base_url,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Judge0 submission failed: {exc}") from exc

    session.coding_round.record_attempt()
    session.coding_round.set_last_result(result)

    if result.get("passed"):
        return _completion_response(session, request.session_id, "submit", result)
    if session.coding_round.attempts_left() <= 0:
        return _attempt_limit_response(session, request.session_id, "submit", result)

    return _build_action_response(request.session_id, session, "submit", result)
