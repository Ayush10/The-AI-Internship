"""
Core RAG pipeline — vectorstore, retrievers, chain.
Lazy-loaded singletons to avoid heavy initialization on every request.
"""

import warnings
from pathlib import Path

from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader

from config import OLLAMA_BASE_URL

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = BASE_DIR / "chroma_db"

PAPER_METADATA = {
    "01_deep_recurrent_q_learning_pomdps": {"topic": "POMDP", "year": "2015", "venue": "AAAI Workshop"},
    "02_general_value_function_networks": {"topic": "Predictive Knowledge", "year": "2021", "venue": "JAIR"},
    "03_recurrent_model_free_rl_pomdps": {"topic": "POMDP", "year": "2021", "venue": "NeurIPS"},
    "04_recurrent_experience_replay_distributed_rl": {"topic": "Distributed RL", "year": "2019", "venue": "ICLR"},
    "05_stabilizing_transformers_rl": {"topic": "Memory Architecture", "year": "2020", "venue": "ICML"},
    "06_reward_machines_rl": {"topic": "Reward Shaping", "year": "2022", "venue": "JMLR"},
    "07_off_policy_deep_rl_without_exploration": {"topic": "Batch RL", "year": "2019", "venue": "ICML"},
    "08_constrained_policy_optimization": {"topic": "Safe RL", "year": "2017", "venue": "ICML"},
    "09_benchmarking_batch_deep_rl": {"topic": "Batch RL", "year": "2019", "venue": "arXiv"},
    "10_mastering_diverse_domains_world_models": {"topic": "World Models", "year": "2023", "venue": "arXiv"},
}

RAG_PROMPT_TEMPLATE = """You are a helpful research assistant that answers questions about reinforcement learning papers based ONLY on the provided context.

Rules:
- Answer based ONLY on the provided context. Do not use external knowledge.
- If the context does not contain enough information, say "I don't have enough information in the provided context to answer this question."
- Cite which paper/source the information comes from when possible.
- Be concise but thorough.

Context:
{context}

Question: {question}

Answer:"""

# --- Caches ---
_vectorstore_cache: dict[str, Chroma] = {}
_bm25_cache: dict[str, BM25Retriever] = {}
_chunks_cache: dict[str, list] = {}
_llm = None


def get_embedding_model():
    return OllamaEmbeddings(model="qwen3-embedding", base_url=OLLAMA_BASE_URL)


def get_vectorstore(chunk_size: int = 500) -> Chroma:
    key = f"chunks_{chunk_size}"
    if key not in _vectorstore_cache:
        _vectorstore_cache[key] = Chroma(
            collection_name=key,
            embedding_function=get_embedding_model(),
            persist_directory=str(CHROMA_DIR),
        )
    return _vectorstore_cache[key]


def _load_and_chunk(chunk_size: int = 500) -> list:
    key = f"chunks_{chunk_size}"
    if key not in _chunks_cache:
        loader = DirectoryLoader(str(DATA_DIR), glob="**/*.pdf", loader_cls=PyPDFLoader)
        documents = loader.load()
        overlap = {300: 30, 500: 50, 1000: 100}.get(chunk_size, 50)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_documents(documents)
        for chunk in chunks:
            source = chunk.metadata.get("source", "")
            stem = Path(source).stem
            meta = PAPER_METADATA.get(stem, {})
            chunk.metadata.update(meta)
        _chunks_cache[key] = chunks
    return _chunks_cache[key]


def get_bm25_retriever(chunk_size: int = 500, k: int = 3) -> BM25Retriever:
    key = f"chunks_{chunk_size}"
    if key not in _bm25_cache:
        chunks = _load_and_chunk(chunk_size)
        _bm25_cache[key] = BM25Retriever.from_documents(chunks)
    retriever = _bm25_cache[key]
    retriever.k = k
    return retriever


