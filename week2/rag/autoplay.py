"""
Autoplay orchestration: runs the entire RAG pipeline via SSE streaming.
Phases: notebook → chat → evaluation → charts → complete

Uses heartbeat events every 15s during long-running steps so the UI
never appears stuck.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import AsyncGenerator

from rag.notebook_runner import run_cell
from rag.engine import query as rag_query
from rag.evaluator import run_evaluation
from rag.charts import generate_all_charts

_cached_results: dict | None = None

NOTEBOOK_CELLS = [
    "step1_load", "step2_chunk", "step3_embed",
    "step4_retrieve", "step5_query", "step6_eval",
]

CHAT_QUESTIONS = [
    "How does DRQN handle partial observability in Atari games?",
    "What is the burn-in technique used in R2D2?",
    "How does DreamerV3 achieve generalization across diverse domains?",
]

EVAL_CONFIGS = [
    {"chunk_size": 300, "search_mode": "vector"},
    {"chunk_size": 300, "search_mode": "hybrid"},
    {"chunk_size": 500, "search_mode": "vector"},
    {"chunk_size": 500, "search_mode": "hybrid"},
    {"chunk_size": 1000, "search_mode": "vector"},
    {"chunk_size": 1000, "search_mode": "hybrid"},
]


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


async def _run_with_heartbeat(func, *args, heartbeat_msg="Still working", interval=15, **kwargs):
    """
    Run a blocking function in a thread. While it runs, yield heartbeat
    SSE events every `interval` seconds so the client knows we're alive.
    Returns (result, list_of_heartbeat_events).
    """
    heartbeats = []
    loop = asyncio.get_event_loop()
    future = loop.run_in_executor(None, lambda: func(*args, **kwargs))
    start = time.time()

    while True:
        try:
            result = await asyncio.wait_for(asyncio.shield(future), timeout=interval)
            return result, heartbeats
        except asyncio.TimeoutError:
            elapsed = int(time.time() - start)
            heartbeats.append(_sse({
                "heartbeat": True,
                "message": f"{heartbeat_msg}... ({elapsed}s elapsed)",
                "elapsed": elapsed,
            }))


async def run_autoplay_stream(theme: str = "dark") -> AsyncGenerator[str, None]:
    global _cached_results

    results = {
        "timestamp": datetime.now().isoformat(),
        "notebook_outputs": {},
        "chat_responses": [],
        "eval_results": [],
        "charts": {},
    }

    total_phases = len(NOTEBOOK_CELLS) + len(CHAT_QUESTIONS) + len(EVAL_CONFIGS) + 1 + 1
    current_step = 0

    # ─── Phase 1: Notebook ───
    for i, cell_id in enumerate(NOTEBOOK_CELLS, 1):
        current_step += 1
        yield _sse({
            "phase": "notebook", "step": i, "total": len(NOTEBOOK_CELLS),
            "overall": current_step, "overall_total": total_phases,
            "status": "running", "cell_id": cell_id,
            "message": f"Running notebook cell: {cell_id}",
        })

        cell_result, heartbeats = await _run_with_heartbeat(
            run_cell, cell_id, None,
            heartbeat_msg=f"Running {cell_id}",
        )
        for hb in heartbeats:
            yield hb

        results["notebook_outputs"][cell_id] = cell_result["output"]

        yield _sse({
            "phase": "notebook", "step": i, "total": len(NOTEBOOK_CELLS),
            "overall": current_step, "overall_total": total_phases,
            "status": "done", "cell_id": cell_id,
            "output": cell_result["output"][:500],
            "time": cell_result["execution_time"],
            "error": cell_result.get("error"),
        })

    # ─── Phase 2: Chat Q&A ───
    for i, question in enumerate(CHAT_QUESTIONS, 1):
        current_step += 1
        yield _sse({
            "phase": "chat", "step": i, "total": len(CHAT_QUESTIONS),
            "overall": current_step, "overall_total": total_phases,
            "status": "running", "question": question,
            "message": f"Asking: {question[:60]}...",
        })

        chat_result, heartbeats = await _run_with_heartbeat(
            rag_query, question=question,
            search_mode="hybrid", chunk_size=500, num_results=3,
            heartbeat_msg=f"Waiting for LLM response",
        )
        for hb in heartbeats:
            yield hb

        results["chat_responses"].append({
            "question": question,
            "answer": chat_result["answer"],
            "sources": chat_result["sources"],
        })

        yield _sse({
            "phase": "chat", "step": i, "total": len(CHAT_QUESTIONS),
            "overall": current_step, "overall_total": total_phases,
            "status": "done", "question": question,
            "answer_preview": chat_result["answer"][:200],
        })

    # ─── Phase 3: Evaluation (heuristic only — fast) ───
    for i, config in enumerate(EVAL_CONFIGS, 1):
        current_step += 1
        label = f"chunk_{config['chunk_size']}_{config['search_mode']}"
        yield _sse({
            "phase": "eval", "step": i, "total": len(EVAL_CONFIGS) + 1,
            "overall": current_step, "overall_total": total_phases,
            "status": "running", "config": label,
            "message": f"Evaluating: {label} (heuristic)",
        })

        eval_result, heartbeats = await _run_with_heartbeat(
            run_evaluation,
            chunk_size=config["chunk_size"],
            search_mode=config["search_mode"],
            use_llm_judge=False,
            use_heuristic=True,
            heartbeat_msg=f"Evaluating {label}",
        )
        for hb in heartbeats:
            yield hb

        results["eval_results"].append(eval_result)

        scores_h = eval_result.get("scores_heuristic", {})
        yield _sse({
            "phase": "eval", "step": i, "total": len(EVAL_CONFIGS) + 1,
            "overall": current_step, "overall_total": total_phases,
            "status": "done", "config": label,
            "scores_heuristic": scores_h,
        })

    # ─── Phase 3b: LLM-as-Judge on best config ───
    current_step += 1
    best_idx = max(
        range(len(results["eval_results"])),
        key=lambda i: results["eval_results"][i].get("scores_heuristic", {}).get("correctness", 0),
    )
    best_config = EVAL_CONFIGS[best_idx]
    best_label = f"chunk_{best_config['chunk_size']}_{best_config['search_mode']}"

    yield _sse({
        "phase": "eval", "step": len(EVAL_CONFIGS) + 1, "total": len(EVAL_CONFIGS) + 1,
        "overall": current_step, "overall_total": total_phases,
        "status": "running", "config": best_label,
        "message": f"LLM-as-Judge scoring: {best_label} (5 questions, ~3-5 min)",
    })

    judge_result, heartbeats = await _run_with_heartbeat(
        run_evaluation,
        chunk_size=best_config["chunk_size"],
        search_mode=best_config["search_mode"],
        use_llm_judge=True,
        use_heuristic=True,
        heartbeat_msg=f"LLM Judge scoring {best_label}",
    )
    for hb in heartbeats:
        yield hb

    results["eval_results"][best_idx] = judge_result

    scores_h = judge_result.get("scores_heuristic", {})
    scores_j = judge_result.get("scores_llm_judge", {})
    yield _sse({
        "phase": "eval", "step": len(EVAL_CONFIGS) + 1, "total": len(EVAL_CONFIGS) + 1,
        "overall": current_step, "overall_total": total_phases,
        "status": "done", "config": best_label,
        "scores_heuristic": scores_h,
        "scores_llm_judge": scores_j,
    })

    # ─── Phase 4: Chart Generation ───
    current_step += 1
    yield _sse({
        "phase": "charts",
        "overall": current_step, "overall_total": total_phases,
        "status": "generating",
        "message": "Generating charts and architecture diagram...",
    })

    charts = await asyncio.to_thread(generate_all_charts, results["eval_results"], theme)
    results["charts"] = charts

    yield _sse({
        "phase": "charts",
        "overall": current_step, "overall_total": total_phases,
        "status": "done",
        "chart_names": list(charts.keys()),
    })

    _cached_results = results

    yield _sse({
        "phase": "complete", "status": "done",
        "timestamp": results["timestamp"],
        "message": "Autoplay complete!",
    })


def get_cached_results() -> dict | None:
    return _cached_results
