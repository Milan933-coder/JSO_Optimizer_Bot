"""
config.py
=========
Central configuration for the JSO HR Intelligence Agent.
Set your API key in a .env file or as an environment variable.
"""

import os
from dotenv import load_dotenv

# Load .env from project root (current working dir) and from utils/.env
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ── Google Gemini ──────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not GOOGLE_API_KEY:
    print("WARNING: GOOGLE_API_KEY is not set. Add it to .env or utils/.env.")
GEMINI_MODEL       = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_MAX_TOKENS  = int(os.getenv("GEMINI_MAX_TOKENS", "2048"))
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL      = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
CLAUDE_MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "2048"))

# ── Database ───────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "jso_hr.db")

# ── Embeddings ─────────────────────────────────────────────
EMBEDDING_MODEL     = "sentence-transformers/all-MiniLM-L6-v2"  # local, free
TOP_K_RESULTS       = 10   # how many cosine similarity results to return
SIMILARITY_THRESHOLD = 0.3  # minimum score to include in results
ENABLE_SEMANTIC     = os.getenv("ENABLE_SEMANTIC", "true").lower() in ("1", "true", "yes")
SEMANTIC_MIN_QUERY_CHARS = int(os.getenv("SEMANTIC_MIN_QUERY_CHARS", "200"))

# ── Agent Behaviour ────────────────────────────────────────
MAX_QUERY_HISTORY   = 50   # how many past queries to remember per session
EXPLAIN_SQL         = True  # whether agent should explain the SQL it generates
SAFE_MODE           = True  # if True, only SELECT queries are allowed (no writes)

# ── Logging ────────────────────────────────────────────────
LOG_QUERIES         = True
LOG_FILE            = "hr_agent.log"
