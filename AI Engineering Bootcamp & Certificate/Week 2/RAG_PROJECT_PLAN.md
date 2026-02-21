# RAG Document Q&A System - Claude Code Plan

## Project Overview

Build a RAG (Retrieval-Augmented Generation) powered Q&A system for a graduate-level AI course assignment. The system must load real documents, chunk them, embed and store in a vector DB, test retrieval, build a RAG chain, and evaluate the pipeline. Three stretch goals are included: chunk size comparison, hybrid BM25 search, and a Streamlit UI.

**Submission format:** Jupyter notebook (.ipynb) + README.md with observations

---

## Project Structure

```
rag-qa-system/
├── README.md                    # Observations, failures, what worked
├── rag_pipeline.ipynb           # Main notebook (all 6 steps)
├── app.py                       # Streamlit UI (Stretch Goal D)
├── data/                        # Source documents go here
│   └── (user's documents)
├── eval/
│   └── eval_results.json        # Evaluation scores
├── requirements.txt
└── .env                         # API keys (OpenAI, etc.)
```

---

## Requirements

```txt
langchain>=0.3.0
langchain-community>=0.3.0
langchain-openai>=0.2.0
langchain-chroma>=0.2.0
chromadb>=0.5.0
pypdf>=4.0.0
python-dotenv>=1.0.0
rank-bm25>=0.2.2
streamlit>=1.38.0
jupyter>=1.0.0
unstructured>=0.15.0
tiktoken>=0.7.0
```

---

## Step-by-Step Implementation Plan

### Step 1: Load Documents

**What to do:**
- Use LangChain document loaders appropriate for the data type
- Support multiple formats if possible (PDF, TXT, Markdown, CSV)
- Print: number of documents loaded, sample of first document content (first 500 chars)

**Loaders to consider:**
- `PyPDFLoader` for PDFs
- `TextLoader` for .txt files
- `UnstructuredMarkdownLoader` for .md files
- `CSVLoader` for CSV data
- `DirectoryLoader` to batch-load from `data/` folder

**Code pattern:**
```python
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader

loader = DirectoryLoader("data/", glob="**/*.pdf", loader_cls=PyPDFLoader)
documents = loader.load()

print(f"Documents loaded: {len(documents)}")
print(f"First doc preview:\n{documents[0].page_content[:500]}")
print(f"Metadata: {documents[0].metadata}")
```

---

### Step 2: Chunk Documents

**What to do:**
- Use `RecursiveCharacterTextSplitter`
- Experiment with at least 2 different `chunk_size` values (we will do 3 for stretch goal A: 300, 500, 1000)
- Print: total chunks, smallest chunk char count, largest chunk char count
- Use `chunk_overlap` of ~10-20% of chunk_size

**Code pattern:**
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

def chunk_documents(docs, chunk_size=500, chunk_overlap=50):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_documents(docs)
    
    lengths = [len(c.page_content) for c in chunks]
    print(f"Chunk size: {chunk_size} | Total chunks: {len(chunks)}")
    print(f"Smallest: {min(lengths)} chars | Largest: {max(lengths)} chars")
    print(f"Average: {sum(lengths)/len(lengths):.0f} chars")
    
    return chunks

# Create 3 variants for stretch goal A
chunks_300 = chunk_documents(documents, chunk_size=300, chunk_overlap=30)
chunks_500 = chunk_documents(documents, chunk_size=500, chunk_overlap=50)
chunks_1000 = chunk_documents(documents, chunk_size=1000, chunk_overlap=100)
```

**Observations to record:**
- How many chunks does each size produce?
- Do any chunks seem too small to be useful or too large to be specific?

---

### Step 3: Embed + Store in ChromaDB

**What to do:**
- Use an embedding model (OpenAI `text-embedding-3-small` or a free HuggingFace model)
- Store in ChromaDB with metadata (source filename, page number, chunk_id)
- Create separate collections for each chunk size (for stretch goal A)

**Code pattern:**
```python
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")

# Primary vector store (chunk_size=500)
vectorstore_500 = Chroma.from_documents(
    documents=chunks_500,
    embedding=embedding_model,
    collection_name="chunks_500",
    persist_directory="./chroma_db"
)

