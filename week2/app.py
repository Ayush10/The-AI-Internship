"""
Streamlit UI for RAG Document Q&A System (Stretch Goal D)
Run with: streamlit run app.py
"""

import streamlit as st
from pathlib import Path

from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader

CHROMA_DIR = "./chroma_db"
DATA_DIR = "data"


@st.cache_resource
def load_vectorstore():
    """Load the existing ChromaDB vector store."""
    embedding_model = OllamaEmbeddings(model="qwen3-embedding")
    vectorstore = Chroma(
        collection_name="chunks_500",
        embedding_function=embedding_model,
        persist_directory=CHROMA_DIR,
    )
    return vectorstore


@st.cache_resource
def load_bm25_retriever():
    """Load documents and build BM25 retriever for hybrid search."""
    loader = DirectoryLoader(DATA_DIR, glob="**/*.pdf", loader_cls=PyPDFLoader)
    documents = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50, separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_documents(documents)
    retriever = BM25Retriever.from_documents(chunks)
    retriever.k = 3
    return retriever


@st.cache_resource
def get_llm():
    """Initialize the LLM."""
    return ChatOllama(model="glm-5:cloud", temperature=0)


def build_chain(retriever, llm):
    """Build a RetrievalQA chain with a custom prompt."""
    custom_prompt = PromptTemplate(
        template="""You are a helpful research assistant that answers questions about reinforcement learning papers based ONLY on the provided context.

Rules:
- Answer based ONLY on the provided context. Do not use external knowledge.
- If the context does not contain enough information, say "I don't have enough information in the provided context to answer this question."
- Cite which paper/source the information comes from when possible.
- Be concise but thorough.

Context:
{context}

Question: {question}

Answer:""",
        input_variables=["context", "question"],
    )

    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": custom_prompt},
    )


def main():
    st.set_page_config(page_title="RL Papers Q&A", page_icon="📚", layout="wide")

    st.title("📚 RL Research Papers Q&A")
    st.caption(
        "RAG-powered Q&A over 10 reinforcement learning papers | "
        "GLM-5 + Qwen3-Embedding + ChromaDB"
    )

    # Sidebar
    with st.sidebar:
        st.header("Settings")

        search_mode = st.radio(
            "Retrieval Mode",
            ["Vector Search", "Hybrid (BM25 + Vector)"],
            help="Toggle between pure vector search and hybrid BM25+vector search.",
        )

        topic_filter = st.selectbox(
            "Filter by Topic (optional)",
            [
                "All Topics",
                "POMDP",
                "Batch RL",
                "Safe RL",
                "Distributed RL",
                "Memory Architecture",
                "Reward Shaping",
                "Predictive Knowledge",
                "World Models",
            ],
        )

        num_results = st.slider("Number of chunks to retrieve", 1, 10, 3)

        st.divider()
        st.header("About")
        st.markdown(
            """
        **Data:** 10 RL research papers (PDF)

        **Models:**
        - LLM: GLM-5 (cloud via Ollama)
        - Embeddings: Qwen3-Embedding-8B

        **Stretch Goals:**
        - A: Chunk comparison
        - B: Hybrid BM25 search
        - C: Metadata filtering
        - D: This Streamlit UI
        - E: Multi-document (PDF+TXT+CSV)
        """
        )

    # Load resources
    vectorstore = load_vectorstore()
    llm = get_llm()

    # Build retriever based on mode
    if search_mode == "Hybrid (BM25 + Vector)":
        bm25_retriever = load_bm25_retriever()
        vector_retriever = vectorstore.as_retriever(search_kwargs={"k": num_results})
        retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_retriever], weights=[0.4, 0.6]
        )
    else:
        search_kwargs = {"k": num_results}
        if topic_filter != "All Topics":
            search_kwargs["filter"] = {"topic": topic_filter}
        retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)

    chain = build_chain(retriever, llm)

    # Query input
    query = st.text_input(
        "Ask a question about the RL papers:",
        placeholder="e.g., How does DreamerV3 handle varying reward magnitudes?",
    )

    if query:
        with st.spinner("Searching and generating answer..."):
            result = chain.invoke({"query": query})

        # Main answer
        st.subheader("Answer")
        st.write(result["result"])

        # Retrieved chunks in sidebar
        with st.sidebar:
            st.divider()
            st.header("Retrieved Chunks")
            for i, doc in enumerate(result["source_documents"]):
                with st.expander(
                    f"Chunk {i+1}: {Path(doc.metadata.get('source', 'unknown')).stem[:30]}..."
                ):
                    st.markdown(f"**Source:** `{doc.metadata.get('source', 'unknown')}`")
                    st.markdown(
                        f"**Topic:** {doc.metadata.get('topic', 'N/A')} | "
                        f"**Year:** {doc.metadata.get('year', 'N/A')}"
                    )
                    st.text(doc.page_content[:500])

    # Example queries
    with st.expander("Example queries to try"):
        examples = [
            "How does DRQN handle partial observability in Atari games?",
            "What is the burn-in technique used in R2D2?",
            "How does DreamerV3 achieve generalization across diverse domains?",
            "What guarantees does CPO provide for safe reinforcement learning?",
            "What is the Gated Transformer-XL architecture?",
        ]
        for ex in examples:
            st.code(ex, language=None)


if __name__ == "__main__":
    main()
