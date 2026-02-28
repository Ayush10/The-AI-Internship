"""
Evaluation module: improved heuristics + LLM-as-judge scoring.
"""

import json
import re
from difflib import SequenceMatcher

from rag.engine import query as rag_query, get_llm

EVAL_SET = [
    {
        "question": "What architecture does DRQN use to handle partial observability?",
        "expected_answer": "DRQN replaces the first fully connected layer of DQN with an LSTM recurrent layer to handle partial observability.",
        "expected_source_keyword": "deep_recurrent_q_learning",
    },
    {
        "question": "What is the burn-in strategy in R2D2?",
        "expected_answer": "Burn-in uses a portion of the replay sequence to initialize the recurrent state before the actual training segment, producing a better initial hidden state.",
        "expected_source_keyword": "recurrent_experience_replay",
    },
    {
        "question": "What is the key contribution of Constrained Policy Optimization (CPO)?",
        "expected_answer": "CPO provides near-constraint satisfaction guarantees at each policy update, enabling safe reinforcement learning with cost constraints.",
        "expected_source_keyword": "constrained_policy_optimization",
    },
    {
        "question": "What is the Gated Transformer-XL (GTrXL) and what problem does it solve?",
        "expected_answer": "GTrXL is a stabilized transformer architecture for RL that replaces residual connections with gating layers, enabling stable training of transformers in RL settings.",
        "expected_source_keyword": "stabilizing_transformers",
    },
    {
        "question": "How does DreamerV3 handle the challenge of varying signal magnitudes across different domains?",
        "expected_answer": "DreamerV3 uses symlog predictions that transform targets with a logarithmic function to handle the wide range of reward magnitudes across different domains.",
        "expected_source_keyword": "mastering_diverse_domains",
    },
]

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
    "to", "for", "of", "and", "or", "that", "this", "it", "with", "by",
    "from", "its", "can", "has", "have", "been", "will", "would", "could",
    "should", "which", "their", "than", "also", "into", "each", "such",
    "not", "but", "more", "about", "does", "what", "how", "where", "when",
    "based", "using", "used",
}

LLM_JUDGE_PROMPT = """You are an expert evaluator for a RAG (Retrieval-Augmented Generation) system about reinforcement learning research papers.

Compare the GENERATED answer against the EXPECTED answer and score it.

## Question
{question}

## Expected Answer
{expected_answer}

## Generated Answer
{generated_answer}

## Retrieved Sources
{sources}

## Scoring Criteria

1. **Retrieval** (0 or 1): Did the system retrieve chunks from the correct source paper?
   Expected source keyword: {expected_source_keyword}

2. **Faithfulness** (0 or 1): Is the generated answer grounded in the retrieved sources?
   Score 0 if the answer contains information NOT present in any retrieved chunk.
   Score 1 if every claim can be traced to retrieved context.

3. **Correctness** (0.0 to 1.0): How well does the generated answer match the expected answer SEMANTICALLY?
   - 1.0: Perfect — covers all key points
   - 0.75: Good — covers most key points, minor omissions
   - 0.5: Partial — captures main idea but misses important details
   - 0.25: Weak — tangentially related but missing core information
   - 0.0: Wrong — contradicts expected answer or completely off-topic

Respond with ONLY a JSON object (no markdown, no code blocks):
{{"retrieval": 0_or_1, "faithfulness": 0_or_1, "correctness": 0.0_to_1.0, "reasoning": "brief explanation"}}"""


def _extract_key_terms(text: str) -> set[str]:
    words = re.findall(r'[a-zA-Z0-9-]+', text.lower())
    return {w for w in words if len(w) > 3 and w not in STOPWORDS}


def score_retrieval_heuristic(sources: list[dict], expected_keyword: str) -> bool:
    for src in sources:
        if expected_keyword in src.get("source", ""):
            return True
    return False


def score_faithfulness_heuristic(answer: str, sources: list[dict]) -> bool:
    if "don't have enough information" in answer.lower():
        return False
    context = " ".join(s.get("content", "") for s in sources).lower()
    answer_terms = _extract_key_terms(answer)
    if not answer_terms:
        return False
    matches = sum(1 for t in answer_terms if t in context)
    return (matches / len(answer_terms)) > 0.2


