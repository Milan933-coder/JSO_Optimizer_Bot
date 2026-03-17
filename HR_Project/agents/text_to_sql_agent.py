"""
text_to_sql_agent.py
====================
Converts natural language HR queries into safe SQL and executes them
against the JSO SQLite database.

Flow:
    1. Receives a natural language query + extracted intent params
    2. Asks Claude to generate SQL using the full schema as context
    3. Validates the SQL (safe mode: SELECT only)
    4. Executes against SQLite
    5. Returns structured results + the SQL used + human explanation
"""

import sqlite3
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.config import GOOGLE_API_KEY, GEMINI_MODEL, GEMINI_MAX_TOKENS, SAFE_MODE, EXPLAIN_SQL
from database.setup_db import get_connection, get_full_schema_context, DB_PATH
from agents.intent_classifier import is_safe_query
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from utils.llm import extract_text

llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    temperature=0,
    max_output_tokens=GEMINI_MAX_TOKENS,
    google_api_key=GOOGLE_API_KEY if GOOGLE_API_KEY else None,
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
7. Return ONLY the SQL query — no markdown, no explanation, no backticks.
8. If you need to JOIN skills, use: JOIN skills s ON s.candidate_id = c.id
9. For "not contacted" status, check applications table for status != 'shortlisted'.
10. Limit results to 50 unless the user specifies a different limit.

SQLite-specific notes:
- Use strftime() for date operations, not DATE_FORMAT()
- Use datetime('now', '-7 days') for relative dates
- There is no MONTH() function — use strftime('%m', date_column)
"""


def _extract_sql_from_text(raw_text: str) -> str:
    """Extracts the first SQL statement starting with SELECT/WITH."""
    text = raw_text.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.lower().startswith("sql"):
                part = part[3:].strip()
            if part.upper().startswith("SELECT") or part.upper().startswith("WITH"):
                text = part
                break
    match = re.search(r"\b(SELECT|WITH)\b", text, re.IGNORECASE)
    if match:
        text = text[match.start():]
    if ";" in text:
        text = text.split(";", 1)[0]
    return text.strip()


def generate_sql(natural_query: str, intent_params: dict = None) -> dict:
    """
    Converts a natural language query to SQL using Claude.

    Args:
        natural_query:  The HR question in plain English.
        intent_params:  Optional pre-extracted params from the intent classifier.

    Returns:
        Dict with: sql, explanation, estimated_rows
    """
    system_prompt = _build_sql_system_prompt()

    # Enhance the query with any extracted filters
    enhanced_query = natural_query
    if intent_params and intent_params.get("sql_params", {}).get("filters"):
        filters = intent_params["sql_params"]["filters"]
        if filters:
            enhanced_query += f"\n\nExtracted filters to apply: {filters}"

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=enhanced_query),
    ])

    raw_sql = _extract_sql_from_text(extract_text(response.content))

    # Generate human-readable explanation if enabled
    explanation = ""
    if EXPLAIN_SQL:
        explanation = _explain_sql(natural_query, raw_sql)

    return {
        "sql": raw_sql,
        "explanation": explanation,
        "original_query": natural_query
    }


def _explain_sql(natural_query: str, sql: str) -> str:
    """Asks Claude to explain the generated SQL in plain English."""
    response = llm.invoke([
        SystemMessage(content="You are a helpful assistant. Explain in 1-2 sentences what this SQL query does, in plain English for a non-technical HR professional. Be concise."),
        HumanMessage(content=f"Original question: {natural_query}\n\nGenerated SQL: {sql}"),
    ])
    return extract_text(response.content)


def execute_sql(sql: str) -> dict:
    """
    Safely executes a SQL query against the JSO database.

    Args:
        sql: The SQL string to execute.

    Returns:
        Dict with: rows (list of dicts), columns, row_count, error
    """
    # Safety check
    if SAFE_MODE and not is_safe_query(sql):
        return {
            "rows": [],
            "columns": [],
            "row_count": 0,
            "error": "⛔ SAFE MODE: Only SELECT queries are allowed. This query was blocked."
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
            "error": None
        }

    except sqlite3.Error as e:
        return {
            "rows": [],
            "columns": [],
            "row_count": 0,
            "error": f"SQL Error: {str(e)}"
        }
    finally:
        conn.close()


def run_text_to_sql(natural_query: str, intent_params: dict = None) -> dict:
    """
    Full pipeline: natural language → SQL → execute → return results.

    Args:
        natural_query: Plain English HR question.
        intent_params: Pre-classified intent from intent_classifier.

    Returns:
        Dict with: sql, explanation, rows, columns, row_count, error
    """
    # Step 1: Generate SQL
    sql_result = generate_sql(natural_query, intent_params)
    sql = sql_result["sql"]
    explanation = sql_result["explanation"]

    # Step 2: Execute SQL
    exec_result = execute_sql(sql)

    return {
        "query_type": "sql",
        "original_query": natural_query,
        "generated_sql": sql,
        "explanation": explanation,
        "rows": exec_result["rows"],
        "columns": exec_result["columns"],
        "row_count": exec_result["row_count"],
        "error": exec_result["error"]
    }


def fix_and_retry(natural_query: str, failed_sql: str, error_message: str) -> dict:
    """
    If SQL execution fails, asks Claude to fix the SQL and retries once.

    Args:
        natural_query:  Original HR question.
        failed_sql:     The SQL that failed.
        error_message:  The error from SQLite.

    Returns:
        Fixed execution result dict.
    """
    fix_prompt = f"""
The following SQL query failed with an error. Please fix it.

Original question: {natural_query}
Failed SQL: {failed_sql}
Error: {error_message}

Return ONLY the corrected SQL query with no explanation.
"""
    response = llm.invoke([
        SystemMessage(content=_build_sql_system_prompt()),
        HumanMessage(content=fix_prompt),
    ])

    fixed_sql = _extract_sql_from_text(extract_text(response.content))
    exec_result = execute_sql(fixed_sql)
    exec_result["generated_sql"] = fixed_sql
    exec_result["explanation"] = f"Auto-fixed SQL after error: {error_message}"
    exec_result["query_type"] = "sql"
    exec_result["original_query"] = natural_query
    return exec_result
