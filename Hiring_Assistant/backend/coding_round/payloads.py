from __future__ import annotations

from typing import Any

from coding_round.constants import (
    CODING_ROUND_DURATION_MINUTES,
    get_language_payloads,
)


def serialize_coding_round(session: Any) -> dict[str, Any] | None:
    coding_round = getattr(session, "coding_round", None)
    if coding_round is None or not coding_round.problem:
        return None

    return {
        "status": coding_round.status,
        "is_active": session.phase.value == "CODING_ROUND" and not coding_round.completed and not coding_round.is_expired(),
        "is_completed": coding_round.completed,
        "time_limit_minutes": CODING_ROUND_DURATION_MINUTES,
        "max_attempts": coding_round.max_attempts,
        "attempts_used": coding_round.attempts_used,
        "attempts_left": coding_round.attempts_left(),
        "remaining_seconds": coding_round.remaining_seconds(),
        "started_at": coding_round.started_at.isoformat() if coding_round.started_at else None,
        "expires_at": coding_round.expires_at.isoformat() if coding_round.expires_at else None,
        "completion_reason": coding_round.completion_reason,
        "problem": {
            **coding_round.problem,
            "available_languages": get_language_payloads(),
        },
        "last_result": coding_round.last_result,
    }
