"""
orchestrator.py
===============
The main brain of the JSO HR Intelligence Agent.

Responsibilities:
    - Receives HR queries
    - Calls the intent classifier
    - Routes to the correct agent (SQL / Semantic / Hybrid / Compare / Stats)
    - Formats results for display
    - Maintains conversation memory within a session
    - Logs queries to DB

Usage:
    from agents.orchestrator import HRAgent
    agent = HRAgent(hr_id=1)
    result = agent.ask("Show me React developers with 5+ years experience")
"""

import builtins
import json
import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.config import LOG_QUERIES, ENABLE_SEMANTIC, SEMANTIC_MIN_QUERY_CHARS
from agents.intent_classifier import classify_intent
from agents.text_to_sql_agent import run_text_to_sql, fix_and_retry
from agents.semantic_search_agent import (
    run_semantic_search,
    run_hybrid_search,
    run_candidate_comparison,
    analyze_skills_gap,
    explain_candidate
)
from database.setup_db import get_connection, DB_PATH

JD_KEYWORDS = (
    "job description",
    "jd:",
    "responsibilities",
    "requirements",
    "must have",
    "nice to have",
    "what you will do",
    "role:",
    "we are looking for",
)


def _looks_like_jd(text: str) -> bool:
    t = text.lower()
    if len(text) >= SEMANTIC_MIN_QUERY_CHARS:
        return True
    return any(k in t for k in JD_KEYWORDS)


def _should_use_semantic(intent: str, query: str, sem_params: dict) -> bool:
    if not ENABLE_SEMANTIC:
        return False
    if intent not in ("semantic", "hybrid"):
        return False
    if sem_params.get("jd_text"):
        return True
    return _looks_like_jd(query)


def _safe_print(message: str = "") -> None:
    try:
        builtins.print(message)
    except UnicodeEncodeError:
        builtins.print(message.encode("ascii", errors="replace").decode("ascii"))


print = _safe_print