def score_correctness_heuristic(expected: str, generated: str) -> tuple[bool, float]:
    expected_lower = expected.lower()
    generated_lower = generated.lower()
    expected_terms = _extract_key_terms(expected)

    if not expected_terms:
        return False, 0.0

    exact_matches = sum(1 for t in expected_terms if t in generated_lower)
    exact_ratio = exact_matches / len(expected_terms)

    gen_words = set(re.findall(r'[a-zA-Z0-9-]+', generated_lower))
    fuzzy_matches = 0
    for term in expected_terms:
        for gw in gen_words:
            if SequenceMatcher(None, term, gw).ratio() > 0.8:
                fuzzy_matches += 1
                break
    fuzzy_ratio = fuzzy_matches / len(expected_terms)

    def bigrams(text):
        words = text.split()
        return set(zip(words, words[1:]))

    exp_bi = bigrams(expected_lower)
    gen_bi = bigrams(generated_lower)
    bigram_overlap = len(exp_bi & gen_bi) / max(len(exp_bi), 1) if exp_bi else 0

    composite = (exact_ratio * 0.4) + (fuzzy_ratio * 0.3) + (bigram_overlap * 0.3)
    return composite >= 0.35, round(composite, 3)


def score_heuristic(result: dict, eval_item: dict) -> dict:
    sources = result["sources"]
    answer = result["answer"]
    retrieval = score_retrieval_heuristic(sources, eval_item["expected_source_keyword"])
    faithfulness = score_faithfulness_heuristic(answer, sources)
    correct, score = score_correctness_heuristic(eval_item["expected_answer"], answer)
    return {
        "retrieval": retrieval,
        "faithfulness": faithfulness,
        "correctness": correct,
        "correctness_score": score,
    }


def score_llm_judge(result: dict, eval_item: dict) -> dict:
    llm = get_llm()
    sources_text = "\n".join(
        f"- {s['source']} (topic: {s.get('topic', 'N/A')}): {s['content'][:200]}..."
        for s in result["sources"]
    )
    prompt = LLM_JUDGE_PROMPT.format(
        question=eval_item["question"],
        expected_answer=eval_item["expected_answer"],
        generated_answer=result["answer"],
        sources=sources_text,
        expected_source_keyword=eval_item["expected_source_keyword"],
    )

    try:
        response = llm.invoke(prompt)
        raw = response.content if hasattr(response, "content") else str(response)
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
        json_match = re.search(r'\{[^{}]*"retrieval"[^{}]*\}', cleaned, re.DOTALL)
        if json_match:
            cleaned = json_match.group()
        data = json.loads(cleaned)
        return {
            "retrieval": bool(data.get("retrieval", 0)),
            "faithfulness": bool(data.get("faithfulness", 0)),
            "correctness": float(data.get("correctness", 0)),
            "reasoning": data.get("reasoning", ""),
        }
    except Exception as e:
        return {
            "retrieval": False,
            "faithfulness": False,
            "correctness": 0.0,
            "reasoning": f"Judge error: {str(e)}",
        }


def run_evaluation(
    chunk_size: int = 500,
    search_mode: str = "hybrid",
    use_llm_judge: bool = True,
    use_heuristic: bool = True,
) -> dict:
    results = []
    heuristic_totals = {"retrieval": 0, "faithfulness": 0, "correctness": 0}
    judge_totals = {"retrieval": 0, "faithfulness": 0, "correctness": 0.0}

    for item in EVAL_SET:
        result = rag_query(
            question=item["question"],
            search_mode=search_mode,
            chunk_size=chunk_size,
            num_results=3,
        )

        entry = {
            "question": item["question"],
            "expected_answer": item["expected_answer"],
            "generated_answer": result["answer"],
            "sources": [s["source"] for s in result["sources"]],
        }

        if use_heuristic:
            h = score_heuristic(result, item)
            entry["heuristic"] = h
            heuristic_totals["retrieval"] += int(h["retrieval"])
            heuristic_totals["faithfulness"] += int(h["faithfulness"])
            heuristic_totals["correctness"] += int(h["correctness"])

        if use_llm_judge:
            j = score_llm_judge(result, item)
            entry["llm_judge"] = j
            judge_totals["retrieval"] += int(j["retrieval"])
            judge_totals["faithfulness"] += int(j["faithfulness"])
            judge_totals["correctness"] += j["correctness"]

        results.append(entry)

    output = {"chunk_size": chunk_size, "search_mode": search_mode, "questions": results}

    if use_heuristic:
        output["scores_heuristic"] = {**heuristic_totals, "total": 5}
    if use_llm_judge:
        output["scores_llm_judge"] = {
            "retrieval": judge_totals["retrieval"],
            "faithfulness": judge_totals["faithfulness"],
            "correctness": round(judge_totals["correctness"], 2),
            "total": 5,
        }

    return output
