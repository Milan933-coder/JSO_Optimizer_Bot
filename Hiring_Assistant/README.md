# 🎯 TalentScout — AI Hiring Assistant Chatbot

TalentScout is an intelligent hiring assistant chatbot that screens tech candidates by collecting their information and generating tailored technical interview questions based on their declared tech stack. Built with **FastAPI** (backend) and **React + Vite** (frontend), it supports **OpenAI**, **Anthropic (Claude)**, **Google Gemini**, and **ElevenLabs** for voice replies.

---

## 📋 Table of Contents

- [Project Overview](#-project-overview)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Usage Guide](#-usage-guide)
- [API Reference](#-api-reference)
- [Prompt Design](#-prompt-design)
- [Challenges & Solutions](#-challenges--solutions)

---

## 🧠 Project Overview

TalentScout automates the initial screening of tech candidates for recruitment agency **TalentScout**. The chatbot:

1. Greets the candidate and explains the process
2. Collects 7 essential candidate details before proceeding
3. Generates 3–5 tailored technical questions based on the candidate's tech stack
4. Handles off-topic responses with a 3-strike warning system
5. Gracefully concludes the session with next steps

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 **Info Token System** | Interview is locked until all 7 candidate fields are provided |
| 🤖 **Multi-Provider AI** | Supports OpenAI GPT-4o, Anthropic Claude, Google Gemini |
| 🔐 **Backend `.env` Keys** | OpenAI, Anthropic, Gemini, Whisper, ElevenLabs, and Judge0 can be configured once in `.env` |
| ❓ **Dynamic Questions** | 3–5 tech questions generated from the candidate's exact stack |
| ⚠️ **3-Strike Deviation Guard** | Off-topic replies trigger warnings; 3rd strike ends the session |
| 👋 **Graceful Exit** | Keywords like "bye", "exit", "quit" end the session politely |
| 🔄 **Context Awareness** | Full conversation history maintained for coherent flow |
| 🚫 **Session Termination** | Uncooperative candidates are blocked with a professional message |
| 🎉 **Closing Message** | Personalised thank-you with next steps after all questions |

---

## 🛠 Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI** — REST API framework
- **Uvicorn** — ASGI server
- **Pydantic v2** — Request/response validation
- **OpenAI SDK** — GPT-4o integration
- **Anthropic SDK** — Claude integration
- **Google Generative AI SDK** — Gemini integration

### Frontend
- **React 18** + **TypeScript**
- **Vite** — Build tool (port 8080)
- **Tailwind CSS** — Styling
- **shadcn/ui** — UI components
- **TanStack Query** — Data fetching
- **React Router v6** — Routing

---

## 📁 Project Structure

```
cv-chat-ai/                          ← repo root
│
├── src/                             ← React frontend
│   ├── pages/
│   │   └── Chat.tsx                 ← Main chat page (provider selector + chat UI)
│   ├── hooks/
│   │   └── useTalentScout.ts        ← Session management hook
│   ├── components/
│   │   └── chat/
│   │       ├── ChatMessages.tsx     ← Message display
│   │       └── ChatInput.tsx        ← Message input box
│   └── lib/
│       └── api.ts                   ← Backend URL config
│
├── backend/                         ← FastAPI backend
│   ├── main.py                      ← App entry point + CORS
│   ├── requirements.txt
│   ├── models/
│   │   └── schemas.py               ← Pydantic request/response models
│   ├── routes/
│   │   └── talentscout_chat.py      ← /start and /message endpoints
│   ├── services/
│   │   ├── ai_service.py            ← Multi-provider AI wrapper
│   │   └── conversation_manager.py ← Token system + state machine
│   └── prompts/
│       └── talentscout_prompts.py   ← All AI prompts & messages
│
├── .env                             ← frontend URL + backend provider keys
├── vite.config.ts
└── package.json
```

---

## 🚀 Installation

### Prerequisites
- **Node.js** 18+ and **npm**
- **Python** 3.11+
- API key for at least one provider (OpenAI / Anthropic / Gemini)

---

### 1. Clone the repository

```bash
git clone https://github.com/Milan933-coder/cv-chat-ai.git
cd cv-chat-ai
```

---

### 2. Create the Environment File

Create `Hiring_Assistant/.env` and add the keys you want to use:

```env
VITE_API_URL=http://localhost:8000

OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
WHISPER_API_KEY=

ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL
ELEVENLABS_MODEL_ID=eleven_multilingual_v2

JUDGE0_API_KEY=
JUDGE0_BASE_URL=https://ce.judge0.com
```

Notes:
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `GEMINI_API_KEY` are used as provider defaults.
- `WHISPER_API_KEY` is optional. If it is empty, the backend falls back to `OPENAI_API_KEY`.
- `ELEVENLABS_API_KEY` enables voice replies.
- UI-entered keys still work and override the `.env` values for that session.

### 3. Setup the Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload --port 8000
```

✅ Backend running at: `http://localhost:8000`
📖 API docs at: `http://localhost:8000/docs`

---

### 4. Setup the Frontend

Open a **new terminal** in the repo root:

```bash
# Install dependencies
npm install

# Start the dev server
npm run dev
```

✅ Frontend running at: `http://localhost:8080`

---

## 📖 Usage Guide

1. **Open** `http://localhost:8080` in your browser
2. **Select** an AI provider from the sidebar (OpenAI / Anthropic / Gemini)
3. **Either** use the backend `.env` keys **or** enter a key manually in the sidebar
4. The chatbot **greets** you and asks for your details
5. **Provide** all 7 required fields:
   - Full Name
   - Email Address
   - Phone Number
   - Years of Experience
   - Desired Position(s)
   - Current Location
   - Tech Stack
6. Once all info is collected, the **technical interview begins**
7. Answer **3–5 questions** tailored to your tech stack
8. Session **closes** with a personalised thank-you message

> ⚠️ Going off-topic 3 times will terminate the session.
> Type `bye`, `exit`, or `quit` to leave at any time.

---

## 🔌 API Reference

### `POST /api/talentscout/start`
Creates a new session and returns the greeting message.

**Request:**
```json
{
  "provider": "openai",
  "api_key": "sk-..."
}
```

**Response:**
```json
{
  "session_id": "uuid-string",
  "reply": "👋 Hello! Welcome to TalentScout...",
  "phase": "INFO_PENDING"
}
```

---

### `POST /api/talentscout/message`
Sends a user message and gets the AI reply.

**Request:**
```json
{
  "session_id": "uuid-string",
  "provider": "openai",
  "api_key": "sk-...",
  "message": "Hi, I'm Milan..."
}
```

**Response:**
```json
{
  "session_id": "uuid-string",
  "reply": "Great to meet you, Milan!...",
  "phase": "INTERVIEWING",
  "is_closed": false
}
```

> When `is_closed: true` — the session has ended and the input is locked.

---

## ✏️ Prompt Design

All prompts live in `backend/prompts/talentscout_prompts.py`.

### Info Collection Prompt
Uses a strict system prompt that instructs the LLM to:
- Collect all 7 fields before proceeding
- Return the exact phrase *"Please provide the information about yourself."* if fields are missing
- Output the `[INFO_TOKEN: ENABLED]` marker once all fields are confirmed

### Question Generation Prompt
A separate JSON-mode prompt that generates 3–5 questions covering:
- Different technologies in the candidate's stack
- Varying difficulty: foundational → intermediate → advanced
- Questions answerable in 2–5 sentences (not coding challenges)

### Interview System Prompt
Instructs the LLM to:
- Acknowledge answers in 1–2 sentences only (no follow-up questions)
- Output `[DEVIATION_COUNT: N]` marker when candidate goes off-topic
- Output `[INTERVIEW_COMPLETE]` when all questions are answered

### Deviation Handling
The route code, not the LLM, enforces the 3-strike limit:
- Strike 1 & 2 → warning with question restated
- Strike 3 → `SESSION_TERMINATED` message, session purged

---

## 🧩 Challenges & Solutions

| Challenge | Solution |
|---|---|
| LLM asking 2 questions at once | Added `_strip_llm_question()` to remove any `?`-ending sentences from LLM reply before appending our question |
| `proxies` error with Anthropic SDK | Pinned `httpx==0.27.0` to fix SDK conflict |
| Blank white screen on load | Fixed `vite.config.ts` to use `@vitejs/plugin-react-swc` and added `target: 'esnext'` |
| API key security | Keys are never stored — sent per-request directly to provider SDK |
| Session state across requests | In-memory session store keyed by UUID; sessions purged on close (GDPR compliant) |
| LLM ignoring prompt instructions | Used marker-based control system — route code reads `[MARKERS]` from LLM output and enforces all state transitions |

---

## 🔒 Data Privacy

- API keys can now be supplied through backend `.env` or passed per request from the UI
- Candidate session data is **purged from memory** when the session closes
- No data is written to disk or any external database
- Compliant with GDPR data minimisation principles

---

## 📄 License

MIT License — free to use and modify.

---

*Built for the PG-AGI AI/ML Intern Assignment — TalentScout Hiring Assistant*
