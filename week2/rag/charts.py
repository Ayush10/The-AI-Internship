"""
Chart generation: matplotlib bar/line charts + architecture SVG.
All charts are returned as base64 PNG strings (or raw SVG).
"""

import io
import base64

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


# ─── Theme Colors ───

THEMES = {
    "dark": {
        "bg": "#0f0f0f",
        "surface": "#1a1a1a",
        "text": "#e5e5e5",
        "muted": "#a3a3a3",
        "border": "#2a2a2a",
        "accent": "#3b82f6",
        "accent2": "#22c55e",
        "accent3": "#f59e0b",
        "grid": "#222222",
    },
    "light": {
        "bg": "#fafaf8",
        "surface": "#ffffff",
        "text": "#1a1a1a",
        "muted": "#666666",
        "border": "#e5e5e5",
        "accent": "#2563eb",
        "accent2": "#16a34a",
        "accent3": "#d97706",
        "grid": "#f0f0f0",
    },
}


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(
        buf, format="png", dpi=150, bbox_inches="tight",
        facecolor=fig.get_facecolor(), edgecolor="none",
    )
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _setup_fig(theme: str, figsize=(10, 5)):
    c = THEMES.get(theme, THEMES["dark"])
    fig, ax = plt.subplots(figsize=figsize)
    fig.set_facecolor(c["bg"])
    ax.set_facecolor(c["surface"])
    ax.tick_params(colors=c["muted"], labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(c["border"])
    ax.spines["left"].set_color(c["border"])
    ax.grid(axis="y", alpha=0.3, color=c["grid"], linewidth=0.5)
    return fig, ax, c


# ─── Evaluation Scores Bar Chart ───

def generate_evaluation_chart(eval_results: list[dict], theme: str = "dark") -> str:
    """Grouped bar chart: retrieval/faithfulness/correctness per configuration."""
    fig, ax, c = _setup_fig(theme, figsize=(12, 5))

    configs = []
    retrieval = []
    faithfulness = []
    correctness = []

    for r in eval_results:
        label = f"c{r['chunk_size']}_{r['search_mode'][:3]}"
        configs.append(label)
        scores = r.get("scores_heuristic", {})
        retrieval.append(scores.get("retrieval", 0))
        faithfulness.append(scores.get("faithfulness", 0))
        correctness.append(scores.get("correctness", 0))

    import numpy as np
    x = np.arange(len(configs))
    width = 0.25

    ax.bar(x - width, retrieval, width, label="Retrieval", color=c["accent"], alpha=0.9)
    ax.bar(x, faithfulness, width, label="Faithfulness", color=c["accent2"], alpha=0.9)
    ax.bar(x + width, correctness, width, label="Correctness", color=c["accent3"], alpha=0.9)

    ax.set_xticks(x)
    ax.set_xticklabels(configs, fontsize=9, color=c["muted"])
    ax.set_ylabel("Score (out of 5)", fontsize=10, color=c["text"])
    ax.set_title("Evaluation Scores by Configuration", fontsize=13, fontweight="bold", color=c["text"], pad=12)
    ax.set_ylim(0, 5.5)
    ax.yaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.legend(fontsize=9, facecolor=c["surface"], edgecolor=c["border"], labelcolor=c["text"])

    # Value labels on bars
    for bars in [ax.containers[0], ax.containers[1], ax.containers[2]]:
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.1, str(int(h)),
                        ha="center", va="bottom", fontsize=8, color=c["muted"])

    return _fig_to_base64(fig)


# ─── Chunk Size Comparison ───

