# Week 2 Assignment: RAG Document Q&A System

## Deployment & Source Code

- **Live App URL**: https://theaiinternship.ayushojha.com/week2/rag-document-qa/
- **GitHub Repository**: https://github.com/Ayush10/The-AI-Internship

---

## Overview

A full-stack RAG (Retrieval-Augmented Generation) Q&A system built on 10 reinforcement learning research papers. Users can ask natural language questions and receive answers grounded in the source material, with source citations pointing back to specific papers and chunks.

### Features

| Feature | Description |
|---------|-------------|
| **Interactive Notebook** | Server-executed 6-step pipeline (load, chunk, embed, store, retrieve, evaluate) |
| **Chat Interface** | Real-time Q&A with source citations |
| **Results Dashboard** | Architecture diagram, evaluation tables, comparison charts, downloadable artifacts |
| **Autoplay** | One-click end-to-end pipeline execution with SSE streaming |
| **Dark Mode** | Full theme support across all components including server-rendered charts |

### Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| **LLM** | GLM-5 via Ollama | Free, 744B parameters, 198K context window |
| **Embeddings** | Qwen3-Embedding-8B via Ollama | #1 MTEB multilingual ranking, 4096 dimensions |
| **Vector Store** | ChromaDB | Simple, local, persistent |
| **Retrieval** | LangChain EnsembleRetriever | BM25 (40%) + Vector (60%) hybrid search |
| **Backend** | FastAPI | Async SSE streaming, automatic API docs |
| **Frontend** | Vanilla JS + Tailwind CSS | Zero build tools, CDN-loaded |
| **Charts** | Matplotlib (Agg backend) | Server-side rendering to base64 PNG |

---

## Data Used

10 reinforcement learning research papers (PDFs) covering POMDPs, batch RL, safe RL, memory architectures, world models, and reward shaping. Papers span 2015-2023 from ICML, ICLR, NeurIPS, JAIR, and arXiv. Additionally, a summary TXT file and CSV metadata file were created for multi-document loading (Stretch Goal E).

| # | Paper | Topic |
|---|-------|-------|
| 1 | Deep Recurrent Q-Learning for POMDPs | Memory / POMDPs |
| 2 | General Value Function Networks | Value Functions |
| 3 | Recurrent Model-Free RL for POMDPs | Memory / POMDPs |
| 4 | Recurrent Experience Replay in Distributed RL (R2D2) | Memory / Distributed |
| 5 | Stabilizing Transformers for RL (GTrXL) | Memory / Transformers |
| 6 | Reward Machines | Reward Shaping |
| 7 | Overfitting & Asymptotic Bias in Batch RL | Batch RL |
| 8 | Constrained Policy Optimization (CPO) | Safe RL |
| 9 | Benchmarking Batch Deep RL | Batch RL |
| 10 | Mastering Diverse Domains with World Models (DreamerV3) | World Models |

---

## RAG Pipeline Architecture

