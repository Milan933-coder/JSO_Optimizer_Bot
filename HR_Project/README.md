# 🤖 JSO HR Intelligence Agent

A conversational AI agent for HR consultants to query candidate data using **plain English**.
No SQL knowledge required. Powered by **Claude (Anthropic)** + **cosine similarity embeddings**.

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your API key
Create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=your_api_key_here
```

### 3. Setup the database
```bash
python database/setup_db.py
```

### 4. Run the agent
```bash
python main.py               # Interactive mode
python main.py --reset-db    # Reset DB and start fresh
```

---

## 📁 Project Structure

```
hr_agent/
├── main.py                         ← Entry point, demo + interactive CLI
│
├── database/
│   ├── schema.sql                  ← All table definitions
│   ├── seed_data.sql               ← 15 dummy candidates, jobs, applications
│   └── setup_db.py                 ← DB initialiser + connection utility
│
├── agents/
│   ├── intent_classifier.py        ← Classifies query type (SQL/semantic/hybrid/etc)
│   ├── text_to_sql_agent.py        ← Converts English → SQL → executes
│   ├── semantic_search_agent.py    ← Cosine similarity CV ↔ JD matching
│   └── orchestrator.py             ← Main brain: routes queries, manages session
│
├── utils/
│   ├── config.py                   ← All settings and env vars
│   └── embeddings.py               ← Vector embeddings + cosine similarity
│
├── requirements.txt
└── README.md
```

---

## 💬 What You Can Ask

### SQL Queries (Structured Filters)
```
"Show me candidates with 5+ years experience"
"Find React developers in London or Mumbai"
"Who has been shortlisted for the Senior Dev job?"
"Show candidates with salary under $100,000"
"Find candidates flagged as high risk"
"How many applications were rejected this month?"
```

### Semantic Search (Paste a JD)
```
"Find candidates matching this job description:
 We need a Senior React Developer with TypeScript, Node.js,
 AWS experience and a background in financial applications..."
```

### Hybrid (Semantic + Filters)
```
"From candidates matching this JD, show only those
 with 5+ years experience in London"
```

### Compare Candidates
```
"Compare candidates 1, 3, 5 for the Senior React role"
```

### Explain a Candidate
```
"Explain candidate 5"
"Tell me about candidate 11"
```

### Stats & Analytics
```
"How many candidates do we have per location?"
"What is the average expected salary?"
"Which skills are most common in our candidate pool?"
```

---

## 🏗️ Architecture

```
HR types natural language query
            ↓
   Intent Classifier (Claude)
   → sql / semantic / hybrid / compare / explain / stats
            ↓
    ┌───────┴────────┐
    │                │
Text-to-SQL     Semantic Search
(Claude API)    (sentence-transformers)
    │                │
    ↓                ↓
 SQLite DB      pgvector-style
 (Supabase      cosine similarity
  in prod)      on CV embeddings
    │                │
    └───────┬────────┘
            ↓
    Formatted Results
    + Claude-generated explanation
```

---

## ⚙️ Configuration (`utils/config.py`)

| Setting | Default | Description |
|---|---|---|
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Model used for SQL gen + summaries |
| `TOP_K_RESULTS` | `10` | Max semantic search results |
| `SIMILARITY_THRESHOLD` | `0.3` | Min cosine score to include |
| `SAFE_MODE` | `True` | Only SELECT queries allowed |
| `EXPLAIN_SQL` | `True` | Claude explains generated SQL |
| `LOG_QUERIES` | `True` | Saves all queries to DB |

---

## 🔌 Production Integration (Next.js + Supabase)

Replace SQLite with **Supabase + pgvector**:

1. Enable `pgvector` extension in Supabase
2. Add `embedding vector(384)` column to `cvs` table
3. Replace `embeddings.py` similarity loop with:
   ```sql
   SELECT *, 1 - (embedding <=> '[...]') AS score
   FROM cvs ORDER BY score DESC LIMIT 10;
   ```
4. Expose agent as a **Node.js API route** (`/api/hr-agent`)
5. Call from HR dashboard via fetch on every message submit

---

## 🔐 Security Notes

- `SAFE_MODE = True` ensures only SELECT queries run (no data modification)
- All queries are logged to `query_history` table for audit
- HR consultant ID is tracked on every query
- API key is loaded from `.env`, never hardcoded
