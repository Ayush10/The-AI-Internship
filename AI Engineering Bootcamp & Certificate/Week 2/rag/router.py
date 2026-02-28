"""
FastAPI router for the RAG Q&A module.
"""

import io
import json
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).parent.parent

router = APIRouter(prefix="/api/rag", tags=["RAG Q&A"])


# --- Schemas ---

class RAGQueryRequest(BaseModel):
    question: str = Field(description="Question to ask the RAG system", examples=["How does DRQN handle partial observability?"])
    search_mode: Literal["vector", "hybrid"] = Field(default="hybrid")
    chunk_size: Literal[300, 500, 1000] = Field(default=500)
    num_results: int = Field(default=3, ge=1, le=10)
    topic_filter: Optional[str] = Field(default=None)


class RAGSource(BaseModel):
    content: str
    source: str
    topic: Optional[str] = None
    year: Optional[str] = None
    page: Optional[int] = None


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[RAGSource]
    search_mode: str
    chunk_size: int


class RAGRetrieveRequest(BaseModel):
    question: str = Field(description="Query for retrieval")
    search_mode: Literal["vector", "hybrid"] = Field(default="hybrid")
    chunk_size: Literal[300, 500, 1000] = Field(default=500)
    num_results: int = Field(default=3, ge=1, le=10)
    topic_filter: Optional[str] = Field(default=None)


class RAGEvalRequest(BaseModel):
    chunk_size: Literal[300, 500, 1000] = Field(default=500)
    search_mode: Literal["vector", "hybrid"] = Field(default="hybrid")
    use_llm_judge: bool = Field(default=True)
    use_heuristic: bool = Field(default=True)


class NotebookRunRequest(BaseModel):
    cell_id: str = Field(description="Cell ID to execute", examples=["step1_load"])
    code: Optional[str] = Field(default=None, description="User-edited code (parameter overrides)")


class NotebookCellOut(BaseModel):
    cell_id: str
    cell_type: Literal["markdown", "code"]
    step: Optional[int] = None
    content: str
    default_output: Optional[str] = None
    is_runnable: bool


class NotebookRunResponse(BaseModel):
    cell_id: str
    output: str
    error: Optional[str] = None
    execution_time: float


# --- Endpoints ---

@router.post(
    "/query",
    response_model=RAGQueryResponse,
    summary="RAG Q&A Query",
    description="Ask a question and get an answer grounded in the RL research papers.",
)
def rag_query(request: RAGQueryRequest):
    from rag.engine import query

    try:
        result = query(
            question=request.question,
            search_mode=request.search_mode,
            chunk_size=request.chunk_size,
            num_results=request.num_results,
            topic_filter=request.topic_filter,
        )
    except Exception as e:
        raise HTTPException(502, f"RAG pipeline error: {e}")

    return RAGQueryResponse(
        answer=result["answer"],
        sources=[RAGSource(**s) for s in result["sources"]],
        search_mode=result["search_mode"],
        chunk_size=result["chunk_size"],
    )


@router.post(
    "/retrieve",
    response_model=list[RAGSource],
    summary="Retrieve Chunks",
    description="Retrieve relevant chunks without LLM generation.",
)
def rag_retrieve(request: RAGRetrieveRequest):
    from rag.engine import retrieve

    try:
        results = retrieve(
            question=request.question,
            search_mode=request.search_mode,
            chunk_size=request.chunk_size,
            num_results=request.num_results,
            topic_filter=request.topic_filter,
        )
    except Exception as e:
        raise HTTPException(502, f"Retrieval error: {e}")

    return [RAGSource(**r) for r in results]


@router.post(
    "/evaluate",
    summary="Run Evaluation",
    description="Run the 5-question evaluation set with heuristic and/or LLM-as-judge scoring.",
)
def rag_evaluate(request: RAGEvalRequest):
    from rag.evaluator import run_evaluation

    try:
        results = run_evaluation(
            chunk_size=request.chunk_size,
            search_mode=request.search_mode,
            use_llm_judge=request.use_llm_judge,
            use_heuristic=request.use_heuristic,
        )
    except Exception as e:
        raise HTTPException(502, f"Evaluation error: {e}")

    return results


@router.get(
    "/notebook",
    response_model=list[NotebookCellOut],
    summary="Get Notebook Cells",
    description="Returns all notebook cells with pre-computed default outputs.",
)
def get_notebook():
    from rag.notebook_cells import NOTEBOOK_CELLS

    return [
        NotebookCellOut(
            cell_id=c["cell_id"],
            cell_type=c["cell_type"],
            step=c.get("step"),
            content=c["content"],
            default_output=c.get("default_output"),
            is_runnable=c.get("is_runnable", False),
        )
        for c in NOTEBOOK_CELLS
    ]


