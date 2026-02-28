"""
Server-side notebook cell execution engine.
Each cell_id maps to a predefined function. User-edited code is parsed for parameter changes only.
"""

import re
import sys
from io import StringIO
from time import time

from rag import engine
from rag.evaluator import run_evaluation


def _capture_output(func, *args, **kwargs) -> tuple[str, str | None, float]:
    buf = StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    t0 = time()
    error = None
    try:
        func(*args, **kwargs)
    except Exception as e:
        error = f"{type(e).__name__}: {str(e)}"
    finally:
        sys.stdout = old_stdout
    return buf.getvalue(), error, round(time() - t0, 2)


def _extract_param(code: str, name: str, default):
    pattern = rf'{name}\s*=\s*["\']?([^"\'\s,\n]+)["\']?'
    match = re.search(pattern, code)
    if match:
        val = match.group(1)
        if isinstance(default, int):
            try:
                return int(val)
            except ValueError:
                return default
        if isinstance(default, bool):
            return val.lower() in ("true", "1", "yes")
        return val
    return default


def run_step1_load():
    stats = engine.get_document_stats()
    print(f"PDF documents loaded: {stats['total_pages']} pages")
    print(f"PDF files: {stats['pdf_count']}")
    print(f"\nSample (first page):")
    print(f"  Source: {stats['sample_source']}")
    print(f"  Content: {stats['sample_content'][:300]}...")


def run_step2_chunk(chunk_size: int = 500):
    overlap = {300: 30, 500: 50, 1000: 100}.get(chunk_size, 50)
    stats = engine.get_chunk_stats(chunk_size)
    print(f"Chunk size: {chunk_size} | Overlap: {overlap}")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Smallest chunk: {stats['smallest']} chars")
    print(f"  Largest chunk:  {stats['largest']} chars")
    print(f"  Average chunk:  {stats['average']} chars")


def run_step3_embed(chunk_size: int = 500):
    info = engine.get_embedding_info()
    print(f"Embedding model: {info['model']}")
    print(f"Embedding dimensions: {info['dimensions']}")
    print(f"Sample values: {info['sample_values']}")
    count = engine.get_collection_count(chunk_size)
    print(f"\nChromaDB collection 'chunks_{chunk_size}': {count} vectors stored")


def run_step4_retrieve(search_mode: str = "hybrid", num_results: int = 3):
    queries = [
        "How does DRQN handle partial observability in Atari games?",
        "What is the burn-in technique used in R2D2 for recurrent experience replay?",
        "How does DreamerV3 achieve generalization across diverse domains without tuning?",
    ]
    for i, q in enumerate(queries, 1):
        print(f"\n{'='*60}")
        print(f"Query {i}: {q}")
        print(f"{'='*60}")
        results = engine.retrieve(q, search_mode=search_mode, num_results=num_results)
        for j, r in enumerate(results, 1):
            print(f"\n  Chunk {j}: {r['source']} (topic: {r.get('topic', 'N/A')})")
            print(f"  Content: {r['content'][:200]}...")


def run_step5_query(search_mode: str = "hybrid", chunk_size: int = 500):
    queries = [
        "How does DRQN handle partial observability in Atari games?",
        "What is the burn-in technique used in R2D2 for recurrent experience replay?",
        "How does DreamerV3 achieve generalization across diverse domains without tuning?",
    ]
    for i, q in enumerate(queries, 1):
        print(f"\n{'='*60}")
        print(f"Query {i}: {q}")
        print(f"{'='*60}")
        result = engine.query(q, search_mode=search_mode, chunk_size=chunk_size)
        print(f"\nAnswer: {result['answer'][:500]}")
        print(f"\nSources: {', '.join(s['source'] for s in result['sources'])}")


def run_step6_eval(
    chunk_size: int = 500,
    search_mode: str = "hybrid",
    use_llm_judge: bool = True,
    use_heuristic: bool = True,
):
    results = run_evaluation(
        chunk_size=chunk_size,
        search_mode=search_mode,
        use_llm_judge=use_llm_judge,
        use_heuristic=use_heuristic,
    )
    for q in results["questions"]:
        print(f"\nQ: {q['question'][:60]}...")
        print(f"  Answer: {q['generated_answer'][:120]}...")
        if "heuristic" in q:
            h = q["heuristic"]
            r = "Y" if h["retrieval"] else "N"
            f = "Y" if h["faithfulness"] else "N"
            c = "Y" if h["correctness"] else "N"
            print(f"  Heuristic  -> R:{r} F:{f} C:{c} (score: {h['correctness_score']})")
        if "llm_judge" in q:
            j = q["llm_judge"]
            print(f"  LLM Judge  -> R:{int(j['retrieval'])} F:{int(j['faithfulness'])} C:{j['correctness']}")
            if j.get("reasoning"):
                print(f"  Reasoning: {j['reasoning'][:100]}...")

    print(f"\n{'='*60}")
    print("SCORES SUMMARY")
    print(f"{'='*60}")
    if "scores_heuristic" in results:
        s = results["scores_heuristic"]
        print(f"Heuristic  -> Retrieval: {s['retrieval']}/5 | Faithfulness: {s['faithfulness']}/5 | Correctness: {s['correctness']}/5")
    if "scores_llm_judge" in results:
        s = results["scores_llm_judge"]
        print(f"LLM Judge  -> Retrieval: {s['retrieval']}/5 | Faithfulness: {s['faithfulness']}/5 | Correctness: {s['correctness']}/5.0")


RUNNERS = {
    "step1_load": (run_step1_load, {}),
    "step2_chunk": (run_step2_chunk, {"chunk_size": 500}),
    "step3_embed": (run_step3_embed, {"chunk_size": 500}),
    "step4_retrieve": (run_step4_retrieve, {"search_mode": "hybrid", "num_results": 3}),
    "step5_query": (run_step5_query, {"search_mode": "hybrid", "chunk_size": 500}),
    "step6_eval": (run_step6_eval, {"chunk_size": 500, "search_mode": "hybrid", "use_llm_judge": True, "use_heuristic": True}),
}


def run_cell(cell_id: str, user_code: str | None = None) -> dict:
    if cell_id not in RUNNERS:
        return {"output": "", "error": f"Cell '{cell_id}' is not runnable.", "execution_time": 0}

    func, defaults = RUNNERS[cell_id]
    params = dict(defaults)

    if user_code:
        for pname, pdefault in defaults.items():
            params[pname] = _extract_param(user_code, pname, pdefault)

    output, error, elapsed = _capture_output(func, **params)
    return {"output": output, "error": error, "execution_time": elapsed}