def generate_chunk_comparison_chart(eval_results: list[dict], theme: str = "dark") -> str:
    """Line chart comparing chunk sizes for hybrid search."""
    fig, ax, c = _setup_fig(theme, figsize=(8, 5))

    # Filter to hybrid only for fair comparison
    hybrid = [r for r in eval_results if r.get("search_mode") == "hybrid"]
    if not hybrid:
        hybrid = eval_results[:3]  # fallback

    hybrid.sort(key=lambda r: r["chunk_size"])

    sizes = [r["chunk_size"] for r in hybrid]
    retrieval = [r.get("scores_heuristic", {}).get("retrieval", 0) for r in hybrid]
    faithfulness = [r.get("scores_heuristic", {}).get("faithfulness", 0) for r in hybrid]
    correctness = [r.get("scores_heuristic", {}).get("correctness", 0) for r in hybrid]

    ax.plot(sizes, retrieval, "o-", label="Retrieval", color=c["accent"], linewidth=2, markersize=8)
    ax.plot(sizes, faithfulness, "s-", label="Faithfulness", color=c["accent2"], linewidth=2, markersize=8)
    ax.plot(sizes, correctness, "^-", label="Correctness", color=c["accent3"], linewidth=2, markersize=8)

    ax.set_xlabel("Chunk Size", fontsize=10, color=c["text"])
    ax.set_ylabel("Score (out of 5)", fontsize=10, color=c["text"])
    ax.set_title("Performance vs Chunk Size (Hybrid Search)", fontsize=13, fontweight="bold", color=c["text"], pad=12)
    ax.set_ylim(0, 5.5)
    ax.set_xticks(sizes)
    ax.yaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.legend(fontsize=9, facecolor=c["surface"], edgecolor=c["border"], labelcolor=c["text"])

    return _fig_to_base64(fig)


# ─── Search Mode Comparison ───

def generate_search_comparison_chart(eval_results: list[dict], theme: str = "dark") -> str:
    """Side-by-side bars: vector vs hybrid at chunk_size=500."""
    fig, ax, c = _setup_fig(theme, figsize=(8, 5))

    vector = next((r for r in eval_results if r["chunk_size"] == 500 and r["search_mode"] == "vector"), None)
    hybrid = next((r for r in eval_results if r["chunk_size"] == 500 and r["search_mode"] == "hybrid"), None)

    if not vector or not hybrid:
        # Fallback: use first two results
        vector = eval_results[0] if len(eval_results) > 0 else {"scores_heuristic": {}}
        hybrid = eval_results[1] if len(eval_results) > 1 else {"scores_heuristic": {}}

    metrics = ["Retrieval", "Faithfulness", "Correctness"]
    v_scores = [
        vector.get("scores_heuristic", {}).get("retrieval", 0),
        vector.get("scores_heuristic", {}).get("faithfulness", 0),
        vector.get("scores_heuristic", {}).get("correctness", 0),
    ]
    h_scores = [
        hybrid.get("scores_heuristic", {}).get("retrieval", 0),
        hybrid.get("scores_heuristic", {}).get("faithfulness", 0),
        hybrid.get("scores_heuristic", {}).get("correctness", 0),
    ]

    import numpy as np
    x = np.arange(len(metrics))
    width = 0.35

    bars1 = ax.bar(x - width / 2, v_scores, width, label="Vector", color=c["accent"], alpha=0.85)
    bars2 = ax.bar(x + width / 2, h_scores, width, label="Hybrid (BM25+Vector)", color=c["accent2"], alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=10, color=c["text"])
    ax.set_ylabel("Score (out of 5)", fontsize=10, color=c["text"])
    ax.set_title("Vector vs Hybrid Search (chunk_size=500)", fontsize=13, fontweight="bold", color=c["text"], pad=12)
    ax.set_ylim(0, 5.5)
    ax.yaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.legend(fontsize=9, facecolor=c["surface"], edgecolor=c["border"], labelcolor=c["text"])

    for bars in [bars1, bars2]:
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.1, str(int(h)),
                        ha="center", va="bottom", fontsize=9, color=c["muted"])

    return _fig_to_base64(fig)


# ─── Heuristic vs LLM Judge ───