@router.post(
    "/notebook/run",
    response_model=NotebookRunResponse,
    summary="Run Notebook Cell",
    description="Execute a specific notebook cell server-side.",
)
def run_notebook_cell(request: NotebookRunRequest):
    from rag.notebook_runner import run_cell

    try:
        result = run_cell(request.cell_id, request.code)
    except Exception as e:
        raise HTTPException(502, f"Cell execution error: {e}")

    return NotebookRunResponse(
        cell_id=request.cell_id,
        output=result["output"],
        error=result.get("error"),
        execution_time=result["execution_time"],
    )


@router.get(
    "/eval/results",
    summary="Get Cached Evaluation Results",
    description="Returns pre-computed evaluation results.",
)
def get_eval_results():
    eval_path = BASE_DIR / "eval" / "eval_results.json"
    if not eval_path.exists():
        raise HTTPException(404, "Evaluation results not found.")

    with open(eval_path, "r") as f:
        return json.load(f)


# ═══════════════════════════════════════════
# AUTOPLAY + RESULTS + DOWNLOADS
# ═══════════════════════════════════════════

@router.get(
    "/autoplay",
    summary="Run Full Autoplay",
    description="SSE stream that runs the entire pipeline: notebook, chat, evaluation, charts.",
)
async def autoplay(theme: str = Query(default="dark", enum=["dark", "light"])):
    from rag.autoplay import run_autoplay_stream

    return StreamingResponse(
        run_autoplay_stream(theme),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get(
    "/results",
    summary="Get Autoplay Results",
    description="Returns the most recent autoplay results including charts and eval data.",
)
def get_autoplay_results():
    from rag.autoplay import get_cached_results

    results = get_cached_results()
    if not results:
        raise HTTPException(404, "No autoplay results available. Run autoplay first.")
    return results


@router.get(
    "/download/zip",
    summary="Download All Results as ZIP",
    description="Downloads a ZIP file containing notebook, README, results, process docs, and charts.",
)
def download_zip():
    from rag.autoplay import get_cached_results
    from rag.downloads import generate_zip

    results = get_cached_results()
    if not results:
        raise HTTPException(404, "No results available. Run autoplay first.")

    zip_buffer = generate_zip(
        eval_results=results["eval_results"],
        charts=results["charts"],
        chat_responses=results["chat_responses"],
        notebook_outputs=results["notebook_outputs"],
    )
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=week2_rag_results.zip"},
    )


@router.get(
    "/download/{filename}",
    summary="Download Individual File",
    description="Download a specific generated or source file.",
)
def download_file(filename: str):
    from rag.autoplay import get_cached_results
    from rag.downloads import generate_results_markdown, generate_readme_markdown, generate_process_markdown

    results = get_cached_results()

    # Files from disk
    disk_files = {
        "rag_pipeline.ipynb": BASE_DIR / "rag_pipeline.ipynb",
        "requirements.txt": BASE_DIR / "requirements.txt",
    }

    if filename in disk_files:
        path = disk_files[filename]
        if not path.exists():
            raise HTTPException(404, f"File not found: {filename}")
        content = path.read_bytes()
        media = "application/octet-stream"
        if filename.endswith(".txt"):
            media = "text/plain"
        return StreamingResponse(
            io.BytesIO(content),
            media_type=media,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    # Generated files (require autoplay results)
    if not results:
        raise HTTPException(404, "No results available. Run autoplay first.")

    generated = {
        "results.md": lambda: generate_results_markdown(
            results["eval_results"], results["chat_responses"], results["notebook_outputs"]
        ),
        "readme.md": generate_readme_markdown,
        "process.md": generate_process_markdown,
    }

    if filename in generated:
        content = generated[filename]()
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    # Chart files
    charts = results.get("charts", {})
    chart_name = filename.replace("charts/", "").replace(".png", "").replace(".svg", "")
    if chart_name in charts:
        import base64
        data = charts[chart_name]
        if chart_name == "architecture_diagram":
            return StreamingResponse(
                io.BytesIO(data.encode("utf-8")),
                media_type="image/svg+xml",
                headers={"Content-Disposition": f"attachment; filename={chart_name}.svg"},
            )
        else:
            png_bytes = base64.b64decode(data)
            return StreamingResponse(
                io.BytesIO(png_bytes),
                media_type="image/png",
                headers={"Content-Disposition": f"attachment; filename={chart_name}.png"},
            )

    raise HTTPException(404, f"Unknown file: {filename}")
