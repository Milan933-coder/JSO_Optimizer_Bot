"""
semantic_search_agent.py
========================
Handles semantic/cosine-similarity-based candidate search.

Given a Job Description (JD) text, this agent:
    1. Converts the JD to a vector embedding
    2. Compares it against all CV embeddings in the DB
    3. Returns ranked candidates with match scores
    4. Optionally generates a human-readable summary via Claude

Also handles:
    - Hybrid mode: semantic search + SQL filters combined
    - Candidate comparison mode
    - Skills gap analysis
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.config import GOOGLE_API_KEY, GEMINI_MODEL, GEMINI_MAX_TOKENS, TOP_K_RESULTS
from utils.embeddings import (
    search_by_job_description,
    compare_candidates,
    embed_all_cvs
)
from database.setup_db import get_connection, DB_PATH
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from utils.llm import extract_text

llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    temperature=0,
    max_output_tokens=GEMINI_MAX_TOKENS,
    google_api_key=GOOGLE_API_KEY if GOOGLE_API_KEY else None,
)


def run_semantic_search(
    jd_text: str,
    top_k: int = TOP_K_RESULTS,
    filters: dict = None,
    generate_summary: bool = True
) -> dict:
    """
    Finds best-matching candidates for a job description using cosine similarity.

    Args:
        jd_text:          The full job description text.
        top_k:            Number of top matches to return.
        filters:          Optional structured filters {experience_years, location, availability}.
        generate_summary: If True, Claude generates a brief narrative summary.

    Returns:
        Dict with: candidates (ranked list), jd_summary, search_type
    """
    # Ensure all CVs are embedded
    embed_all_cvs()

    # Run cosine similarity search
    candidates = search_by_job_description(jd_text, top_k=top_k, filters=filters or {})

    # Generate summary using Claude
    summary = ""
    if generate_summary and candidates:
        summary = _generate_search_summary(jd_text, candidates)

    return {
        "query_type": "semantic",
        "jd_text": jd_text[:300] + "..." if len(jd_text) > 300 else jd_text,
        "filters_applied": filters or {},
        "total_found": len(candidates),
        "candidates": candidates,
        "summary": summary
    }


def run_hybrid_search(
    jd_text: str,
    sql_filters: dict,
    top_k: int = TOP_K_RESULTS
) -> dict:
    """
    Hybrid mode: semantic similarity search WITH structured SQL filters.
    Example: "Candidates matching this JD with 5+ years experience in London"

    Args:
        jd_text:     Job description text.
        sql_filters: Dict of SQL filters to apply e.g. {"experience_years": 5, "location": "London"}
        top_k:       How many results to return.

    Returns:
        Same format as run_semantic_search but with filters applied.
    """
    candidates = search_by_job_description(jd_text, top_k=top_k, filters=sql_filters)

    summary = _generate_search_summary(jd_text, candidates) if candidates else "No candidates found matching your criteria."

    return {
        "query_type": "hybrid",
        "jd_text": jd_text[:300] + "...",
        "filters_applied": sql_filters,
        "total_found": len(candidates),
        "candidates": candidates,
        "summary": summary
    }


def run_candidate_comparison(candidate_ids: list[int], jd_text: str) -> dict:
    """
    Compares specific candidates side-by-side against a job description.

    Args:
        candidate_ids: List of candidate IDs to compare.
        jd_text:       Job description to compare against.

    Returns:
        Dict with comparison table data and Claude's recommendation.
    """
    comparison = compare_candidates(candidate_ids, jd_text)
    recommendation = _generate_comparison_recommendation(comparison, jd_text)

    return {
        "query_type": "compare",
        "candidates_compared": len(comparison),
        "comparison_table": comparison,
        "recommendation": recommendation
    }


def analyze_skills_gap(jd_text: str, top_k: int = 20) -> dict:
    """
    Analyzes what skills are most missing across all candidates for a given JD.

    Args:
        jd_text: The job description.
        top_k:   How many candidates to analyze.

    Returns:
        Dict with skills gap analysis.
    """
    candidates = search_by_job_description(jd_text, top_k=top_k)

    # Extract required skills from JD using Claude
    required_skills = _extract_required_skills(jd_text)

    # Count how many candidates have each required skill
    skill_coverage = {}
    total_candidates = len(candidates)

    if total_candidates == 0:
        return {"query_type": "skills_gap", "error": "No candidates found."}

    conn = get_connection(DB_PATH)
    for skill in required_skills:
        count = 0
        for c in candidates:
            has_skill = conn.execute(
                "SELECT 1 FROM skills WHERE candidate_id = ? AND LOWER(skill_name) LIKE ?",
                (c["candidate_id"], f"%{skill.lower()}%")
            ).fetchone()
            if has_skill:
                count += 1

        missing_pct = round(((total_candidates - count) / total_candidates) * 100, 1)
        skill_coverage[skill] = {
            "candidates_with_skill": count,
            "candidates_missing": total_candidates - count,
            "missing_percent": missing_pct
        }
    conn.close()

    # Sort by most missing
    sorted_gaps = dict(sorted(skill_coverage.items(), key=lambda x: x[1]["missing_percent"], reverse=True))

    return {
        "query_type": "skills_gap",
        "total_candidates_analyzed": total_candidates,
        "required_skills": required_skills,
        "skills_gap": sorted_gaps
    }


def explain_candidate(candidate_id: int, jd_text: str = None) -> dict:
    """
    Generates a human-readable briefing on a candidate.
    Optionally explains fit against a specific JD.

    Args:
        candidate_id: The candidate's database ID.
        jd_text:      Optional JD to compare against.

    Returns:
        Dict with candidate briefing and fit analysis.
    """
    conn = get_connection(DB_PATH)

    candidate = conn.execute("""
        SELECT c.*, cv.raw_text
        FROM candidates c
        LEFT JOIN cvs cv ON cv.candidate_id = c.id
        WHERE c.id = ?
    """, (candidate_id,)).fetchone()

    if not candidate:
        conn.close()
        return {"error": f"Candidate with ID {candidate_id} not found."}

    skills = conn.execute(
        "SELECT skill_name, proficiency_level, years_of_experience FROM skills WHERE candidate_id = ?",
        (candidate_id,)
    ).fetchall()
    conn.close()

    skill_list = [f"{s['skill_name']} ({s['proficiency_level']}, {s['years_of_experience']}yr)" for s in skills]

    profile_data = f"""
