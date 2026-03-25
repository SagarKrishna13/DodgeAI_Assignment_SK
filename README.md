# Dodge AI — SAP Order-to-Cash Graph Explorer

An intelligent, interactive graph visualization system for SAP Order-to-Cash (O2C) data. Ask natural language questions and watch the graph highlight the relevant business documents in real-time.

---

## Features

- **Natural Language Querying** — Powered by Groq's `llama-3.1-8b-instant` LLM, translate plain English questions into accurate SQL.
- **Dynamic Graph Visualization** — Vis.js network graph with 1,000+ O2C nodes (Orders, Deliveries, Invoices, Payments, Customers).
- **Real-time Subgraph Highlighting** — When a query returns results, the UI automatically animates and highlights the relevant nodes while fading the background.
- **SQLite Guardrails** — Strict prompt rules prevent SQL hallucinations and MySQL/PostgreSQL-specific syntax errors.
- **Read-only Guardrail** — Rejects any attempt to INSERT, UPDATE, or DELETE data.
- **Domain Guardrail** — Restricts the agent to SAP O2C data only; ignores off-topic questions.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Uvicorn |
| LLM | Groq API (`llama-3.1-8b-instant`) |
| Database | SQLite (auto-generated on startup) |
| Frontend | Vanilla JS + Vis.js Network |
| Data Ingestion | Pandas (from JSONL files) |

---

## Run Locally

### Prerequisites
- Python 3.10+
- A [Groq](https://console.groq.com) API key

### Setup

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd sap-o2c-graph

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a .env file with your Groq API key
echo GROQ_API_KEY=your_key_here > .env

# 5. Place your JSONL data files in the data/ directory
#    (The app will auto-ingest them on startup)

# 6. Start the server
uvicorn app.main:app --reload

# 7. Open your browser
# http://127.0.0.1:8000
```

---

## Deployment on Render

1. Push this repo to GitHub.
2. Create a new **Web Service** on [Render](https://render.com).
3. Connect your GitHub repository.
4. Set the following configuration:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port 10000`
5. Add the environment variable `GROQ_API_KEY` in Render's dashboard.
6. Deploy!

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the frontend UI (`index.html`) |
| `GET` | `/graph/full` | Returns the full O2C graph dataset for initial rendering |
| `GET` | `/schema_graph` | Returns the high-level schema-only relationship graph |
| `POST` | `/query` | Accepts a natural language question; returns SQL + answer + highlighted entity IDs |
| `POST` | `/subgraph` | Accepts a list of entity IDs; returns the connected subgraph for highlighting |

### POST `/query` Example

```json
// Request
{ "question": "Show me the highest value sales order and its customer." }

// Response
{
  "answer": "The highest value sales order is 740509...",
  "sql": "SELECT soh.salesOrder, soh.soldToParty...",
  "highlighted_ids": ["740509", "310000109"]
}
```

---

## Project Structure

```
sap-o2c-graph/
├── app/
│   ├── main.py              # FastAPI app, routes, startup
│   ├── config.py            # Environment config (GROQ_API_KEY)
│   ├── db/
│   │   ├── connection.py    # SQLite connection factory
│   │   └── schema.py        # Schema extraction utility
│   ├── graph/
│   │   ├── full_graph.py    # Full O2C node/edge builder
│   │   ├── schema_graph.py  # Schema-level graph builder
│   │   └── subgraph.py      # Entity subgraph extractor
│   ├── guardrails/
│   │   └── sql_validator.py # SQL safety checks (SELECT-only, LIMIT enforcement)
│   ├── ingestion/
│   │   └── ingest.py        # JSONL → SQLite ingestion pipeline
│   └── llm/
│       ├── prompt.py        # System prompt, SQL rules, guardrails
│       └── query_engine.py  # Groq API call + SQL executor + ID extractor
├── static/
│   └── index.html           # Frontend (Vis.js + chat UI)
├── requirements.txt
└── README.md
```