class HRAgent:
    """
    Conversational HR Intelligence Agent.

    Maintains session state, conversation history, and routes queries
    to the appropriate specialised agent.
    """

    def __init__(self, hr_id: int = None, hr_name: str = "HR Consultant"):
        self.hr_id = hr_id
        self.hr_name = hr_name
        self.conversation_history = []   # full turn history for context
        self.last_result = None          # last query result for follow-ups
        self.last_jd = None              # last JD used (for follow-up comparisons)
        self.session_start = datetime.datetime.now()
        print(f"\n🤖 JSO HR Intelligence Agent ready. Hello, {hr_name}!")
        print("   Type your question in plain English. Type 'exit' to quit.\n")

    def ask(self, query: str) -> dict:
        """
        Main entry point. Process a natural language HR query.

        Args:
            query: Plain English question from the HR consultant.

        Returns:
            Structured result dict with response data and formatted output.
        """
        print(f"\n💬 You: {query}")
        print("   🔄 Thinking...\n")

        # Step 1: Classify intent
        intent_data = classify_intent(query, self.conversation_history)
        intent = intent_data.get("intent", "sql")
        confidence = intent_data.get("confidence", 0.5)

        print(f"   🎯 Intent: {intent} (confidence: {confidence:.0%})")

        # Step 2: Route to correct agent
        result = self._route(query, intent_data)

        # Step 3: Format and display
        formatted = self._format_result(result)
        print(formatted)

        # Step 4: Update conversation history
        self.conversation_history.append({"role": "user", "content": query})
        self.conversation_history.append({
            "role": "assistant",
            "content": f"Query type: {intent}. Found {result.get('row_count', result.get('total_found', 0))} results."
        })
        self.last_result = result

        # Step 5: Log to DB
        if LOG_QUERIES:
            self._log_query(query, intent, result)

        return result

    def _route(self, query: str, intent_data: dict) -> dict:
        """Routes the query to the correct specialised agent."""
        intent = intent_data.get("intent", "sql")
        sem_params = intent_data.get("semantic_params", {})
        sql_params = intent_data.get("sql_params", {})

        if intent == "semantic":
            if not _should_use_semantic(intent, query, sem_params):
                # Fallback to SQL for short, structured queries
                result = run_text_to_sql(query, intent_data)
                if result.get("error") and "SQL Error" in result["error"]:
                    result = fix_and_retry(query, result["generated_sql"], result["error"])
                return result
            jd_text = sem_params.get("jd_text") or self._extract_jd_from_query(query)
            if not jd_text:
                return {"error": "Please provide a job description to search against.", "query_type": "error"}
            self.last_jd = jd_text
            return run_semantic_search(
                jd_text=jd_text,
                top_k=sem_params.get("top_k", 10),
                filters=sem_params.get("filters", {})
            )

        elif intent == "hybrid":
            if not _should_use_semantic(intent, query, sem_params):
                # Fallback to SQL for short, structured queries
                result = run_text_to_sql(query, intent_data)
                if result.get("error") and "SQL Error" in result["error"]:
                    result = fix_and_retry(query, result["generated_sql"], result["error"])
                return result
            jd_text = sem_params.get("jd_text") or self.last_jd
            if not jd_text:
                return {"error": "Please provide a job description for hybrid search.", "query_type": "error"}
            self.last_jd = jd_text
            return run_hybrid_search(
                jd_text=jd_text,
                sql_filters=sql_params.get("filters", {}),
                top_k=sem_params.get("top_k", 10)
            )

        elif intent == "compare":
            # Try to extract candidate IDs from query or use last result
            candidate_ids = self._extract_candidate_ids(query)
            jd_text = self.last_jd or self._extract_jd_from_query(query)
            if not candidate_ids:
                return {"error": "Please specify candidate IDs or names to compare.", "query_type": "error"}
            return run_candidate_comparison(candidate_ids, jd_text or "general software engineering role")

        elif intent == "explain":
            candidate_id = self._extract_candidate_id(query)
            if candidate_id:
                return explain_candidate(candidate_id, self.last_jd)
            return {"error": "Please specify a candidate ID to explain.", "query_type": "error"}

        elif intent == "stats":
            # Stats queries are handled via SQL
            result = run_text_to_sql(query, intent_data)
            if result.get("error") and "SQL Error" in result["error"]:
                result = fix_and_retry(query, result["generated_sql"], result["error"])
            return result

        else:
            # Default: SQL query
            result = run_text_to_sql(query, intent_data)
            if result.get("error") and "SQL Error" in result["error"]:
                print(f"   ⚠️  SQL Error detected, attempting auto-fix...")
                result = fix_and_retry(query, result["generated_sql"], result["error"])
            return result

    def _format_result(self, result: dict) -> str:
        """Formats the result into a clean terminal display."""
        lines = []
        query_type = result.get("query_type", "unknown")

        if result.get("error"):
            return f"   ❌ Error: {result['error']}"

        # ── SQL Results ──────────────────────────────────────────
        if query_type in ("sql", "stats"):
            if result.get("explanation"):
                lines.append(f"   📋 {result['explanation']}")
            lines.append(f"   🔍 SQL: {result.get('generated_sql', 'N/A')[:120]}...")
            lines.append(f"   📊 Results: {result.get('row_count', 0)} rows found\n")

            rows = result.get("rows", [])
            if rows:
                cols = result.get("columns", list(rows[0].keys()))
                display_cols = cols[:6]  # cap columns for readability

                # Header
                header = " | ".join(str(c).upper()[:18].ljust(18) for c in display_cols)
                lines.append(f"   {header}")
                lines.append("   " + "-" * len(header))

                # Rows
                for row in rows[:15]:  # show max 15 rows
                    line = " | ".join(str(row.get(c, ""))[:18].ljust(18) for c in display_cols)
                    lines.append(f"   {line}")

                if len(rows) > 15:
                    lines.append(f"\n   ... and {len(rows) - 15} more results.")

        # ── Semantic / Hybrid Results ───────────────────────────
        elif query_type in ("semantic", "hybrid"):
            if result.get("summary"):
                lines.append(f"   💡 {result['summary']}\n")

            lines.append(f"   🎯 Found {result.get('total_found', 0)} matching candidates:\n")
            candidates = result.get("candidates", [])

            for i, c in enumerate(candidates, 1):
                risk_icon = "🔴" if c["risk_score"] > 20 else "🟡" if c["risk_score"] > 10 else "🟢"
                lines.append(f"   {i:2}. {c['full_name']:<20} Match: {c['match_percent']:<8} "
                              f"Exp: {c['experience_years']}yr  GitHub: {c['github_score']}/10  "
                              f"Risk: {risk_icon}  Location: {c['location']}")
                top_skills = ", ".join(s.split(" (")[0] for s in c["skills"][:4])
                lines.append(f"       Skills: {top_skills}")
                lines.append(f"       Salary: ${c['expected_salary']:,}  Available: {c['availability']}\n")

        # ── Comparison Results ──────────────────────────────────
        elif query_type == "compare":
            lines.append(f"\n   📊 CANDIDATE COMPARISON\n")
            lines.append(f"   {'Name':<22} {'Match':<10} {'Exp':<6} {'GitHub':<10} {'Salary':<12} {'Skills'}")
            lines.append("   " + "─" * 85)

            for c in result.get("comparison_table", []):
                skills = ", ".join(c.get("top_skills", [])[:3])
                lines.append(
                    f"   {c['full_name']:<22} {c['match_percent']:<10} "
                    f"{c['experience_years']}yr   {c['github_score']}/10      "
                    f"${c['expected_salary']:<10,} {skills}"
                )

            if result.get("recommendation"):
                lines.append(f"\n   🏆 Recommendation: {result['recommendation']}")

        # ── Explain Results ─────────────────────────────────────
        elif query_type == "explain":
            lines.append(f"\n   👤 Candidate Briefing: {result.get('full_name', '')}\n")
            lines.append(f"   {result.get('briefing', '')}")
            if result.get("skills"):
                lines.append(f"\n   🛠  Skills: {', '.join(result['skills'][:6])}")

        return "\n".join(lines)

    def _extract_jd_from_query(self, query: str) -> str | None:
        """
        If the query itself contains a job description (long text),
        extract it; otherwise return None.
        """
        if len(query) > 200:
            return query
        return None

    def _extract_candidate_ids(self, query: str) -> list[int]:
        """Extracts candidate IDs mentioned in a query like 'compare candidates 1, 3, 5'."""
        import re
        numbers = re.findall(r'\b(\d+)\b', query)
        ids = [int(n) for n in numbers if 1 <= int(n) <= 9999]
        return ids[:5]  # max 5 at a time

    def _extract_candidate_id(self, query: str) -> int | None:
        """Extracts a single candidate ID from a query."""
        import re
        numbers = re.findall(r'\b(\d+)\b', query)
        return int(numbers[0]) if numbers else None

    def _log_query(self, query: str, intent: str, result: dict) -> None:
        """Logs the query to the query_history table."""
        try:
            conn = get_connection(DB_PATH)
            conn.execute("""
                INSERT INTO query_history (hr_id, natural_language_query, generated_sql, query_type, result_count)
                VALUES (?, ?, ?, ?, ?)
            """, (
                self.hr_id,
                query,
                result.get("generated_sql", ""),
                intent,
                result.get("row_count", result.get("total_found", 0))
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass  # Logging failure shouldn't break the agent

    def get_session_summary(self) -> dict:
        """Returns a summary of the current session."""
        duration = (datetime.datetime.now() - self.session_start).seconds
        return {
            "hr": self.hr_name,
            "queries_asked": len(self.conversation_history) // 2,
            "session_duration_seconds": duration,
            "last_jd_used": self.last_jd[:100] + "..." if self.last_jd else None
        }
