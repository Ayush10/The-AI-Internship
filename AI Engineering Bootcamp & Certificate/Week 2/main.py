"""
Week 2 — RAG Document Q&A System
Standalone FastAPI app with interactive notebook + chat UI.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from rag.router import router as rag_router

app = FastAPI(
    title="RAG Document Q&A — Week 2",
    summary="Interactive RAG pipeline over reinforcement learning research papers.",
    description="""## RAG Q&A System

A fully interactive notebook + chat interface built on 10 RL research papers.

**Stack:** GLM-5 (Ollama) | Qwen3-Embedding-8B | ChromaDB | LangChain

### Features
- Interactive notebook with 6-step RAG pipeline
- Live Q&A chat with hybrid BM25 + vector search
- Dual evaluation: improved heuristics + LLM-as-judge
- Metadata filtering by topic, year, venue
""",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(rag_router)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/health")
def health():
    return {"status": "healthy", "service": "rag-qa-week2"}


@app.get("/", include_in_schema=False)
def serve_ui():
    return FileResponse(str(STATIC_DIR / "index.html"))


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
