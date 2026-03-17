"""
embeddings.py
=============
Handles text vectorisation and cosine similarity computation.
Uses sentence-transformers (local, free, no API key required) to generate
embeddings for CVs and Job Descriptions.

Key functions:
    - get_embedding(text)         → numpy vector
    - cosine_similarity(a, b)     → float 0-1
    - embed_all_cvs()             → embeds + stores all CVs in DB
    - search_by_jd(jd_text, k)   → returns top-k matching candidates
"""

import json
import sqlite3
import numpy as np
from typing import Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.config import DB_PATH, TOP_K_RESULTS, SIMILARITY_THRESHOLD
from database.setup_db import get_connection

# Lazy-load the model (only once)
_model = None

def _get_model():
    """Loads the sentence-transformer model (cached after first call)."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("  🔄 Loading embedding model (first time only)...")
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            print("  ✅ Embedding model loaded.")
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed.\n"
                "Run: pip install sentence-transformers"
            )
    return _model


def get_embedding(text: str) -> np.ndarray:
    """
    Converts a text string into a dense vector embedding.

    Args:
        text: Any string (CV, job description, skill list, etc.)

    Returns:
        numpy array of shape (384,) — the embedding vector
    """
    model = _get_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Computes cosine similarity between two vectors.

    Returns:
        float between 0.0 (no match) and 1.0 (perfect match)
    """
    if np.linalg.norm(vec_a) == 0 or np.linalg.norm(vec_b) == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b)))


def embed_all_cvs(force_reembed: bool = False) -> int:
    """
    Generates and stores embeddings for all CVs in the database.
    Skips CVs that already have embeddings unless force_reembed=True.

    Args:
        force_reembed: If True, re-embeds even if embedding already exists.

    Returns:
        Number of CVs embedded.
    """
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()

    if force_reembed:
        rows = cursor.execute("SELECT id, candidate_id, raw_text FROM cvs").fetchall()
    else:
        rows = cursor.execute(
            "SELECT id, candidate_id, raw_text FROM cvs WHERE embedding IS NULL"
        ).fetchall()

    count = 0
    for row in rows:
        embedding = get_embedding(row["raw_text"])
        embedding_json = json.dumps(embedding.tolist())
        cursor.execute(
            "UPDATE cvs SET embedding = ? WHERE id = ?",
            (embedding_json, row["id"])
        )
        count += 1

    conn.commit()
    conn.close()

    if count > 0:
        print(f"  ✅ Embedded {count} CV(s).")
    return count


def search_by_job_description(
    jd_text: str,
    top_k: int = TOP_K_RESULTS,
    min_score: float = SIMILARITY_THRESHOLD,
    filters: Optional[dict] = None
) -> list[dict]:
    """
    Finds the most semantically similar candidates for a given job description.

    Args:
        jd_text:  The full job description text.
        top_k:    How many top results to return.
        min_score: Minimum cosine similarity to include in results.
        filters:  Optional SQL filters dict e.g. {"experience_years": 5, "location": "London"}

    Returns:
        List of dicts with candidate info + match_score, sorted by score descending.
    """
    # Ensure all CVs are embedded
    embed_all_cvs()

    jd_embedding = get_embedding(jd_text)

    conn = get_connection(DB_PATH)
    cursor = conn.cursor()

    # Build optional WHERE clause from filters
    where_clauses = ["cvs.embedding IS NOT NULL"]
    params = []
    if filters:
        if "experience_years" in filters:
            where_clauses.append("candidates.experience_years >= ?")
            params.append(filters["experience_years"])
        if "location" in filters:
            where_clauses.append("LOWER(candidates.location) LIKE ?")
            params.append(f"%{filters['location'].lower()}%")
        if "availability" in filters:
            where_clauses.append("candidates.availability = ?")
            params.append(filters["availability"])

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    query = f"""
        SELECT
            candidates.id,
            candidates.full_name,
            candidates.email,
            candidates.location,
            candidates.experience_years,
            candidates.current_role,
            candidates.current_company,
            candidates.expected_salary,
            candidates.availability,
            candidates.github_score,
            candidates.risk_score,
            cvs.embedding,
            cvs.raw_text
        FROM cvs
        JOIN candidates ON cvs.candidate_id = candidates.id
        {where_sql}
    """

    rows = cursor.execute(query, params).fetchall()
    conn.close()

    # Compute cosine similarity for each candidate
    results = []
    for row in rows:
        try:
            cv_embedding = np.array(json.loads(row["embedding"]))
            score = cosine_similarity(jd_embedding, cv_embedding)

            if score >= min_score:
                # Fetch skills for this candidate
                conn2 = get_connection(DB_PATH)
                skills = conn2.execute(
                    "SELECT skill_name, proficiency_level FROM skills WHERE candidate_id = ? ORDER BY years_of_experience DESC",
                    (row["id"],)
                ).fetchall()
                conn2.close()

                skill_list = [f"{s['skill_name']} ({s['proficiency_level']})" for s in skills]

                results.append({
                    "candidate_id":    row["id"],
                    "full_name":       row["full_name"],
                    "email":           row["email"],
                    "location":        row["location"],
                    "experience_years":row["experience_years"],
                    "current_role":    row["current_role"],
                    "current_company": row["current_company"],
                    "expected_salary": row["expected_salary"],
                    "availability":    row["availability"],
                    "github_score":    row["github_score"],
                    "risk_score":      row["risk_score"],
                    "skills":          skill_list,
                    "match_score":     round(score, 4),
                    "match_percent":   f"{round(score * 100, 1)}%",
                    "cv_snippet":      row["raw_text"][:200] + "..."
                })
        except (json.JSONDecodeError, ValueError):
            continue

    # Sort by match score descending
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:top_k]


def compare_candidates(candidate_ids: list[int], jd_text: str) -> list[dict]:
    """
    Generates a side-by-side comparison of specific candidates against a JD.

    Args:
        candidate_ids: List of candidate IDs to compare.
        jd_text:       The job description to compare against.

    Returns:
        List of dicts with candidate details + match score, sorted by score.
    """
    jd_embedding = get_embedding(jd_text)
    conn = get_connection(DB_PATH)
    results = []

    for cid in candidate_ids:
        row = conn.execute("""
            SELECT c.id, c.full_name, c.experience_years, c.location, c.github_score,
                   c.risk_score, c.expected_salary, cv.embedding, cv.raw_text
            FROM candidates c JOIN cvs cv ON cv.candidate_id = c.id
            WHERE c.id = ?
        """, (cid,)).fetchone()

        if row and row["embedding"]:
            cv_emb = np.array(json.loads(row["embedding"]))
            score = cosine_similarity(jd_embedding, cv_emb)

            skills = conn.execute(
                "SELECT skill_name FROM skills WHERE candidate_id = ? ORDER BY years_of_experience DESC LIMIT 6",
                (cid,)
            ).fetchall()

            results.append({
                "candidate_id":    row["id"],
                "full_name":       row["full_name"],
                "experience_years":row["experience_years"],
                "location":        row["location"],
                "github_score":    row["github_score"],
                "risk_score":      row["risk_score"],
                "expected_salary": row["expected_salary"],
                "top_skills":      [s["skill_name"] for s in skills],
                "match_score":     round(score, 4),
                "match_percent":   f"{round(score * 100, 1)}%",
            })

    conn.close()
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results
