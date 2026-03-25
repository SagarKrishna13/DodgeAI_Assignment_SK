# Graph-Based SAP O2C Query System

A system that converts natural language queries into SQL over SAP Order-to-Cash data and visualizes results as a dynamic, interactive graph.

---

## Description

This project enables business users to ask plain-English questions about SAP Order-to-Cash (O2C) processes. The system translates the question into SQL using an LLM, executes it over a SQLite database, and visualizes the relevant documents (Orders, Deliveries, Invoices, Payments, Customers) as a highlighted subgraph on a Vis.js network.

---

## Features

- **Natural Language to SQL** — Powered by Groq's `llama-3.1-8b-instant` LLM
- **Schema-Aware Prompting** — Explicit column notes and table definitions injected into every prompt
- **Join Dictionary** — Pre-built SAP O2C join relationships enforced in all SQL generation
- **Graph Visualization** — Interactive Vis.js network with 1000+ O2C document nodes
- **Subgraph Extraction** — Query results dynamically highlight relevant graph paths in real-time
- **Guardrails** — Domain restriction (SAP O2C only), read-only enforcement, SQLite date arithmetic rules

---

## Architecture

```
User Query (Natural Language)
        |
        v
  FastAPI Backend (/query)
        |
        v
  LLM (Groq API) — Schema-aware prompting + guardrails
        |
        v
  SQL Execution (SQLite)
        |
        v
  Entity ID Extraction
        |
        v
  Subgraph API (/subgraph)
        |
        v
  Vis.js Graph — Highlighted subgraph rendered in browser
```

| Layer | Technology |
|---|---|
| Backend | FastAPI + Uvicorn |
| LLM | Groq API (`llama-3.1-8b-instant`) |
| Database | SQLite (auto-generated on startup from JSONL data) |
| Frontend | Vanilla JS + Vis.js Network |
| Data Ingestion | Pandas |

---

## How to Run Locally

### Prerequisites
- Python 3.10+
- A [Groq API key](https://console.groq.com)
- SAP O2C JSONL data files placed inside a `data/` folder

```bash
# 1. Clone the repository
git clone https://github.com/SagarKrishna13/DodgeAI_Assignment_SK.git
cd DodgeAI_Assignment_SK

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your Groq API key (create a .env file)
echo GROQ_API_KEY=your_key_here > .env

# 5. Start the server
uvicorn app.main:app --reload

# 6. Open browser
# http://127.0.0.1:8000
```

On startup, the app automatically ingests all JSONL files in `data/` into a local SQLite database.

---

## Deployment

This project is designed for **Render** deployment.

1. Push this repo to GitHub.
2. Create a new **Web Service** on [Render](https://render.com).
3. Connect your GitHub repository.
4. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port 10000`
5. Add environment variable `GROQ_API_KEY` in the Render dashboard.
6. Deploy!

> **Note:** Since `data/` and `*.db` are excluded from the repo via `.gitignore`, you must either mount a persistent disk with your data files or pre-seed the database as part of deployment.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the frontend UI |
| `GET` | `/schema_graph` | Returns high-level O2C entity-relationship graph |
| `GET` | `/graph/full` | Returns the full sampled O2C document graph |
| `POST` | `/query` | Natural language → SQL → answer + highlighted entity IDs |
| `POST` | `/subgraph` | Accepts entity IDs → returns connected subgraph |

### POST `/query` Example

```json
// Request
{ "question": "Show the highest value sales order and its customer." }

// Response
{
  "answer": "The highest value order is 740509 for customer 310000109 with $19,021.27.",
  "sql": "SELECT soh.salesOrder, soh.soldToParty, CAST(soh.totalNetAmount AS FLOAT)...",
  "highlighted_ids": ["740509", "310000109"]
}
```

---

## Project Structure

```
sap-o2c-graph/
├── app/
│   ├── main.py              # FastAPI entrypoint, routing, static file serving
│   ├── config.py            # Environment variable loading (GROQ_API_KEY)
│   ├── db/                  # SQLite connection + schema extraction
│   ├── graph/               # Full graph, schema graph, subgraph builders
│   ├── guardrails/          # Domain check + SQL safety validator
│   ├── ingestion/           # JSONL → SQLite ingestion pipeline
│   └── llm/                 # Groq prompt builder + query engine
├── static/
│   └── index.html           # Vis.js frontend + chat UI
├── requirements.txt
└── README.md
```