def get_ensemble_retriever(chunk_size: int = 500, k: int = 3) -> EnsembleRetriever:
    bm25 = get_bm25_retriever(chunk_size, k)
    vector = get_vectorstore(chunk_size).as_retriever(search_kwargs={"k": k})
    return EnsembleRetriever(retrievers=[bm25, vector], weights=[0.4, 0.6])


def get_llm() -> ChatOllama:
    global _llm
    if _llm is None:
        _llm = ChatOllama(model="qwen3:8b", base_url=OLLAMA_BASE_URL, temperature=0)
    return _llm


def build_chain(retriever, llm=None):
    if llm is None:
        llm = get_llm()
    prompt = PromptTemplate(
        template=RAG_PROMPT_TEMPLATE,
        input_variables=["context", "question"],
    )
    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )


def retrieve(
    question: str,
    search_mode: str = "hybrid",
    chunk_size: int = 500,
    num_results: int = 3,
    topic_filter: str | None = None,
) -> list[dict]:
    if search_mode == "hybrid":
        retriever = get_ensemble_retriever(chunk_size, num_results)
        docs = retriever.invoke(question)[:num_results]
    else:
        search_kwargs = {"k": num_results}
        if topic_filter:
            search_kwargs["filter"] = {"topic": topic_filter}
        retriever = get_vectorstore(chunk_size).as_retriever(search_kwargs=search_kwargs)
        docs = retriever.invoke(question)

    return [
        {
            "content": doc.page_content[:500],
            "source": Path(doc.metadata.get("source", "unknown")).stem,
            "topic": doc.metadata.get("topic"),
            "year": doc.metadata.get("year"),
            "page": doc.metadata.get("page"),
        }
        for doc in docs
    ]


def query(
    question: str,
    search_mode: str = "hybrid",
    chunk_size: int = 500,
    num_results: int = 3,
    topic_filter: str | None = None,
) -> dict:
    if search_mode == "hybrid":
        retriever = get_ensemble_retriever(chunk_size, num_results)
    else:
        search_kwargs = {"k": num_results}
        if topic_filter:
            search_kwargs["filter"] = {"topic": topic_filter}
        retriever = get_vectorstore(chunk_size).as_retriever(search_kwargs=search_kwargs)

    chain = build_chain(retriever)
    result = chain.invoke({"query": question})

    sources = [
        {
            "content": doc.page_content[:500],
            "source": Path(doc.metadata.get("source", "unknown")).stem,
            "topic": doc.metadata.get("topic"),
            "year": doc.metadata.get("year"),
            "page": doc.metadata.get("page"),
        }
        for doc in result.get("source_documents", [])
    ]

    return {
        "answer": result["result"],
        "sources": sources,
        "search_mode": search_mode,
        "chunk_size": chunk_size,
    }


def get_document_stats() -> dict:
    loader = DirectoryLoader(str(DATA_DIR), glob="**/*.pdf", loader_cls=PyPDFLoader)
    documents = loader.load()
    return {
        "total_pages": len(documents),
        "pdf_count": len(set(Path(d.metadata.get("source", "")).name for d in documents)),
        "sample_source": documents[0].metadata.get("source", "") if documents else "",
        "sample_content": documents[0].page_content[:500] if documents else "",
    }


def get_chunk_stats(chunk_size: int = 500) -> dict:
    chunks = _load_and_chunk(chunk_size)
    lengths = [len(c.page_content) for c in chunks]
    return {
        "chunk_size": chunk_size,
        "total_chunks": len(chunks),
        "smallest": min(lengths) if lengths else 0,
        "largest": max(lengths) if lengths else 0,
        "average": int(sum(lengths) / len(lengths)) if lengths else 0,
    }


def get_embedding_info() -> dict:
    model = get_embedding_model()
    test_embedding = model.embed_query("test query")
    return {
        "model": "qwen3-embedding (Qwen3-Embedding-8B)",
        "dimensions": len(test_embedding),
        "sample_values": test_embedding[:5],
    }


def get_collection_count(chunk_size: int = 500) -> int:
    vs = get_vectorstore(chunk_size)
    collection = vs._collection
    return collection.count()
