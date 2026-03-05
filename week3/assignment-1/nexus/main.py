"""Nexus Multi-Agent Support — FastAPI entrypoint."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from router import router as nexus_router

BASE_PATH = os.environ.get("BASE_PATH", "")

app = FastAPI(
    title="Nexus Multi-Agent Support — Week 3",
    description="Multi-agent customer support system built with Google ADK, Supabase MCP, and A2A protocol.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(nexus_router)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/health")
def health():
    return {"status": "healthy", "service": "nexus-week3"}


@app.get("/", include_in_schema=False)
def serve_ui():
    html = (STATIC_DIR / "index.html").read_text()

    # Inject BASE_PATH for client-side routing
    inject = f'<script>window.__BASE_PATH__ = "{BASE_PATH}";</script>'
    html = html.replace("</head>", f"{inject}</head>")

    # Rewrite static paths to absolute
    rewrites = {
        'href="static/favicon.svg"': f'href="{BASE_PATH}/static/favicon.svg"',
        'href="static/style.css"': f'href="{BASE_PATH}/static/style.css"',
        'src="static/app.js"': f'src="{BASE_PATH}/static/app.js"',
    }
    for old, new in rewrites.items():
        html = html.replace(old, new)

    return HTMLResponse(html)


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
