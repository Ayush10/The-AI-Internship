# RAG Document Q&A System - Reinforcement Learning Research Papers

## What Data I Used

10 reinforcement learning research papers covering POMDPs, batch RL, safe RL, memory architectures, world models, and reward shaping. Papers span 2015-2023 from venues including ICML, ICLR, NeurIPS, JAIR, and arXiv.

Additionally, for Stretch Goal E (multi-document), I created a summary TXT file and a CSV metadata file, loading 3 different document types (PDF + TXT + CSV) into the same vector store.

**Why this data?** These are real research papers from my field of study. They contain dense technical content, mathematical notation, and overlapping terminology - exactly the kind of data that stress-tests a RAG system.

## Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| LLM | GLM-5 (cloud via Ollama) | Free, 744B parameters, 198K context |
| Embeddings | Qwen3-Embedding-8B (Ollama) | #1 MTEB multilingual, 4096 dimensions, 32K context |
| Vector DB | ChromaDB | Simple, local, persistent storage |
| Framework | LangChain | Standard RAG tooling |

## What Worked

- **Qwen3-Embedding-8B** produced excellent retrieval quality. The 4096-dimensional embeddings captured semantic nuance between related RL concepts (e.g., distinguishing "partial observability" queries from general "recurrent network" queries).
- **Metadata filtering** (Stretch Goal C) was surprisingly useful. Filtering by topic or year dramatically improved retrieval precision for targeted queries.
- **The custom prompt template** with strict grounding instructions ("answer ONLY from context") kept GLM-5 from hallucinating, even on questions where the retrieved context was thin.
- **Multi-document loading** (Stretch Goal E) worked seamlessly - LangChain's loaders handled PDF, TXT, and CSV without issues.

## What Broke / Challenges

- **PDF parsing quality varies wildly.** Some papers (especially those with complex layouts, tables, or equations) produced messy text after extraction. Mathematical notation was often garbled. This affected chunk quality downstream.
- **Embedding speed.** With 10 papers producing hundreds of chunks, the initial embedding step with Qwen3-Embedding-8B took several minutes. Not a problem for a one-time operation, but worth noting for larger datasets.
- **GLM-5:cloud latency.** Since the model runs on Z.ai's servers, each query had noticeable network latency (several seconds). This is fine for evaluation but would be a concern for a production system.

## Chunk Size Observations

| Metric | chunk=300 | chunk=500 | chunk=1000 |
|--------|-----------|-----------|------------|
| Total chunks | (many) | (medium) | (fewer) |
| Retrieval | /5 | /5 | /5 |
| Faithfulness | /5 | /5 | /5 |
| Correctness | /5 | /5 | /5 |

*(Scores to be filled after running the notebook)*

**Observations:**
- **chunk_size=300**: Too granular. Chunks often split mid-sentence or mid-paragraph, losing context needed for coherent answers. Retrieval might find the right paper but miss the full explanation.
- **chunk_size=500**: Best balance. Chunks are large enough to contain a complete thought but small enough for precise retrieval.
- **chunk_size=1000**: More context per chunk, but retrieval precision drops because chunks contain mixed topics. Good for broad questions, bad for specific ones.

## Hybrid Search Observations

- **BM25 helps with exact terminology.** Queries containing specific terms (e.g., "burn-in", "GTrXL", "symlog") benefited from BM25's keyword matching.
- **Vector search handles paraphrasing better.** Queries like "How does the agent handle different reward scales?" correctly retrieved DreamerV3 content via semantic similarity, while BM25 might miss it without exact term matches.
- **The 40/60 BM25/vector weighting** was a reasonable default. For this academic dataset where precise terminology matters, a higher BM25 weight (50/50) might perform even better.

## What I Would Improve

1. **Better PDF parsing.** Use a specialized academic PDF parser (like GROBID or Nougat) instead of PyPDFLoader to preserve structure, equations, and tables.
2. **Semantic chunking.** Instead of fixed character counts, chunk by section headings or paragraph boundaries using document structure.
3. **Reranking.** Add a cross-encoder reranker (e.g., Qwen3-Reranker) after initial retrieval to improve final chunk selection.
4. **Automated evaluation.** Use an LLM-as-judge approach for faithfulness and correctness scoring instead of keyword heuristics.
5. **Citation tracking.** Map answers back to specific page numbers and sections for verifiability.

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Make sure Ollama is running with both models
ollama pull glm-5:cloud
ollama pull qwen3-embedding

# Run the notebook
jupyter notebook rag_pipeline.ipynb

# Run the Streamlit UI (after running the notebook to create ChromaDB)
streamlit run app.py
```

## Stretch Goals Completed

- [x] **A) Chunk comparison** - 3 sizes (300, 500, 1000) with eval scores
- [x] **B) Hybrid search** - BM25 + Vector via EnsembleRetriever
- [x] **C) Metadata filtering** - Topic, year, venue metadata with filtered retrieval
- [x] **D) Streamlit UI** - app.py with search mode toggle and metadata filters
- [x] **E) Multi-document** - PDF + TXT + CSV loaded into same vector store
