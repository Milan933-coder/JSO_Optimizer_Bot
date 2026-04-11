from __future__ import annotations

from typing import Any

from prompts.talentscout_prompts import (
    build_answer_review_prompt,
    build_final_assessment_prompt,
    build_question_generation_prompt,
)
from services.ai_service import json_completion


def _clean_list(values: Any, *, limit: int = 4) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for value in values:
        text = str(value).strip()
        if text:
            cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def _score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(round(score, 1), 10.0))


def _normalize_question_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_questions = payload.get("questions")
    if not isinstance(raw_questions, list):
        return []

    normalized: list[dict[str, Any]] = []
    for index, raw_question in enumerate(raw_questions[:10], start=1):
        if not isinstance(raw_question, dict):
            continue

        question_text = str(raw_question.get("question", "")).strip()
        if not question_text:
            continue

        technology = str(raw_question.get("technology", "Declared stack")).strip() or "Declared stack"
        normalized.append(
            {
                "id": int(raw_question.get("id") or index),
                "technology": technology,
                "difficulty": str(raw_question.get("difficulty", "intermediate")).strip().lower() or "intermediate",
                "focus_area": str(raw_question.get("focus_area", technology)).strip() or technology,
                "question": question_text,
                "evaluation_rubric": _clean_list(raw_question.get("evaluation_rubric"), limit=4),
            }
        )

    return normalized


def _normalize_review_payload(payload: dict[str, Any]) -> dict[str, Any]:
    is_deviation = bool(payload.get("is_deviation"))
    answered_question = bool(payload.get("answered_question", not is_deviation))
    review_text = str(payload.get("review", "")).strip()
    technical_score = _score(payload.get("technical_score"))
    explanation_score = _score(payload.get("explanation_score"))
    communication_score = _score(payload.get("communication_score"))
    overall_score = _score(payload.get("overall_score"))
    if overall_score == 0 and not is_deviation:
        overall_score = round((technical_score + explanation_score + communication_score) / 3, 1)

    return {
        "answered_question": answered_question,
        "is_deviation": is_deviation,
        "redirect_message": str(payload.get("redirect_message", "")).strip(),
        "technical_score": technical_score,
        "explanation_score": explanation_score,
        "communication_score": communication_score,
        "overall_score": overall_score,
        "verdict": str(payload.get("verdict", "Needs improvement")).strip() or "Needs improvement",
        "review": review_text,
        "strengths": _clean_list(payload.get("strengths"), limit=3),
        "improvements": _clean_list(payload.get("improvements"), limit=3),
        "communication_notes": str(payload.get("communication_notes", "")).strip(),
    }


def _normalize_final_assessment(payload: dict[str, Any]) -> dict[str, Any]:
    technical_depth_score = _score(payload.get("technical_depth_score"))
    communication_score = _score(payload.get("communication_score"))
    readiness_score = _score(payload.get("readiness_score"))
    if readiness_score == 0:
        readiness_score = round((technical_depth_score + communication_score) / 2, 1)

    return {
        "status": str(payload.get("status", "Assessment pending")).strip() or "Assessment pending",
        "readiness_score": readiness_score,
        "technical_depth_score": technical_depth_score,
        "communication_score": communication_score,
        "summary": str(payload.get("summary", "")).strip(),
        "strengths": _clean_list(payload.get("strengths"), limit=4),
        "improvement_areas": _clean_list(payload.get("improvement_areas"), limit=4),
        "recommended_actions": _clean_list(payload.get("recommended_actions"), limit=4),
        "coverage_note": str(payload.get("coverage_note", "")).strip(),
    }


async def generate_interview_questions(
    *,
    provider: str,
    api_key: str,
    candidate_info: dict[str, Any],
) -> list[dict[str, Any]]:
    last_error: Exception | None = None

    for _ in range(2):
        try:
            payload = await json_completion(
                provider=provider,
                api_key=api_key,
                system_prompt=build_question_generation_prompt(
                    tech_stack=candidate_info.get("tech_stack", "general software"),
                    experience_years=candidate_info.get("years_experience", "unknown"),
                    position=candidate_info.get("desired_position", "tech role"),
                ),
                user_message="Generate the interview questions now.",
            )
            questions = _normalize_question_payload(payload)
            if len(questions) >= 5:
                return questions
        except Exception as exc:  # pragma: no cover - depends on external provider
            last_error = exc

    if last_error is not None:
        raise last_error
    raise ValueError("Question generation returned fewer than 5 valid questions.")


