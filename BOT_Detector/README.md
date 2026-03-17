# 🛡️ Sentinel-JSO — AI Risk Monitoring Agent

> An automated platform security agent that detects fake accounts, bot activity, and fraudulent recruitment patterns using LangChain + Google Gemini AI, with a real-time Super Admin dashboard.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [Risk Scoring Model](#risk-scoring-model)
- [Database Schema](#database-schema)
- [How the AI Agent Works](#how-the-ai-agent-works)
- [Dashboard Guide](#dashboard-guide)
- [Configuration](#configuration)
- [Generated Dataset Summary](#generated-dataset-summary)

---

## Overview

Sentinel-JSO is the security backbone of the JSO (Job Seeker & Opportunity) platform. It continuously monitors all user activity — job applications, logins, recruiter posts, and content uploads — and assigns every account a dynamic risk score.

When a score crosses a threshold, the agent automatically escalates the account to the Super Admin dashboard with a full AI-generated investigation report explaining exactly why the account was flagged, what signals triggered it, and what action should be taken.

The agent is built as a **Python + Flask** backend with a **LangChain + Gemini AI** reasoning pipeline, a **SQLite** database seeded with **Faker-generated** realistic dummy data, and a dark-themed **Super Admin dashboard** frontend.

---

## Features

| Feature | Description |
|---|---|
| **Real-time risk scoring** | Every user gets a 0.0–1.0 dynamic risk score updated from live activity signals |
| **4-signal detection model** | Behavior anomaly · Account link clustering · Content scam analysis · Device/IP risk |
| **Auto-escalation** | Accounts scoring ≥ 0.85 are automatically escalated to the admin feed |
| **Gemini AI investigation** | Admins can ask natural-language questions about any user and receive a full AI report |
| **Bot network detection** | Graph-based clustering groups accounts sharing IPs, devices, or resume embeddings |
| **Phishing post scanner** | Job posts are scored for scam links, fraudulent offers, and suspicious patterns |
| **Faker-generated dataset** | 200 users · 1,800+ logs · 2,400+ applications · 200+ posts · 15 bot clusters |
| **Explainable AI decisions** | Every flag includes the specific signals, weights, and reasoning behind it |

---

## Project Structure

```
sentinel_jso/
│
├── app.py                  ← Flask REST API server (6 endpoints)
├── database.py             ← SQLite schema + Faker data generation
├── sentinel_agent.py       ← LangChain + Gemini AI investigation agent
│
├── templates/
│   └── index.html          ← Super Admin dashboard (vanilla JS, dark theme)
│
├── requirements.txt        ← Python dependencies
├── .env.example            ← Environment variable template
└── README.md               ← This file
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **AI / LLM** | Google Gemini 2.5 Flash (`gemini-2.5-flash-preview-05-20`) |
| **AI Framework** | LangChain (`langchain`, `langchain-google-genai`) |
| **Backend** | Python 3.10+ · Flask 3.0 · Flask-CORS |
| **Database** | SQLite (via Python `sqlite3`) |
| **Data Generation** | Faker 24+ |
| **Frontend** | Vanilla HTML/CSS/JS · JetBrains Mono · Syne font |
| **Environment** | `python-dotenv` |

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- A free Google Gemini API key — get one at [aistudio.google.com](https://aistudio.google.com/app/apikey)

### Installation

**1. Clone or download the project**

```bash
cd sentinel_jso
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Set up your environment**

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder with your real key:

```env
GEMINI_API_KEY=your_actual_api_key_here
```

**4. Generate the database**

```bash
python database.py
```

This creates `sentinel_jso.db` with 200 Faker-generated users, 1,800+ activity logs, 2,400+ job applications, 200+ job posts, and 15 bot clusters. You should see:

```
Generating users with Faker...
  60 HR users, 140 job seekers
Generating activity logs...
  1814 activity logs
...
Database ready at 'sentinel_jso.db'
```

**5. Start the server**

```bash
python app.py
```

**6. Open the dashboard**

Visit [http://localhost:5000](http://localhost:5000)

---

## API Reference

All endpoints return JSON. The frontend consumes these directly.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the Super Admin dashboard HTML |
| `GET` | `/api/stats` | Platform-wide risk statistics |
| `GET` | `/api/users` | All users sorted by risk score descending |
| `GET` | `/api/users?role=HR` | Filter users by role (`HR` or `JobSeeker`) |
| `GET` | `/api/users/flagged` | Only flagged/suspicious accounts |
| `GET` | `/api/users/<id>` | Full profile with logs, applications, posts, clusters |
| `POST` | `/api/investigate/<id>` | Run Gemini AI investigation on a user |
| `GET` | `/api/summary` | Generate an executive platform security briefing |
| `GET` | `/api/health` | Health check — returns agent version |

### Investigation endpoint

`POST /api/investigate/<user_id>`

Optional request body:
```json
{
  "question": "Why was this user flagged? Is suspension warranted?"
}
```

Response:
```json
{
  "user_id": 204,
  "user_name": "Monica Kerr",
  "user_role": "JobSeeker",
  "risk": {
    "final_score": 0.9125,
    "risk_level": "High Risk",
    "behavior_score": 0.97,
    "link_score": 0.75,
    "content_score": 0.0,
    "device_score": 0.4
  },
  "narrative": "Risk Score: 0.91 — HIGH RISK\n\nTop signals:\n1. 160 job applications submitted in under 6 minutes..."
}
```

---

## Risk Scoring Model

Every account is scored using a weighted formula across four independent signals:

```
Risk Score = (0.35 × Behavior) + (0.25 × Account Link) + (0.20 × Content) + (0.20 × Device/IP)
```

| Signal | Weight | What it measures |
|---|---|---|
| **Behavior anomaly** | 35% | Bulk job applications, content scraping, abnormal login frequency |
| **Account link risk** | 25% | Shared IP addresses, device fingerprints, duplicate resume embeddings |
| **Content scam score** | 20% | Phishing links in posts, scam recruitment forms, misleading job ads |
| **Device / IP risk** | 20% | Distinct IP count, geographic anomalies, flagged device fingerprints |

### Risk levels

| Score range | Status | Action |
|---|---|---|
| 0.00 – 0.40 | 🟢 Normal | No action required |
| 0.40 – 0.70 | 🟡 Suspicious | Monitor closely |
| 0.70 – 1.00 | 🔴 High Risk | Review and investigate |
| ≥ 0.85 | 🚨 Critical | **Auto-escalated to admin feed** |

> **Important:** All four sub-scores are computed entirely in Python using SQL query results. The LLM receives only the pre-computed numbers — it never counts, sums, or does arithmetic. See `sentinel_agent.py → compute_risk_score()`.

---

## Database Schema

### `users`
Stores both HR recruiters and Job Seekers.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Unique user ID (1–60 = HR, 200–339 = Seekers) |
| `name` | TEXT | Faker-generated full name |
| `email` | TEXT | Faker-generated email |
| `role` | TEXT | `HR` or `JobSeeker` |
| `risk_score` | REAL | Pre-computed risk score (0.0–1.0) |
| `risk_level` | TEXT | `Normal` / `Suspicious` / `High Risk` |
| `flagged` | INTEGER | `1` if flagged for review |
| `flag_reason` | TEXT | Human-readable flag explanation |

### `activity_logs`
Raw platform telemetry events per user.

| Column | Description |
|---|---|
| `action` | Event type: `apply_job`, `login`, `scrape_content`, `post_job`, etc. |
| `ip_address` | IPv4 address at time of action |
| `device_id` | Device fingerprint identifier |
| `metadata` | JSON blob with event-specific details (speed, bot_prob, country, etc.) |

### `job_applications`
One row per application submitted by a Job Seeker.

### `job_posts`
One row per job posted by an HR user — includes `contains_phishing` flag and `scam_score`.

### `account_clusters`
Maps accounts to bot clusters. Multiple accounts share the same `cluster_id`, `shared_ip`, and `shared_device`.

---

## How the AI Agent Works

The agent (`sentinel_agent.py`) uses three separate **LangChain chains**, each backed by Gemini:

### 1. `investigation_chain`
Triggered when an admin investigates any user.

- Fetches the full user profile from SQLite
- Computes the 4-signal risk breakdown in Python
- Assembles a structured `ChatPromptTemplate` with profile JSON + risk scores + admin's question
- Gemini returns a plain-language report with: risk score, top signals, recommended action

### 2. `cluster_chain`
Analyses a detected bot network cluster.

- Receives cluster data (accounts, shared IPs, shared devices)
- Gemini identifies the fraud type, scope, and recommended response

### 3. `summary_chain`
Generates the executive platform security briefing (AI Briefing tab).

- Receives platform-wide stats + all flagged user summaries
- Gemini writes a 4-sentence executive briefing covering overall risk level, top threats, most dangerous accounts, and one priority action

---

## Dashboard Guide

The Super Admin dashboard has four sections accessible from the left sidebar:

**Risk Feed** — Live table of all users sorted by risk score. Click any row to load their profile in the Investigation panel. Type a question and press Ask to run a Gemini investigation.

**All Users** — Full platform user table with filter tabs for HR / Job Seekers. Shows ID, email, location, risk score, status, and flag indicator.

**Flagged Accounts** — Filtered view of all accounts with `flagged = 1`. Each row shows the flag reason and a direct Investigate button.

**AI Briefing** — Calls `/api/summary` to generate a live Gemini executive security briefing summarising the current platform risk state in plain English.

---

## Configuration

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | ✅ Yes | Your Google Gemini API key |

Set it in `.env`:
```env
GEMINI_API_KEY=AIzaSy...
```

The app will still run without the key — the dashboard, database, and all stats will work. Only the `/api/investigate` and `/api/summary` endpoints require it and will return a helpful error message if the key is missing.

---

## Generated Dataset Summary

Running `python database.py` produces a fixed-seed (`seed=42`) reproducible dataset:

| Table | Rows | Notes |
|---|---|---|
| Users | 200 | 60 HR + 140 Job Seekers; 70% normal / 18% suspicious / 12% high-risk |
| Activity logs | ~1,800 | Volume scales with risk level: 2–8 logs (normal) up to 50 (high-risk) |
| Job applications | ~2,400 | Bots generate 80–200 burst applications; normal seekers generate 1–5 |
| Job posts | ~200 | High-risk HR accounts have a 70% chance of phishing content per post |
| Bot clusters | 108 memberships | 15 named clusters (C01–C15) with shared IPs and device fingerprints |

Re-running `python database.py` always produces the same data, making it suitable for consistent testing and demos.