Candidate: {candidate['full_name']}
Location: {candidate['location']}
Experience: {candidate['experience_years']} years
Current Role: {candidate['current_role']} at {candidate['current_company']}
Expected Salary: ${candidate['expected_salary']:,}
Availability: {candidate['availability']}
GitHub Score: {candidate['github_score']}/10
Risk Score: {candidate['risk_score']}/100
Skills: {', '.join(skill_list)}
CV: {candidate['raw_text'] or 'Not available'}
"""

    jd_context = f"\n\nJob Description to evaluate against:\n{jd_text}" if jd_text else ""

    prompt = f"""
Write a concise 3-4 sentence professional briefing on this candidate{' and their fit for the job' if jd_text else ''}.
Focus on: strengths, experience highlights, and {'fit for this specific role' if jd_text else 'key selling points'}.
Be factual and professional, like a recruiter briefing a hiring manager.

{profile_data}{jd_context}
"""

    response = llm.invoke([
        SystemMessage(content="You are a senior talent acquisition specialist writing candidate briefings."),
        HumanMessage(content=prompt),
    ])

    briefing = extract_text(response.content)

    return {
        "query_type": "explain",
        "candidate_id": candidate_id,
        "full_name": candidate["full_name"],
        "briefing": briefing,
        "skills": skill_list
    }


# ── Private helpers ─────────────────────────────────────────────────────────

def _generate_search_summary(jd_text: str, candidates: list) -> str:
    """Generates a brief summary of semantic search results."""
    top_3 = candidates[:3]
    top_names = ", ".join([f"{c['full_name']} ({c['match_percent']})" for c in top_3])

    response = llm.invoke([
        SystemMessage(content="You are a recruitment assistant. Write a 2-sentence summary of candidate search results for an HR consultant. Be direct and practical."),
        HumanMessage(content=f"JD summary: {jd_text[:300]}\nTop candidates: {top_names}\nTotal found: {len(candidates)}"),
    ])
    return extract_text(response.content)


def _generate_comparison_recommendation(comparison: list, jd_text: str) -> str:
    """Generates a hiring recommendation based on candidate comparison."""
    if not comparison:
        return "No candidates available for comparison."

    summary = "\n".join([
        f"- {c['full_name']}: {c['match_percent']} match, {c['experience_years']} yrs exp, GitHub {c['github_score']}/10"
        for c in comparison
    ])

    response = llm.invoke([
        SystemMessage(content="You are a senior recruitment consultant. Give a clear hiring recommendation based on candidate comparison data. Be decisive and practical."),
        HumanMessage(content=f"Job: {jd_text[:200]}\n\nCandidates:\n{summary}\n\nWho should we interview first and why?"),
    ])
    return extract_text(response.content)


def _extract_required_skills(jd_text: str) -> list[str]:
    """Uses Claude to extract required skills from a JD."""
    response = llm.invoke([
        SystemMessage(content="Extract the required technical skills from this job description. Return ONLY a comma-separated list of skill names. No explanation."),
        HumanMessage(content=jd_text),
    ])
    skills_text = extract_text(response.content)
    return [s.strip() for s in skills_text.split(",") if s.strip()]
