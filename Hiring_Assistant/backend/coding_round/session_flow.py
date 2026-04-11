from __future__ import annotations

from coding_round.codeforces_service import fetch_random_medium_problem
from coding_round.constants import (
    CODING_ROUND_DURATION_MINUTES,
    CODING_ROUND_MAX_ATTEMPTS,
)
from prompts.talentscout_prompts import (
    build_closing_message,
    build_coding_round_intro,
)


CODING_ROUND_START_KEYWORDS = (
    "start coding round",
    "start dsa round",
    "start dsa",
    "begin coding round",
    "begin dsa round",
    "begin dsa",
    "open coding round",
    "open dsa round",
)


def is_start_coding_round_intent(message: str) -> bool:
    lowered = (message or "").strip().lower()
    return any(keyword in lowered for keyword in CODING_ROUND_START_KEYWORDS)


async def start_coding_round_for_session(session, acknowledgement: str) -> tuple[str, bool]:
    try:
        coding_problem = await fetch_random_medium_problem()
    except Exception:
        closing = build_closing_message(session.candidate.to_dict())
        fallback = "I wasn't able to load the coding round right now, so I'll wrap up the interview here."
        final_reply = "\n\n".join(part for part in [acknowledgement.strip(), fallback, closing] if part)
        session.close("completed")
        session.add_message("assistant", final_reply)
        return final_reply, True

    session.start_coding_round(
        coding_problem,
        duration_minutes=CODING_ROUND_DURATION_MINUTES,
        max_attempts=CODING_ROUND_MAX_ATTEMPTS,
    )
    intro = build_coding_round_intro(
        session.candidate.to_dict(),
        coding_problem,
        CODING_ROUND_DURATION_MINUTES,
        CODING_ROUND_MAX_ATTEMPTS,
    )
    final_reply = "\n\n".join(part for part in [acknowledgement.strip(), intro] if part)
    session.add_message("assistant", final_reply)
    return final_reply, False