async def review_interview_answer(
    *,
    provider: str,
    api_key: str,
    question: Any,
    answer: str,
) -> dict[str, Any]:
    question_context = {
        "id": getattr(question, "id", None),
        "technology": getattr(question, "technology", ""),
        "difficulty": getattr(question, "difficulty", ""),
        "focus_area": getattr(question, "focus_area", ""),
        "question": getattr(question, "question", ""),
        "evaluation_rubric": getattr(question, "evaluation_rubric", []),
    }

    payload = await json_completion(
        provider=provider,
        api_key=api_key,
        system_prompt=build_answer_review_prompt(question_context),
        user_message=f"Candidate answer:\n{answer.strip()}",
    )
    return _normalize_review_payload(payload)


async def summarize_interview_assessment(
    *,
    provider: str,
    api_key: str,
    candidate_info: dict[str, Any],
    questions: list[Any],
) -> dict[str, Any]:
    answered_questions: list[dict[str, Any]] = []
    for question in questions:
        review = getattr(question, "review", None)
        if not review:
            continue
        answered_questions.append(
            {
                "question_id": getattr(question, "id", None),
                "technology": getattr(question, "technology", ""),
                "focus_area": getattr(question, "focus_area", ""),
                "difficulty": getattr(question, "difficulty", ""),
                "question": getattr(question, "question", ""),
                "candidate_answer": getattr(question, "candidate_answer", ""),
                "review": {
                    "technical_score": getattr(review, "technical_score", 0),
                    "explanation_score": getattr(review, "explanation_score", 0),
                    "communication_score": getattr(review, "communication_score", 0),
                    "overall_score": getattr(review, "overall_score", 0),
                    "verdict": getattr(review, "verdict", ""),
                    "review": getattr(review, "review", ""),
                    "strengths": getattr(review, "strengths", []),
                    "improvements": getattr(review, "improvements", []),
                    "communication_notes": getattr(review, "communication_notes", ""),
                },
            }
        )

    payload = await json_completion(
        provider=provider,
        api_key=api_key,
        system_prompt=build_final_assessment_prompt(candidate_info, answered_questions),
        user_message="Generate the final interview assessment now.",
    )
    return _normalize_final_assessment(payload)


def format_question_review_markdown(review: Any) -> str:
    strengths = getattr(review, "strengths", []) or []
    improvements = getattr(review, "improvements", []) or []
    communication_notes = getattr(review, "communication_notes", "")

    lines = [
        "### Answer Review",
        f"- Technical understanding: **{getattr(review, 'technical_score', 0):.1f}/10**",
        f"- Explanation depth: **{getattr(review, 'explanation_score', 0):.1f}/10**",
        f"- Communication clarity: **{getattr(review, 'communication_score', 0):.1f}/10**",
        f"- Overall: **{getattr(review, 'overall_score', 0):.1f}/10** ({getattr(review, 'verdict', 'Needs improvement')})",
    ]

    review_text = getattr(review, "review", "")
    if review_text:
        lines.extend(["", review_text])

    if strengths:
        lines.extend(["", "**What went well**"])
        lines.extend([f"- {item}" for item in strengths])

    if improvements:
        lines.extend(["", "**What to improve next**"])
        lines.extend([f"- {item}" for item in improvements])

    if communication_notes:
        lines.extend(["", f"**Communication note:** {communication_notes}"])

    return "\n".join(lines).strip()


def format_final_assessment_markdown(assessment: Any, heading: str = "Final Interview Assessment") -> str:
    if not assessment:
        return ""

    strengths = getattr(assessment, "strengths", []) or []
    improvement_areas = getattr(assessment, "improvement_areas", []) or []
    recommended_actions = getattr(assessment, "recommended_actions", []) or []
    coverage_note = getattr(assessment, "coverage_note", "")

    lines = [
        f"### {heading}",
        f"- Current status: **{getattr(assessment, 'status', 'Assessment pending')}**",
        f"- Interview readiness: **{getattr(assessment, 'readiness_score', 0):.1f}/10**",
        f"- Technical depth: **{getattr(assessment, 'technical_depth_score', 0):.1f}/10**",
        f"- Communication: **{getattr(assessment, 'communication_score', 0):.1f}/10**",
    ]

    summary = getattr(assessment, "summary", "")
    if summary:
        lines.extend(["", summary])

    if coverage_note:
        lines.extend(["", f"**Assessment scope:** {coverage_note}"])

    if strengths:
        lines.extend(["", "**Strengths noticed**"])
        lines.extend([f"- {item}" for item in strengths])

    if improvement_areas:
        lines.extend(["", "**Where to improve**"])
        lines.extend([f"- {item}" for item in improvement_areas])

    if recommended_actions:
        lines.extend(["", "**Suggested next steps**"])
        lines.extend([f"- {item}" for item in recommended_actions])

    return "\n".join(lines).strip()


def append_final_assessment_to_reply(reply: str, assessment: Any) -> str:
    assessment_text = format_final_assessment_markdown(assessment, heading="Interview Assessment Snapshot")
    if not assessment_text:
        return reply
    return "\n\n".join(part for part in [reply.strip(), assessment_text] if part)
