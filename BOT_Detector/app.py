"""
app.py — Sentinel-JSO Flask Backend
REST API consumed by the Super Admin dashboard frontend.
"""

import os
import json
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

from database import (
    init_db, get_all_users, get_user_by_id,
    get_flagged_users, get_stats
)
from sentinel_agent import investigate_user, platform_security_summary

# ── Bootstrap ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

DB_PATH = "sentinel_jso.db"
if not os.path.exists(DB_PATH):
    init_db()


# ── Frontend ──────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


# ── REST API ──────────────────────────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    """Platform-wide risk statistics."""
    return jsonify(get_stats())


@app.route("/api/users")
def api_users():
    """All users, sorted by risk score descending."""
    role = request.args.get("role")          # ?role=HR or ?role=JobSeeker
    users = get_all_users()
    if role:
        users = [u for u in users if u["role"] == role]
    return jsonify(users)


@app.route("/api/users/flagged")
def api_flagged():
    """Only flagged / suspicious users."""
    return jsonify(get_flagged_users())


@app.route("/api/users/<int:user_id>")
def api_user_detail(user_id):
    """Full user profile with logs, apps, posts, clusters."""
    data = get_user_by_id(user_id)
    if not data:
        return jsonify({"error": "User not found"}), 404
    return jsonify(data)


@app.route("/api/investigate/<int:user_id>", methods=["POST"])
def api_investigate(user_id):
    """
    POST body (optional JSON): { "question": "Why was this user flagged?" }
    Runs Gemini investigation chain and returns narrative + risk breakdown.
    """
    body     = request.get_json(silent=True) or {}
    question = body.get("question", "Why was this user flagged? Provide a full investigation report.")

    try:
        result = investigate_user(user_id, question)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "hint": "Check GEMINI_API_KEY in .env"}), 500


@app.route("/api/summary", methods=["GET"])
def api_summary():
    """
    Returns Gemini-generated executive platform security summary.
    """
    try:
        summary = platform_security_summary()
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": str(e), "hint": "Check GEMINI_API_KEY in .env"}), 500


# ── Health check ───────────────────────────────────────────────────────────────
@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok", "agent": "Sentinel-JSO", "version": "1.0.0"})


if __name__ == "__main__":
    print("🛡️  Sentinel-JSO running → http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
