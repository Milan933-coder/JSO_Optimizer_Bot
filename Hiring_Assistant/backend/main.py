# =============================================================================
# main.py
# TalentScout — FastAPI Backend Entry Point
# Run: uvicorn main:app --reload --port 8000
# =============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.talentscout_chat import router as talentscout_router
from coding_round.router import router as coding_round_router

app = FastAPI(
    title       = "TalentScout API",
    description = "AI-powered hiring assistant — supports OpenAI, Anthropic & Gemini",
    version     = "1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",   # Vite frontend
        "http://localhost:3000",
        "http://127.0.0.1:8080",
    ],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(talentscout_router, prefix="/api/talentscout", tags=["TalentScout"])
app.include_router(coding_round_router, prefix="/api/talentscout/coding-round", tags=["CodingRound"])

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/")
def health_check():
    return {
        "status"  : "ok",
        "message" : "TalentScout backend is running 🚀",
        "docs"    : "http://localhost:8000/docs",
    }