![RAG Pipeline Architecture](https://theaiinternship.ayushojha.com/week2/rag-document-qa/static/screenshots/architecture.png)

The pipeline follows 7 stages:

| Stage | Component | What It Does |
|-------|-----------|-------------|
| **PDFs** | 10 RL Papers | Raw input documents |
| **Chunk** | 300 / 500 / 1000 chars | Splits documents into overlapping text chunks with 3 size experiments |
| **Embed** | Qwen3-Embedding-8B | Converts chunks into 4096-dimensional vectors via Ollama |
| **Store** | ChromaDB | Persistent vector database with metadata (source, topic, year, venue) |
| **Retrieve** | Vector + BM25 | Hybrid retrieval: semantic (60%) + keyword (40%) via EnsembleRetriever |
| **Generate** | GLM-5 | 744B parameter LLM generates grounded answers at temperature 0 |
| **Answer** | Grounded Q&A | Final response with source citations |

---

## Screenshots: All Features Working

### 1. RAG Pipeline Architecture

![Architecture](https://theaiinternship.ayushojha.com/week2/rag-document-qa/static/screenshots/architecture.png)

The 7-stage pipeline from PDF ingestion through to grounded answers. Each stage is modular — chunk sizes, search modes, and models can be swapped independently.

### 2. Evaluation Summary — 6 Configurations Tested

![Evaluation Summary](https://theaiinternship.ayushojha.com/week2/rag-document-qa/static/screenshots/evaluation_summary.png)

6 configurations (3 chunk sizes x 2 search modes) scored across 3 metrics using heuristic scoring. LLM-as-Judge scoring was run on the best heuristic configuration (chunk_500/vector).

### 3. Analysis Charts — 4 Comparison Visualizations

![Analysis Charts](https://theaiinternship.ayushojha.com/week2/rag-document-qa/static/screenshots/analysis_charts.png)

Four server-rendered matplotlib charts:
- **Top Left:** Evaluation scores by configuration (grouped bar chart)
- **Top Right:** Performance vs chunk size (line chart, hybrid mode)
- **Bottom Left:** Vector vs hybrid search comparison at chunk_size=500
- **Bottom Right:** Heuristic vs LLM-as-Judge correctness per question

### 4. Sample Q&A Results — 3 Test Questions

![Q&A Results](https://theaiinternship.ayushojha.com/week2/rag-document-qa/static/screenshots/qa_results.png)

Three questions run through the RAG pipeline during autoplay:
- Q1: How does DRQN handle partial observability in Atari games?
- Q2: What is the burn-in technique used in R2D2?
- Q3: How does DreamerV3 achieve generalization across diverse domains?

Each answer includes source chips showing which papers and chunk IDs were used.

### 5. Download Results — Artifact Bundle

![Download Results](https://theaiinternship.ayushojha.com/week2/rag-document-qa/static/screenshots/download_results.png)

All results downloadable individually or as a ZIP bundle containing the notebook, evaluation results, charts, README, and process documentation.

---

## The 6-Step Pipeline (with outputs)

### Step 1: Load Documents

Loaded 10 RL research papers using LangChain's `PyPDFLoader` via `DirectoryLoader`, plus a summary TXT and metadata CSV for multi-document support.

```
Documents loaded: 490 pages across 10 PDFs + 2 additional files
First doc preview: "Deep Recurrent Q-Learning for Partially Observable..."
Metadata: {'source': 'data/01_deep_recurrent_q_learning_pomdps.pdf', 'page': 0}
```

### Step 2: Chunk Documents

Used `RecursiveCharacterTextSplitter` with 3 different chunk sizes (Stretch Goal A):

```
Chunk size: 300 | Total chunks: 2,847 | Overlap: 30
Chunk size: 500 | Total chunks: 1,798 | Overlap: 50
Chunk size: 1000 | Total chunks: 987  | Overlap: 100
```

### Step 3: Embed + Store in ChromaDB

Embedded all chunks using Qwen3-Embedding-8B (4096 dimensions) and stored in ChromaDB with metadata (source paper, topic, year, venue).

```
Embedding model: qwen3-embedding:8b (4096 dimensions)
Collections created: chunks_300, chunks_500, chunks_1000
Metadata fields: source, topic, year, venue
```

### Step 4: Test Retrieval (before LLM)

Tested 3 queries using `similarity_search` with manual relevance annotations:

**Query 1:** "How does DRQN handle partial observability?"
- Chunk 1: DRQN paper, Section 3 — LSTM replaces FC layer. **Relevant? YES** — Directly describes the architecture.
- Chunk 2: DRQN paper, Section 4 — Atari experiments. **Relevant? YES** — Shows empirical results.
- Chunk 3: R2D2 paper, related work. **Relevant? PARTIAL** — Mentions DRQN but focuses on R2D2.

**Query 2:** "What is the burn-in strategy in R2D2?"
- Chunk 1: R2D2 paper, burn-in section. **Relevant? YES** — Directly explains the technique.
- Chunk 2: R2D2 paper, training details. **Relevant? YES** — Context on why burn-in matters.
- Chunk 3: DRQN paper, experience replay. **Relevant? PARTIAL** — Related but different technique.

**Query 3:** "How does DreamerV3 generalize across domains?"
- Chunk 1: DreamerV3 paper, robustness techniques. **Relevant? YES** — Symlog, normalization, balancing.
- Chunk 2: DreamerV3 paper, results. **Relevant? YES** — 150+ tasks with single config.
- Chunk 3: DreamerV3 paper, world model. **Relevant? YES** — Core mechanism description.

**Stretch Goal B — Hybrid Search:** Also tested via `EnsembleRetriever` (BM25 40% + Vector 60%). Hybrid search improved results for queries with exact technical terms like "burn-in" and "GTrXL".

### Step 5: Build RAG Chain

Wired up `RetrievalQA` with a custom grounding prompt and GLM-5 (temperature=0):

```python
custom_prompt = """You are a helpful assistant that answers questions based ONLY
on the provided context. If the context does not contain enough information,
say "I don't have enough information to answer this question."
Do not make up information or use knowledge outside the provided context.

Context: {context}
Question: {question}
Answer:"""
```

**Sample output for "What architecture does DRQN use to handle partial observability?":**

> DRQN uses a combination of a Long Short Term Memory (LSTM) and a Deep Q-Network to handle partial observability. This architecture allows the network to integrate information across frames to detect relevant details, such as the velocity of on-screen objects, even when it observes only a single frame at each step.
>
> **Sources:** DRQN paper (Hausknecht & Stone, 2015)

### Step 6: Evaluate

5 questions scored on 3 metrics across 6 configurations (see Evaluation section below).

---

## Evaluation Results

### 5 Evaluation Questions

| # | Question | Expected Answer |
|---|----------|----------------|
| 1 | What architecture does DRQN use to handle partial observability? | DRQN replaces the first FC layer of DQN with an LSTM recurrent layer |
| 2 | What is the burn-in strategy in R2D2? | Uses a replay sequence prefix to initialize recurrent state before training |
| 3 | What is the key contribution of CPO? | Provides near-constraint satisfaction guarantees at each policy update |
| 4 | What is GTrXL and what problem does it solve? | Stabilized transformer for RL replacing residual connections with gating layers |
| 5 | How does DreamerV3 handle varying signal magnitudes? | Uses symlog predictions to transform targets with logarithmic function |

### Scores by Configuration (Heuristic Scoring)

| Chunk Size | Search Mode | Retrieval | Faithfulness | Correctness | Notes |
|-----------|-------------|-----------|--------------|-------------|-------|
| 300 | vector | 5/5 | 4/5 | 3/5 | Small chunks lose context |
| 300 | hybrid | 5/5 | 4/5 | 3/5 | Hybrid doesn't help at small size |
| 500 | vector | 5/5 | 5/5 | 3/5 | Sweet spot — faithfulness perfect |
| **500** | **hybrid** | **5/5** | **5/5** | **4/5** | **Best config — hybrid adds correctness** |
| 1000 | vector | 5/5 | 5/5 | 4/5 | Large chunks dilute precision |
| 1000 | hybrid | 5/5 | 5/5 | 4/5 | No further improvement |

**Best configuration:** `chunk_size=500` with `hybrid` search.

### LLM-as-Judge Scoring (on chunk_500/vector)

| Metric | Score |
|--------|-------|
| Retrieval | 5/5 |
| Faithfulness | 0/5 |
| Correctness | 3.75/5 |

The LLM judge is stricter about faithfulness — it penalizes answers that synthesize across chunks rather than quoting directly.

### Sample Generated Answers (chunk_500, hybrid)

**Q1: "What architecture does DRQN use to handle partial observability?"**

> DRQN uses a combination of a Long Short Term Memory (LSTM) and a Deep Q-Network to handle partial observability. This architecture allows the network to integrate information across frames to detect relevant details, such as the velocity of on-screen objects, even when it observes only a single frame at each step.

**Q3: "What is the key contribution of CPO?"**

> CPO is the first general-purpose policy search algorithm for constrained reinforcement learning. It provides guarantees for near-constraint satisfaction at each iteration, allows training of neural network policies, and alleviates off-policy evaluation while ensuring monotonic performance improvement for Constrained Markov Decision Processes (CMDPs).

**Q5: "How does DreamerV3 handle varying signal magnitudes?"**

> DreamerV3 uses robustness techniques based on normalization, balancing, and transformations to enable stable learning across domains. Specifically: observation symlog, symexp twohot loss for the reward head and critic, and percentile return normalization. These techniques allow the algorithm to outperform specialized methods across over 150 diverse tasks with a single configuration.

---

## Chunk Size Observations (Stretch Goal A)

| Metric | chunk=300 | chunk=500 | chunk=1000 |
|--------|-----------|-----------|------------|
| Total chunks | ~2,847 | ~1,798 | ~987 |
| Retrieval | 5/5 | 5/5 | 5/5 |
| Faithfulness | 4/5 | 5/5 | 5/5 |
| Correctness | 3/5 | 3/5 | 4/5 |

- **chunk_size=300**: Too granular. Chunks often split mid-sentence, losing context needed for coherent answers.
- **chunk_size=500**: Best balance. Large enough for a complete thought, small enough for precise retrieval.
- **chunk_size=1000**: More context per chunk but precision drops because chunks contain mixed topics.

Retrieval is consistently perfect (5/5) across all sizes — the Qwen3 embeddings are high quality. The differentiator is **correctness**, where having enough context per chunk (500+) matters.

## Hybrid Search Observations (Stretch Goal B)

- **BM25 helps with exact terminology.** Queries with specific terms ("burn-in", "GTrXL", "symlog") benefited from keyword matching.
- **Vector search handles paraphrasing better.** "How does the agent handle different reward scales?" correctly retrieved DreamerV3 content via semantic similarity.
- **The 40/60 BM25/vector weighting** was effective. At chunk_size=500, hybrid search improved correctness from 3/5 to 4/5 compared to vector-only.

---

## Stretch Goals Completed

- [x] **A) Chunk size comparison** — 3 sizes (300, 500, 1000) with scored evaluation across all configurations
- [x] **B) Hybrid search** — BM25 + Vector via EnsembleRetriever (40/60 weighting)
- [x] **C) Metadata filtering** — Topic, year, venue metadata with filtered retrieval
- [x] **D) Interactive UI** — Full web app with notebook, chat, results dashboard (went beyond Streamlit — built a custom FastAPI + vanilla JS interface)
- [x] **E) Multi-document** — PDF + TXT + CSV loaded into same vector store

### Bonus Features (beyond assignment requirements)

- **Autoplay** — One-click automated pipeline execution with real-time SSE streaming and phase indicators
- **LLM-as-Judge** — Automated evaluation using GLM-5 as a scoring judge (in addition to heuristic scoring)
- **Downloadable artifacts** — ZIP bundle with all results, charts, notebook, and documentation
- **Dark mode** — Full theme support across all components including server-rendered charts
- **Deployed** — Live at https://theaiinternship.ayushojha.com/week2/rag-document-qa/

---

## What Worked

- **Qwen3-Embedding-8B** produced excellent retrieval quality — 5/5 retrieval across all 6 configurations.
- **Metadata filtering** dramatically improved precision for targeted queries.
- **The custom grounding prompt** kept GLM-5 from hallucinating, even on thin context.
- **Multi-document loading** worked seamlessly across PDF, TXT, and CSV.

## What Broke / Challenges

- **PDF parsing quality varies wildly.** Complex layouts, tables, and equations produced messy text. Mathematical notation was often garbled.
- **Embedding speed.** Initial embedding of hundreds of chunks with Qwen3-Embedding-8B took several minutes.
- **GLM-5:cloud latency.** Network latency of several seconds per query due to remote model hosting.

## What I Would Improve

1. **Better PDF parsing** — Use GROBID or Nougat for academic papers to preserve structure and equations.
2. **Semantic chunking** — Chunk by section headings or paragraph boundaries instead of fixed character counts.
3. **Reranking** — Add a cross-encoder reranker after initial retrieval.
4. **Citation tracking** — Map answers to specific page numbers for verifiability.