def generate_judge_comparison_chart(eval_results: list[dict], theme: str = "dark") -> str:
    """Compare heuristic vs LLM-judge scoring for best config (chunk_500 hybrid)."""
    fig, ax, c = _setup_fig(theme, figsize=(9, 5))

    best = next(
        (r for r in eval_results if r["chunk_size"] == 500 and r["search_mode"] == "hybrid"),
        eval_results[0] if eval_results else None,
    )
    if not best:
        plt.close(fig)
        return ""

    questions_short = [f"Q{i+1}" for i in range(len(best.get("questions", [])))]

    h_scores = []
    j_scores = []
    for q in best.get("questions", []):
        h = q.get("heuristic", {})
        j = q.get("llm_judge", {})
        h_scores.append(h.get("correctness_score", 0))
        j_scores.append(j.get("correctness", 0))

    import numpy as np
    x = np.arange(len(questions_short))
    width = 0.35

    bars1 = ax.bar(x - width / 2, h_scores, width, label="Heuristic", color=c["accent3"], alpha=0.85)
    bars2 = ax.bar(x + width / 2, j_scores, width, label="LLM Judge", color=c["accent"], alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(questions_short, fontsize=10, color=c["text"])
    ax.set_ylabel("Correctness Score", fontsize=10, color=c["text"])
    ax.set_title("Heuristic vs LLM-as-Judge Correctness", fontsize=13, fontweight="bold", color=c["text"], pad=12)
    ax.set_ylim(0, 1.15)
    ax.legend(fontsize=9, facecolor=c["surface"], edgecolor=c["border"], labelcolor=c["text"])

    for bars in [bars1, bars2]:
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.02,
                        f"{h:.2f}", ha="center", va="bottom", fontsize=8, color=c["muted"])

    return _fig_to_base64(fig)


# ─── Architecture Diagram (SVG) ───

def generate_architecture_svg(theme: str = "dark") -> str:
    c = THEMES.get(theme, THEMES["dark"])
    bg = c["bg"]
    surface = c["surface"]
    text = c["text"]
    muted = c["muted"]
    accent = c["accent"]
    border = c["border"]

    nodes = [
        ("PDFs", "10 RL Papers", "description"),
        ("Chunk", "300 / 500 / 1000", "content_cut"),
        ("Embed", "Qwen3-Embedding", "hub"),
        ("Store", "ChromaDB", "storage"),
        ("Retrieve", "Vector + BM25", "search"),
        ("Generate", "Qwen3", "smart_toy"),
        ("Answer", "Grounded Q&A", "chat"),
    ]

    node_w, node_h = 110, 70
    gap = 16
    total_w = len(nodes) * node_w + (len(nodes) - 1) * gap
    svg_w = total_w + 40
    svg_h = 140
    start_x = 20
    node_y = 40

    rects = ""
    arrows = ""
    for i, (title, subtitle, icon) in enumerate(nodes):
        x = start_x + i * (node_w + gap)
        cx = x + node_w / 2
        cy = node_y + node_h / 2

        rects += f"""
        <rect x="{x}" y="{node_y}" width="{node_w}" height="{node_h}" rx="10"
              fill="{surface}" stroke="{accent}" stroke-width="1.5" opacity="0.95"/>
        <text x="{cx}" y="{cy - 8}" text-anchor="middle"
              fill="{text}" font-size="12" font-weight="700" font-family="DM Sans, sans-serif">{title}</text>
        <text x="{cx}" y="{cy + 10}" text-anchor="middle"
              fill="{muted}" font-size="9" font-family="DM Sans, sans-serif">{subtitle}</text>
        """

        if i > 0:
            x1 = start_x + (i - 1) * (node_w + gap) + node_w
            x2 = x
            ay = node_y + node_h / 2
            mid = (x1 + x2) / 2
            arrows += f"""
            <line x1="{x1 + 2}" y1="{ay}" x2="{x2 - 2}" y2="{ay}"
                  stroke="{accent}" stroke-width="1.5" marker-end="url(#arrowhead)"/>
            """

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="100%" style="max-width:{svg_w}px">
  <defs>
    <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="{accent}"/>
    </marker>
  </defs>
  <rect width="{svg_w}" height="{svg_h}" fill="{bg}" rx="12"/>
  <text x="{svg_w/2}" y="24" text-anchor="middle" fill="{text}"
        font-size="13" font-weight="700" font-family="DM Sans, sans-serif">RAG Pipeline Architecture</text>
  {rects}
  {arrows}
</svg>"""


# ─── Master Function ───

def generate_all_charts(eval_results: list[dict], theme: str = "dark") -> dict[str, str]:
    return {
        "architecture_diagram": generate_architecture_svg(theme),
        "evaluation_scores": generate_evaluation_chart(eval_results, theme),
        "chunk_comparison": generate_chunk_comparison_chart(eval_results, theme),
        "search_comparison": generate_search_comparison_chart(eval_results, theme),
        "judge_comparison": generate_judge_comparison_chart(eval_results, theme),
    }
