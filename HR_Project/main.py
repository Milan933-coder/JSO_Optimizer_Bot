"""
main.py
=======
JSO HR Intelligence Agent — FastAPI Server (port 8000)

Endpoints:
    GET  /                  → health check + API info
    POST /ask               → ask the agent a natural-language question
    POST /reset             → reset the agent session
    GET  /history           → last 50 logged queries
    GET  /candidates        → list all candidates
    GET  /candidates/{id}   → single candidate detail + skills + applications
    GET  /jobs              → list all job descriptions
    GET  /jobs/{id}         → single job + all its applications

Usage:
    python main.py
    python main.py --port 9000
    python main.py --reload        # hot-reload dev mode
    python main.py --reset-db      # wipe + reseed DB on startup

Or directly with uvicorn:
    uvicorn main:app --reload --port 8000
"""

import sys
import os
import argparse
import traceback
from contextlib import asynccontextmanager
from typing import Any, Optional, TYPE_CHECKING

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))

from database.setup_db import setup_database, get_connection, DB_PATH

if TYPE_CHECKING:
    from agents.orchestrator import HRAgent


# ── Pydantic models ───────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    query: str
    hr_name: Optional[str] = "HR Consultant"
    hr_id: Optional[int] = 1


class AskResponse(BaseModel):
    query: str
    query_type: str
    success: bool
    # SQL / Stats
    generated_sql: Optional[str] = None
    explanation: Optional[str] = None
    row_count: Optional[int] = None
    columns: Optional[list] = None
    rows: Optional[list] = None
    # Semantic / Hybrid
    total_found: Optional[int] = None
    summary: Optional[str] = None
    filters_applied: Optional[dict] = None
    candidates: Optional[list] = None
    # Compare
    candidates_compared: Optional[int] = None
    comparison_table: Optional[list] = None
    recommendation: Optional[str] = None
    # Explain
    candidate_id: Optional[int] = None
    full_name: Optional[str] = None
    briefing: Optional[str] = None
    skills: Optional[list] = None
    # Error
    error: Optional[str] = None


class ResetResponse(BaseModel):
    status: str
    message: str


# ── Agent singleton ───────────────────────────────────────────────────────────

_agent: Any = None


def _get_hr_agent_class():
    from agents.orchestrator import HRAgent

    return HRAgent


def get_agent(hr_id: int = 1, hr_name: str = "HR Consultant", create: bool = False) -> Optional["HRAgent"]:
    global _agent
    if _agent is None:
        if not create:
            return None
        agent_class = _get_hr_agent_class()
        _agent = agent_class(hr_id=hr_id, hr_name=hr_name)
    return _agent


