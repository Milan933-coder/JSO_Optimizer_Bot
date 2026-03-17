"""
sentinel_agent.py — Sentinel-JSO AI Investigation Agent
Uses LangChain + Google Generative AI (Gemini) to reason about
user risk profiles and answer admin investigation queries.

Model: gemini-2.5-flash-preview  (set GEMINI_API_KEY in .env)
"""

import os
import json
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough

from database import get_user_by_id, get_flagged_users, get_stats

load_dotenv()

# ── Model setup ───────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_API_KEY_HERE")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-preview-05-20",   # gemini-2.5-flash-preview
    google_api_key=GEMINI_API_KEY,
    temperature=0.2,
    convert_system_message_to_human=True,
)

# ── Risk scoring helper ───────────────────────────────────────────────────────

def compute_risk_score(user_data: dict) -> dict:
    """
    Re-computes a structured risk breakdown from raw user data.
    Weights mirror the Sentinel-JSO scoring model:
      0.35 × Behavior   +  0.25 × Account Link
      0.20 × Content    +  0.20 × Device/IP
    """
    user   = user_data.get("user", {})
    logs   = user_data.get("logs", [])
    posts  = user_data.get("posts", [])
    clusters = user_data.get("clusters", [])

    # Behaviour anomaly (bulk actions, scraping)
    bulk_actions   = sum(1 for l in logs if "bulk" in l.get("metadata",""))
    scrape_actions = sum(1 for l in logs if l.get("action") == "scrape_content")
    multi_login    = sum(1 for l in logs if l.get("action") == "login")
    behavior_score = min(1.0, (bulk_actions * 0.15 + scrape_actions * 0.4 + max(0, multi_login - 1) * 0.2))

    # Account link risk (clusters)
    link_score = min(1.0, len(clusters) * 0.25)

    # Content scam score
    phishing_posts = sum(1 for p in posts if p.get("contains_phishing"))
    avg_scam       = (sum(p.get("scam_score", 0) for p in posts) / len(posts)) if posts else 0
    content_score  = min(1.0, phishing_posts * 0.4 + avg_scam * 0.6)

    # Device / IP risk (distinct IPs)
    unique_ips = len({l.get("ip_address") for l in logs if l.get("ip_address")})
    device_score = min(1.0, unique_ips * 0.2)

    final_score = round(
        0.35 * behavior_score +
        0.25 * link_score     +
        0.20 * content_score  +
        0.20 * device_score,
        4,
    )

    level = "Normal" if final_score < 0.40 else ("Suspicious" if final_score < 0.70 else "High Risk")

    return {
        "final_score":      final_score,
        "risk_level":       level,
        "behavior_score":   round(behavior_score, 4),
        "link_score":       round(link_score, 4),
        "content_score":    round(content_score, 4),
        "device_score":     round(device_score, 4),
    }


# ── Prompt templates ──────────────────────────────────────────────────────────

INVESTIGATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are Sentinel-JSO, an expert AI security analyst for a job platform.
Your role is to analyse user risk profiles and explain findings clearly to Super Admins.

Guidelines:
- Be concise and structured.
- Always state the Risk Score and Level first.
- List the top 3 most suspicious signals with brief explanations.
- Recommend a clear action: Monitor / Warn User / Suspend Account / Escalate.
- Use plain language — no jargon.
- If the user appears legitimate, say so confidently."""),

    ("human", """Investigate this user profile and answer the admin's question.

=== USER PROFILE ===
{profile_json}

=== RISK BREAKDOWN ===
{risk_breakdown}

=== ADMIN QUESTION ===
{question}

Provide a clear investigation report."""),
])

CLUSTER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are Sentinel-JSO. Analyse account cluster data to detect coordinated fraud networks."""),
    ("human", """Analyse this bot/fraud cluster and summarise the threat:

=== CLUSTER DATA ===
{cluster_json}

Describe: what kind of fraud this is, how many accounts are involved, shared infrastructure, and recommended action."""),
])

PLATFORM_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are Sentinel-JSO. Generate a concise platform security briefing for the Super Admin."""),
    ("human", """Platform stats: {stats_json}

Flagged users: {flagged_json}

Write a 4-sentence executive security summary covering: overall risk level, top threats, 
most dangerous users, and one recommended priority action."""),
])


# ── LangChain chains ──────────────────────────────────────────────────────────

investigation_chain = (
    RunnablePassthrough()
    | INVESTIGATION_PROMPT
    | llm
    | StrOutputParser()
)

cluster_chain = (
    RunnablePassthrough()
    | CLUSTER_PROMPT
    | llm
    | StrOutputParser()
)

summary_chain = (
    RunnablePassthrough()
    | PLATFORM_SUMMARY_PROMPT
    | llm
    | StrOutputParser()
)


# ── Public API ────────────────────────────────────────────────────────────────

def investigate_user(user_id: int, question: str = "Why was this user flagged?") -> dict:
    """
    Full investigation pipeline for a single user.
    Returns risk breakdown + Gemini narrative.
    """
    data = get_user_by_id(user_id)
    if not data:
        return {"error": f"User {user_id} not found"}

    risk = compute_risk_score(data)

    # Trim metadata for prompt (avoid token bloat)
    profile = {
        "id":           data["user"]["id"],
        "name":         data["user"]["name"],
        "email":        data["user"]["email"],
        "role":         data["user"]["role"],
        "location":     data["user"]["location"],
        "joined":       data["user"]["joined_date"],
        "stored_risk":  data["user"]["risk_score"],
        "activity_logs": data["logs"][:6],
        "job_apps":     data["apps"][:5],
        "job_posts":    data["posts"][:4],
        "clusters":     data["clusters"],
    }

    narrative = investigation_chain.invoke({
        "profile_json":   json.dumps(profile, indent=2),
        "risk_breakdown": json.dumps(risk, indent=2),
        "question":       question,
    })

    return {
        "user_id":    user_id,
        "user_name":  data["user"]["name"],
        "user_role":  data["user"]["role"],
        "risk":       risk,
        "narrative":  narrative,
    }


def analyse_cluster(cluster_id: str, accounts: list) -> str:
    """Analyse a known account cluster for coordinated fraud."""
    cluster_data = {"cluster_id": cluster_id, "accounts": accounts}
    return cluster_chain.invoke({"cluster_json": json.dumps(cluster_data, indent=2)})


def platform_security_summary() -> str:
    """Generate an executive platform security briefing."""
    stats   = get_stats()
    flagged = get_flagged_users()
    # Trim for prompt
    flagged_slim = [
        {"id": u["id"], "name": u["name"], "role": u["role"],
         "risk_score": u["risk_score"], "flag_reason": u["flag_reason"]}
        for u in flagged
    ]
    return summary_chain.invoke({
        "stats_json":   json.dumps(stats, indent=2),
        "flagged_json": json.dumps(flagged_slim, indent=2),
    })


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🔍  Investigating User 104 (Marcus Lee)…")
    result = investigate_user(104)
    print(json.dumps(result["risk"], indent=2))
    print("\n", result["narrative"])

    print("\n\n📊  Platform Security Summary…")
    print(platform_security_summary())
