# Job Search Optimiser

Monorepo with three related projects focused on job search, hiring workflows, and developer portfolio evaluation. Each subproject runs independently and has its own dependencies and runtime.

**Subprojects**
- `BOT_Detector`: Bot detection project (see folder for details).
- `crawler_agent`: Crawls GitHub repos and technical articles, then uses an LLM to generate review feedback.
- `Hiring_Assistant/cv-chat-ai`: TalentScout hiring assistant chatbot (FastAPI backend + React/Vite frontend).
- `HR_Project`: JSO HR Intelligence Agent (CLI workflow over a local SQLite candidate database).

**Top-Level Structure**
- `BOT_Detector/`
- `crawler_agent/`
- `Hiring_Assistant/`
- `HR_Project/`

## Quick Start
## 🛡️ Part B — Sentinel-JSO: AI Risk Monitoring Agent

Sentinel-JSO is an automated security agent that protects the JSO platform from fake accounts,
bot activity, and fraudulent recruitment. It assigns every user a dynamic risk score using a
4-signal weighted model (behavior · account linkage · content · device/IP), auto-escalates
high-risk accounts to the Super Admin dashboard, and powers a LangChain + Gemini AI
investigation pipeline that lets admins query any flagged account in plain English and receive
a full explainable report. Built with Flask, SQLite, and a Faker-generated dataset of 200 users,
1,800+ activity logs, and 15 bot clusters.

→ See [`/BOT_Detector/README.md`](./BOT_Detector/README.md) for full setup and documentation.
### 1) crawler_agent

**What it does**
- Fetches GitHub repo metadata, READMEs, and recent commits
- Optionally fetches and summarizes technical articles
- Produces review feedback using a configurable LLM provider

**Entry point**
- `crawler_agent/Github Crwaler Agent/main.py`

**Config**
- `crawler_agent/Github Crwaler Agent/config.yaml`

**Run (PowerShell)**
```bash
cd "crawler_agent/Github Crwaler Agent"
python main.py
```

**Notes**
- Required Python packages are inferred from imports in `crawler_agent/` (examples: `requests`, `PyYAML`, `newspaper3k`, `langchain-*`).
- Update `config.yaml` with your GitHub username, provider, model, and API keys.

---

### 2) Hiring_Assistant (TalentScout)

**What it does**
- Screens candidates by collecting required info
- Generates 3 to 5 technical questions based on candidate tech stack
- Supports OpenAI, Anthropic, and Gemini providers
- See [`/Hiring_Assistant/README.md`](./Hiring_Assistant/README.md) for full setup and documentation.

**Backend**
```bash
cd "Hiring_Assistant/cv-chat-ai/backend"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend**
```bash
cd "Hiring_Assistant/cv-chat-ai"
npm install
# create .env in this folder with:
# VITE_API_URL=http://localhost:8000
npm run dev
```

---

### 3) HR_Project (JSO HR Intelligence Agent)

**What it does**
- Conversational HR assistant to query a local SQLite candidate database
- Supports SQL, semantic search, hybrid search, comparisons, explanations, and stats
- Uses Anthropic Claude for intent classification and SQL generation
- See [`/HR_Project/README.md`](./HR_Project/README.md) for full setup and documentation.

**Run**
```bash
cd "HR_Project"
python setup_db.py
python main.py
```

**Configuration**
- Set `ANTHROPIC_API_KEY` in a `.env` file or environment variables.

**Known Issues (as of this repo state)**
- `HR_Project/main.py` and `HR_Project/orchestrator.py` import modules from `database/`, `agents/`, and `utils/` packages that are not present in this repo. The code is currently in a flat file layout. You may need to update imports (for example, `from setup_db import setup_database`, `from orchestrator import HRAgent`, `from config import ...`) or recreate those package directories.
- `HR_Project/config.py` points `DB_PATH` to `../database/jso_hr.db`, but the database file is located at `HR_Project/jso_hr.db` by default.

---

## Development Notes

- This repo contains multiple independent runtimes. Create separate virtual environments for Python projects and avoid sharing dependencies across them unless pinned.
- The `Hiring_Assistant/cv-chat-ai` frontend and backend are designed to run in two terminals.
- The `crawler_agent` uses direct API calls and LLM providers. Avoid committing real API keys into the repository.

## License

No top-level license file found. Individual subprojects may define their own licenses.