# ── Lifespan (startup / shutdown hooks) ──────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n🗄️  Checking database...")
    setup_database()
    print("Agent lazy-loading is enabled; the first /ask request will initialize the HR agent.")
    print("✅ Server ready.\n")
    yield
    print("\n👋 Server shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="JSO HR Intelligence Agent",
    description=(
        "Ask questions about candidates and job matches in plain English. "
        "Powered by Gemini + cosine similarity search.\n\n"
        "**Example queries for POST /ask:**\n"
        "- `Show me React developers with 5+ years experience`\n"
        "- `Find candidates in London sorted by GitHub score`\n"
        "- `Compare candidates 1, 3, 5`\n"
        "- `Explain candidate 5`\n"
        "- `How many candidates per location?`\n"
        "- Paste a full job description to run semantic search"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.head("/", tags=["Health"], include_in_schema=False)
def health_head():
    """HEAD ping — used by browsers and uptime tools."""
    return {}


@app.get("/", tags=["Health"])
def health_check():
    """Health check and quick API reference."""
    return {
        "status": "ok",
        "service": "JSO HR Intelligence Agent",
        "version": "1.0.0",
        "swagger_ui": "http://localhost:8000/docs",
        "example_queries": [
            "Show me candidates with 5+ years of experience",
            "Find React developers in London",
            "Top 5 candidates by GitHub score",
            "Who was shortlisted for job 1?",
            "How many candidates per location?",
            "Compare candidates 1, 3, 5",
            "Explain candidate 5",
            "Paste a full JD here to find best matches",
        ],
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
def ask_agent(body: AskRequest):
    """
    Main agent endpoint — ask anything in plain English.

    The agent automatically detects whether your question needs:
    - **SQL query** — filters, counts, lookups by field
    - **Semantic search** — paste a job description to match CVs
    - **Hybrid** — JD text + structured filters combined
    - **Compare** — side-by-side candidate comparison
    - **Explain** — human-readable briefing on a candidate
    - **Stats** — aggregates and analytics
    """
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Field 'query' must not be empty.")

    agent = get_agent(hr_id=body.hr_id, hr_name=body.hr_name, create=True)

    try:
        result = agent.ask(query)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    qtype = result.get("query_type", "unknown")
    response = AskResponse(
        query=query,
        query_type=qtype,
        success=result.get("error") is None,
        error=result.get("error"),
    )

    if result.get("error"):
        return response

    if qtype in ("sql", "stats"):
        response.generated_sql = result.get("generated_sql", "")
        response.explanation    = result.get("explanation", "")
        response.row_count      = result.get("row_count", 0)
        response.columns        = result.get("columns", [])
        response.rows           = result.get("rows", [])

    elif qtype in ("semantic", "hybrid"):
        response.total_found     = result.get("total_found", 0)
        response.summary         = result.get("summary", "")
        response.filters_applied = result.get("filters_applied", {})
        response.candidates      = result.get("candidates", [])

    elif qtype == "compare":
        response.candidates_compared = result.get("candidates_compared", 0)
        response.comparison_table    = result.get("comparison_table", [])
        response.recommendation      = result.get("recommendation", "")

    elif qtype == "explain":
        response.candidate_id = result.get("candidate_id")
        response.full_name    = result.get("full_name", "")
        response.briefing     = result.get("briefing", "")
        response.skills       = result.get("skills", [])

    return response


@app.post("/reset", response_model=ResetResponse, tags=["Agent"])
def reset_session():
    """Clears conversation history and starts a fresh agent session."""
    global _agent
    _agent = None
    return ResetResponse(status="reset", message="Session cleared. Conversation history wiped.")


@app.get("/history", tags=["Logs"])
def get_query_history(limit: int = 50):
    """Returns the last N logged queries from the database."""
    conn = get_connection(DB_PATH)
    rows = conn.execute(
        """
        SELECT id, natural_language_query, query_type, result_count, executed_at
        FROM query_history
        ORDER BY executed_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return {"total": len(rows), "history": [dict(r) for r in rows]}


@app.get("/candidates", tags=["Data"])
def list_candidates():
    """Returns all candidates with key profile fields, ordered by experience."""
    conn = get_connection(DB_PATH)
    rows = conn.execute(
        """
        SELECT id, full_name, email, location, experience_years,
               current_role, current_company, expected_salary,
               availability, github_score, risk_score, profile_status
        FROM candidates
        ORDER BY experience_years DESC
        """
    ).fetchall()
    conn.close()
    return {"total": len(rows), "candidates": [dict(r) for r in rows]}


@app.get("/candidates/{candidate_id}", tags=["Data"])
def get_candidate(candidate_id: int):
    """Returns full profile for one candidate: details + skills + application history."""
    conn = get_connection(DB_PATH)

    candidate = conn.execute(
        "SELECT * FROM candidates WHERE id = ?", (candidate_id,)
    ).fetchone()

    if not candidate:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found.")

    skills = conn.execute(
        """
        SELECT skill_name, proficiency_level, years_of_experience
        FROM skills WHERE candidate_id = ?
        ORDER BY years_of_experience DESC
        """,
        (candidate_id,),
    ).fetchall()

    applications = conn.execute(
        """
        SELECT a.status, a.match_score, a.applied_at, a.hr_notes,
               j.title AS job_title, j.company
        FROM applications a
        JOIN job_descriptions j ON j.id = a.job_id
        WHERE a.candidate_id = ?
        ORDER BY a.applied_at DESC
        """,
        (candidate_id,),
    ).fetchall()

    conn.close()
    return {
        "candidate":    dict(candidate),
        "skills":       [dict(s) for s in skills],
        "applications": [dict(a) for a in applications],
    }


@app.get("/jobs", tags=["Data"])
def list_jobs():
    """Returns all job descriptions ordered by most recent."""
    conn = get_connection(DB_PATH)
    rows = conn.execute(
        """
        SELECT id, title, company, location, job_type,
               experience_required, salary_min, salary_max,
               required_skills, status, created_at
        FROM job_descriptions
        ORDER BY created_at DESC
        """
    ).fetchall()
    conn.close()
    return {"total": len(rows), "jobs": [dict(r) for r in rows]}


@app.get("/jobs/{job_id}", tags=["Data"])
def get_job(job_id: int):
    """Returns full details for one job including all applicants ranked by match score."""
    conn = get_connection(DB_PATH)

    job = conn.execute(
        "SELECT * FROM job_descriptions WHERE id = ?", (job_id,)
    ).fetchone()

    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    applications = conn.execute(
        """
        SELECT a.status, a.match_score, a.applied_at, a.hr_notes,
               c.id AS candidate_id, c.full_name, c.email,
               c.location, c.experience_years, c.github_score
        FROM applications a
        JOIN candidates c ON c.id = a.candidate_id
        WHERE a.job_id = ?
        ORDER BY a.match_score DESC
        """,
        (job_id,),
    ).fetchall()

    conn.close()
    return {"job": dict(job), "applications": [dict(a) for a in applications]}


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="JSO HR Intelligence Agent — FastAPI Server")
    parser.add_argument("--port",     type=int,  default=8000,    help="Port (default: 8000)")
    parser.add_argument("--host",     type=str,  default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("--reload",   action="store_true",        help="Hot-reload on file changes (dev mode)")
    parser.add_argument("--reset-db", action="store_true",        help="Wipe and reseed the database on startup")
    args = parser.parse_args()

    if args.reset_db:
        setup_database(reset=True)

    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║         JSO HR Intelligence Agent — FastAPI Server               ║
╠══════════════════════════════════════════════════════════════════╣
║  Base URL    →  http://localhost:{args.port:<33}║
║  Swagger UI  →  http://localhost:{args.port}/docs{' ' * 28}║
║  ReDoc       →  http://localhost:{args.port}/redoc{' ' * 27}║
╠══════════════════════════════════════════════════════════════════╣
║  POST /ask              ← ask the agent anything                 ║
║  GET  /candidates       ← list all candidates                    ║
║  GET  /candidates/{{id}}  ← candidate detail + skills            ║
║  GET  /jobs             ← list all jobs                          ║
║  GET  /jobs/{{id}}        ← job detail + applicants              ║
║  GET  /history          ← query log                              ║
║  POST /reset            ← clear session                          ║
╠══════════════════════════════════════════════════════════════════╣
║  Quick test:                                                     ║
║  curl -X POST http://localhost:{args.port}/ask \\                 ║
║    -H "Content-Type: application/json" \\                        ║
║    -d '{{"query":"React devs with 5+ years"}}'                   ║
╚══════════════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
