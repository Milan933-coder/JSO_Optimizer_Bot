"""
intent_classifier.py
====================
Classifies the HR user's natural language query into one of three types:
    - "sql"      → structured data query (filters, counts, lookups)
    - "semantic" → meaning-based search (find candidates matching a JD)
    - "hybrid"   → combination of both (semantic search + SQL filters)
    - "compare"  → side-by-side candidate comparison
    - "explain"  → explain a candidate profile or past query result
    - "stats"    → analytics / aggregate statistics question

Uses Claude to classify intent and extract any parameters from the query.
"""

import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.config import GOOGLE_API_KEY, GEMINI_MODEL, GEMINI_MAX_TOKENS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from utils.llm import extract_text

llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    temperature=0,
    max_output_tokens=GEMINI_MAX_TOKENS,
    google_api_key=GOOGLE_API_KEY if GOOGLE_API_KEY else None,
)

INTENT_SYSTEM_PROMPT = """
You are an intent classifier for a HR recruitment platform's AI agent.

Your job is to analyze the HR user's question and return a structured JSON response
identifying what type of query it is and extracting key parameters.

Query Types:
- "sql"      : Questions about structured data — filtering by experience, location, skills,
               status, dates, counts, etc.
- "semantic" : Questions that require matching meaning — "find candidates for this job",
               "who matches this description", "best fit for..."
- "hybrid"   : Semantic search PLUS structured filters — "candidates matching this JD
               with 5+ years experience in London"
- "compare"  : Comparing specific candidates against each other or a JD
- "stats"    : Aggregate analytics — counts, averages, summaries, trends
- "explain"  : Explain a candidate, a past result, a decision, or a score

Important routing rule:
- Only choose "semantic" or "hybrid" if the user provides a full job description
  (usually 200+ characters) OR explicitly says they are pasting a JD.
  For short queries like "React devs in London", choose "sql".

For SQL queries, identify:
- filters (experience_years, location, skills, status, availability, salary range)
- aggregation (count, average, min, max)
- sort_by and sort_order
- limit

For semantic queries, identify:
- job_description_text (the JD text if provided inline)
- job_id (if they reference a specific job by ID)
- top_k (how many results they want)
- additional_filters (any structured constraints to apply after semantic search)

Always respond ONLY with valid JSON. No explanation, no markdown.

Response format:
{
  "intent": "sql" | "semantic" | "hybrid" | "compare" | "stats" | "explain",
  "confidence": 0.0-1.0,
  "description": "one sentence explaining what the user wants",
  "sql_params": {
    "filters": {},
    "aggregation": null,
    "sort_by": null,
    "sort_order": "DESC",
    "limit": 20
  },
  "semantic_params": {
    "jd_text": null,
    "job_id": null,
    "top_k": 10,
    "filters": {}
  },
  "raw_query": ""
}
"""


def _to_lc_message(msg: dict):
    role = msg.get("role")
    content = msg.get("content", "")
    if role == "assistant":
        return AIMessage(content=content)
    if role == "system":
        return SystemMessage(content=content)
    return HumanMessage(content=content)


def classify_intent(user_query: str, conversation_history: list = None) -> dict:
    """
    Classifies the intent of an HR query using Claude.

    Args:
        user_query: The natural language question from the HR consultant.
        conversation_history: Previous messages for context-aware classification.

    Returns:
        Dict with intent type, confidence, and extracted parameters.
    """
    messages = [SystemMessage(content=INTENT_SYSTEM_PROMPT)]

    # Include recent conversation for context (last 4 turns)
    if conversation_history:
        for msg in conversation_history[-4:]:
            messages.append(_to_lc_message(msg))

    messages.append(HumanMessage(content=user_query))

    response = llm.invoke(messages)

    raw_response = extract_text(response.content)

    try:
        # Strip markdown fences if present
        if raw_response.startswith("```"):
            raw_response = raw_response.split("```")[1]
            if raw_response.startswith("json"):
                raw_response = raw_response[4:]

        result = json.loads(raw_response)
        result["raw_query"] = user_query
        return result

    except json.JSONDecodeError:
        # Fallback to SQL if classification fails
        return {
            "intent": "sql",
            "confidence": 0.5,
            "description": "Could not classify intent, defaulting to SQL query.",
            "sql_params": {"filters": {}, "limit": 20},
            "semantic_params": {"jd_text": None, "top_k": 10, "filters": {}},
            "raw_query": user_query
        }


def is_safe_query(query: str) -> bool:
    """
    Basic safety check: only allow SELECT statements, no writes.
    Used before executing generated SQL.
    """
    dangerous_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "TRUNCATE", "ALTER", "CREATE"]
    query_upper = query.upper().strip()
    for keyword in dangerous_keywords:
        if keyword in query_upper:
            return False
    return query_upper.startswith("SELECT") or query_upper.startswith("WITH")
