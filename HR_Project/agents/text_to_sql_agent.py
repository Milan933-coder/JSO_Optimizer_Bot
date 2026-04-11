"""
text_to_sql_agent.py
====================
Converts natural language HR queries into safe SQL and executes them
against the JSO SQLite database.

Flow:
    1. Receives a natural language query + extracted intent params
    2. Asks the configured LLM to generate SQL using the full schema as context
    3. Validates the SQL (safe mode: SELECT only)
    4. Executes against SQLite
    5. Returns structured results + the SQL used + human explanation
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.intent_classifier import is_safe_query
from database.setup_db import DB_PATH, get_connection, get_full_schema_context
from utils.config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MAX_TOKENS,
    CLAUDE_MODEL,
    EXPLAIN_SQL,
    GEMINI_MAX_TOKENS,
    GEMINI_MODEL,
    GOOGLE_API_KEY,
    SAFE_MODE,
)
from utils.llm import extract_text

_anthropic_client = None
_gemini_clients: dict[int, object] = {}


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic

        _anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _anthropic_client


def _get_gemini_client(max_tokens: int):
    cached = _gemini_clients.get(max_tokens)
    if cached is not None:
        return cached

    from langchain_google_genai import ChatGoogleGenerativeAI

    client = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        temperature=0,
        max_output_tokens=max_tokens,
        google_api_key=GOOGLE_API_KEY if GOOGLE_API_KEY else None,
    )
    _gemini_clients[max_tokens] = client
    return client


def _invoke_llm(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    if ANTHROPIC_API_KEY:
        client = _get_anthropic_client()
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text.strip()

    if GOOGLE_API_KEY:
        from langchain_core.messages import HumanMessage, SystemMessage

        client = _get_gemini_client(max_tokens=max_tokens or GEMINI_MAX_TOKENS)
        response = client.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        return extract_text(response.content).strip()

    raise RuntimeError(
        "No LLM API key configured. Add ANTHROPIC_API_KEY or GOOGLE_API_KEY to utils/.env."
    )


def _build_sql_system_prompt() -> str:
    """Builds the system prompt with the full DB schema injected."""
    schema = get_full_schema_context()
    return f"""
You are an expert SQL generator for a recruitment platform database.

Your job is to convert natural language HR questions into precise, efficient SQLite queries.

{schema}

Important rules:
1. ONLY generate SELECT queries. Never write INSERT, UPDATE, DELETE, DROP, or ALTER.
2. Always use table aliases for clarity.
3. For skill searches, use the skills table with JOINs.
4. For full text searches on CVs, use the cvs table.
5. Always include candidate name, email, location, experience_years in SELECT for people queries.
6. Use LOWER() for case-insensitive text comparisons.
7. Return ONLY the SQL query. No markdown, no explanation, no backticks.
8. If you need to JOIN skills, use: JOIN skills s ON s.candidate_id = c.id
9. For "not contacted" status, check applications table for status != 'shortlisted'.
10. Limit results to 50 unless the user specifies a different limit.

SQLite-specific notes:
- Use strftime() for date operations, not DATE_FORMAT()
- Use datetime('now', '-7 days') for relative dates
- There is no MONTH() function. Use strftime('%m', date_column)
"""


def _clean_sql(raw_sql: str) -> str:
    if "```" in raw_sql:
        parts = raw_sql.split("```")
        for part in parts:
            part = part.strip()
            if part.upper().startswith("SELECT") or part.upper().startswith("WITH"):
                raw_sql = part
                break

    if raw_sql.lower().startswith("sql\n"):
        raw_sql = raw_sql[4:].strip()

    return raw_sql.strip()


def generate_sql(natural_query: str, intent_params: dict = None) -> dict:
    """
    Converts a natural language query to SQL using the configured LLM.
    """
    system_prompt = _build_sql_system_prompt()

    enhanced_query = natural_query
    if intent_params and intent_params.get("sql_params", {}).get("filters"):
        filters = intent_params["sql_params"]["filters"]
        if filters:
            enhanced_query += f"\n\nExtracted filters to apply: {filters}"

    raw_sql = _invoke_llm(system_prompt, enhanced_query, CLAUDE_MAX_TOKENS or GEMINI_MAX_TOKENS)
    cleaned_sql = _clean_sql(raw_sql)

    explanation = ""
    if EXPLAIN_SQL:
        explanation = _explain_sql(natural_query, cleaned_sql)

    return {
        "sql": cleaned_sql,
        "explanation": explanation,
        "original_query": natural_query,
    }


def _explain_sql(natural_query: str, sql: str) -> str:
    """Explains the generated SQL in plain English."""
    return _invoke_llm(
        "You are a helpful assistant. Explain in 1-2 sentences what this SQL query does, in plain English for a non-technical HR professional. Be concise.",
        f"Original question: {natural_query}\n\nGenerated SQL: {sql}",
        min(CLAUDE_MAX_TOKENS, 200) if CLAUDE_MAX_TOKENS else 200,
    )


def execute_sql(sql: str) -> dict:
    """
    Safely executes a SQL query against the JSO database.
    """
    if SAFE_MODE and not is_safe_query(sql):
        return {
            "rows": [],
            "columns": [],
            "row_count": 0,
            "error": "SAFE MODE: Only SELECT queries are allowed. This query was blocked.",
        }

    conn = get_connection(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description] if cursor.description else []
        result_rows = [dict(row) for row in rows]

        return {
            "rows": result_rows,
            "columns": columns,
            "row_count": len(result_rows),
            "error": None,
        }

    except sqlite3.Error as exc:
        return {
            "rows": [],
            "columns": [],
            "row_count": 0,
            "error": f"SQL Error: {exc}",
        }
    finally:
        conn.close()


def run_text_to_sql(natural_query: str, intent_params: dict = None) -> dict:
    """
    Full pipeline: natural language -> SQL -> execute -> return results.
    """
    sql_result = generate_sql(natural_query, intent_params)
    sql = sql_result["sql"]
    explanation = sql_result["explanation"]

    exec_result = execute_sql(sql)

    return {
        "query_type": "sql",
        "original_query": natural_query,
        "generated_sql": sql,
        "explanation": explanation,
        "rows": exec_result["rows"],
        "columns": exec_result["columns"],
        "row_count": exec_result["row_count"],
        "error": exec_result["error"],
    }


def fix_and_retry(natural_query: str, failed_sql: str, error_message: str) -> dict:
    """
    If SQL execution fails, asks the LLM to fix the SQL and retries once.
    """
    fix_prompt = f"""
The following SQL query failed with an error. Please fix it.

Original question: {natural_query}
Failed SQL: {failed_sql}
Error: {error_message}

Return ONLY the corrected SQL query with no explanation.
"""
    fixed_sql = _clean_sql(
        _invoke_llm(_build_sql_system_prompt(), fix_prompt, min(CLAUDE_MAX_TOKENS, 512) if CLAUDE_MAX_TOKENS else 512)
    )
    exec_result = execute_sql(fixed_sql)
    exec_result["generated_sql"] = fixed_sql
    exec_result["explanation"] = f"Auto-fixed SQL after error: {error_message}"
    exec_result["query_type"] = "sql"
    exec_result["original_query"] = natural_query
    return exec_result
