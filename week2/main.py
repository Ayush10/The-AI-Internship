"""
Week 2 — RAG Document Q&A System
Standalone FastAPI app with interactive notebook + chat UI.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from rag.router import router as rag_router

BASE_PATH = os.environ.get("BASE_PATH", "")

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
    html = (STATIC_DIR / "index.html").read_text()
    inject = f'<script>window.__BASE_PATH__ = "{BASE_PATH}";</script>'
    html = html.replace("</head>", f"{inject}</head>")
    # Rewrite relative static paths to absolute so they work behind nginx subpath proxy
    for old, new in [
        ('href="static/favicon.svg"', f'href="{BASE_PATH}/static/favicon.svg"'),
        ('href="static/style.css"', f'href="{BASE_PATH}/static/style.css"'),
        ('src="static/app.js"', f'src="{BASE_PATH}/static/app.js"'),
    ]:
        html = html.replace(old, new)
    return HTMLResponse(html)


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
