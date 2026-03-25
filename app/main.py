from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from typing import List, Optional
from pydantic import BaseModel

from app.ingestion.ingest import ingest_data
from app.llm.query_engine import query_groq
from app.graph.schema_graph import build_schema_graph
from app.graph.subgraph import fetch_subgraph
from app.graph.full_graph import build_full_graph

# ── Pydantic Request Models ───────────────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str
    history: Optional[List[dict]] = []

class SubgraphRequest(BaseModel):
    entity_ids: List[str]

# ── Startup lifecycle ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Startup: Running data ingestion...")
    ingest_data()
    print("Startup: Ingestion complete.")
    yield

# ── App Initialization ────────────────────────────────────────────────────────
app = FastAPI(
    title="SAP O2C Graph API",
    description="Modular backend for SAP Order-to-Cash graph analysis and NL querying.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────

# ── Static Files & Root ──────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
@app.get("/index.html")
async def read_index():
    return FileResponse("static/index.html")

@app.get("/schema_graph")
def schema_graph():
    """Returns the high-level O2C entity-relationship graph (no data loaded)."""
    return build_schema_graph()

    
@app.get("/graph/full")
def full_graph():
    """Returns a massive cohesive graph of actual sampled O2C documents."""
    return build_full_graph()


@app.post("/query")
async def query(request: QueryRequest):
    """
    Translates a natural language question to SQL, executes it,
    and returns a human-readable answer with highlighted graph IDs.
    """
    try:
        result = query_groq(request.question, request.history)
        return result
    except Exception as e:
        print(f"[/query] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/subgraph")
def subgraph(request: SubgraphRequest):
    """
    Fetches a focused data-level subgraph for the provided entity IDs.
    Traverses Customer → Order → Delivery → Invoice → Payment.
    """
    try:
        return fetch_subgraph(request.entity_ids)
    except Exception as e:
        print(f"[/subgraph] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