# Additional stores for stretch goal A
vectorstore_300 = Chroma.from_documents(
    documents=chunks_300,
    embedding=embedding_model,
    collection_name="chunks_300",
    persist_directory="./chroma_db"
)

vectorstore_1000 = Chroma.from_documents(
    documents=chunks_1000,
    embedding=embedding_model,
    collection_name="chunks_1000",
    persist_directory="./chroma_db"
)
```

**Free alternative (no API key needed):**
```python
from langchain_community.embeddings import HuggingFaceEmbeddings
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
```

---

### Step 4: Test Retrieval (BEFORE wiring up LLM)

**What to do:**
- Run 3 test queries using `similarity_search`
- For each query, print top 3 retrieved chunks
- Manually annotate: is each chunk relevant? Yes/No and why?
- This is worth 15 points on its own

**Code pattern:**
```python
test_queries = [
    "QUERY 1 - replace with a real question about your data",
    "QUERY 2 - replace with a real question about your data",
    "QUERY 3 - replace with a real question about your data",
]

for i, query in enumerate(test_queries):
    print(f"\n{'='*60}")
    print(f"Query {i+1}: {query}")
    print(f"{'='*60}")
    
    results = vectorstore_500.similarity_search(query, k=3)
    
    for j, doc in enumerate(results):
        print(f"\n--- Chunk {j+1} ---")
        print(f"Source: {doc.metadata.get('source', 'unknown')}")
        print(f"Content: {doc.page_content[:300]}...")
        print(f"Relevant? [YES/NO] - [Your reasoning here]")
```

**Stretch Goal B - Hybrid Search with BM25:**
```python
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

bm25_retriever = BM25Retriever.from_documents(chunks_500)
bm25_retriever.k = 3

vector_retriever = vectorstore_500.as_retriever(search_kwargs={"k": 3})

ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.4, 0.6]  # 40% keyword, 60% semantic
)

# Test the same queries with hybrid search
for query in test_queries:
    hybrid_results = ensemble_retriever.invoke(query)
    # Compare with pure vector search results
```

---

### Step 5: Build the RAG Chain

**What to do:**
- Wire up `RetrievalQA` with a custom prompt template
- Run the same 3 test queries through the full chain
- Print the generated answers

**Code pattern:**
```python
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

custom_prompt = PromptTemplate(
    template="""You are a helpful assistant that answers questions based ONLY on the provided context. 
If the context does not contain enough information to answer the question, say "I don't have enough information to answer this question."
Do not make up information or use knowledge outside the provided context.

Context:
{context}

Question: {question}

Answer:""",
    input_variables=["context", "question"]
)

rag_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore_500.as_retriever(search_kwargs={"k": 3}),
    return_source_documents=True,
    chain_type_kwargs={"prompt": custom_prompt}
)

# Run the same 3 queries
for query in test_queries:
    result = rag_chain.invoke({"query": query})
    print(f"\nQ: {query}")
    print(f"A: {result['result']}")
    print(f"Sources: {[doc.metadata for doc in result['source_documents']]}")
```

---

### Step 6: Evaluate

**What to do:**
- Create 5 questions where you KNOW the correct answer from your documents
- Run all 5 through the pipeline
- Score each on 3 dimensions:
  - Retrieval: Did it find the right chunks? (check source_documents)
  - Faithfulness: Is the answer grounded in context, not hallucinated?
  - Correctness: Is the final answer actually right?
- Report scores as X/5 for each metric

**Code pattern:**
```python
eval_set = [
    {
        "question": "REPLACE WITH QUESTION 1",
        "expected_answer": "REPLACE WITH KNOWN ANSWER",
        "expected_source": "WHICH DOCUMENT/SECTION SHOULD IT COME FROM"
    },
    # ... repeat for 5 questions
]

results_table = []

for item in eval_set:
    result = rag_chain.invoke({"query": item["question"]})
    
    # Check retrieval
    retrieved_sources = [doc.metadata.get("source", "") for doc in result["source_documents"]]
    retrieval_correct = # True/False - did it retrieve from the right source?
    
    # Check faithfulness  
    faithful = # True/False - is the answer supported by the retrieved chunks?
    
    # Check correctness
    correct = # True/False - does the answer match expected_answer?
    
    results_table.append({
        "question": item["question"],
        "expected": item["expected_answer"],
        "generated": result["result"],
        "retrieval": "PASS" if retrieval_correct else "FAIL",
        "faithfulness": "PASS" if faithful else "FAIL", 
        "correctness": "PASS" if correct else "FAIL",
    })

# Summary scores
retrieval_score = sum(1 for r in results_table if r["retrieval"] == "PASS")
faithfulness_score = sum(1 for r in results_table if r["faithfulness"] == "PASS")
correctness_score = sum(1 for r in results_table if r["correctness"] == "PASS")

print(f"\nFinal Scores:")
print(f"Retrieval:    {retrieval_score}/5")
print(f"Faithfulness: {faithfulness_score}/5")
print(f"Correctness:  {correctness_score}/5")
```

---

## Stretch Goals

### Goal A: Chunk Size Comparison

Run the full 5-question eval set against all three chunk sizes (300, 500, 1000). Build a comparison table:

| Metric        | chunk=300 | chunk=500 | chunk=1000 |
|---------------|-----------|-----------|------------|
| Retrieval     | X/5       | X/5       | X/5        |
| Faithfulness  | X/5       | X/5       | X/5        |
| Correctness   | X/5       | X/5       | X/5        |

Record observations about WHY certain sizes performed better or worse.

### Goal B: Hybrid Search (BM25 + Vector)

Compare pure vector search vs. hybrid (BM25 + vector) using `EnsembleRetriever`. Run the same 5 eval questions through both and compare retrieval accuracy. Note which queries benefit from keyword matching vs. semantic similarity.

### Goal D: Streamlit UI

Create `app.py` with:
- Text input for questions
- Response display area
- Sidebar showing retrieved chunks with source metadata
- Toggle between vector-only and hybrid retrieval

```python
import streamlit as st

st.title("Document Q&A System")

query = st.text_input("Ask a question about your documents:")

if query:
    with st.spinner("Searching..."):
        result = rag_chain.invoke({"query": query})
    
    st.write("### Answer")
    st.write(result["result"])
    
    with st.sidebar:
        st.write("### Retrieved Chunks")
        for doc in result["source_documents"]:
            st.write(f"**Source:** {doc.metadata.get('source', 'unknown')}")
            st.write(doc.page_content[:200] + "...")
            st.divider()
```

---

## README Template

The README.md should include:

1. **What data I used** - describe the documents and why you chose them
2. **What worked** - which steps went smoothly, what chunk size performed best
3. **What broke** - be honest about failures; this is worth points
4. **Chunk size observations** - what changed between 300/500/1000
5. **Hybrid search observations** - did BM25 help? For which query types?
6. **What I would improve** - if you had more time, what would you change?

---

## Important Notes

- Start with 1 to 3 documents max. Do not try to index hundreds of files.
- If retrieval is bad at Step 4, STOP. Debug chunking and embeddings before moving to Step 5.
- Print intermediate outputs at every step. Visibility = debugging speed.
- Document failures. "I tried X and it broke because Y" is worth more than a clean notebook.
- The eval set (Step 6) is worth 20 points. Do not skip it.
- Store API keys in `.env` file, never hardcode them.
- Use `python-dotenv` to load environment variables.

---

## Grading Checklist

| Criteria | Points | Status |
|----------|--------|--------|
| Working pipeline (all 6 steps end-to-end) | 40 | [ ] |
| Real data (not a tutorial dataset) | 10 | [ ] |
| Retrieval testing with relevance annotations | 15 | [ ] |
| 5-question eval with 3 metrics | 20 | [ ] |
| Written observations in README | 10 | [ ] |
| Stretch Goal A: Chunk comparison | +5 | [ ] |
| Stretch Goal B: Hybrid BM25 search | +5 | [ ] |
| Stretch Goal D: Streamlit UI | +5 | [ ] |
| **Total** | **100 + 15 bonus** | |
