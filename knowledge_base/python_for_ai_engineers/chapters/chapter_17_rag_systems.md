# Chapter 17: RAG Systems

> **Learning Objective**: Build Retrieval-Augmented Generation systems to ground LLM responses.

---

## 17.1 Why RAG?

LLMs have limitations:
- Knowledge cutoff: frozen at training time
- Hallucination: can generate false information
- No access to private/proprietary data

RAG solves this by retrieving relevant documents before generation:
```
User Query → Retrieve Relevant Docs → Inject into Prompt → LLM Generates Answer
```

---

## 17.2 RAG Pipeline

```python
# 1. Document Loading
from langchain.document_loaders import TextLoader
loader = TextLoader("knowledge_base/chapter_01.md")
docs = loader.load()

# 2. Chunking
from langchain.text_splitter import RecursiveCharacterTextSplitter
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)

# 3. Embedding + Vector Store
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma

embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(chunks, embeddings)

# 4. Retrieval
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
docs = retriever.get_relevant_documents("What is Python?")

# 5. Generation
context = "\n\n".join([d.page_content for d in docs])
prompt = f"Context:\n{context}\n\nQuestion: What is Python?\nAnswer:"
```

---

## 17.3 Vector Embeddings

Embeddings convert text into dense vectors in high-dimensional space.
Similar texts have similar vectors (measured by cosine similarity).

```
"cat" → [0.2, 0.5, -0.1, ...]  (384-1536 dimensions)
"kitten" → [0.18, 0.52, -0.08, ...]  ← similar to "cat"
"car" → [-0.3, 0.1, 0.7, ...]  ← different from "cat"
```

---

## 17.4 A3's TF-IDF Retriever

A3 uses a lightweight TF-IDF approach (no embeddings needed):

```python
from src.rag.retriever import get_retriever

retriever = get_retriever()
chunks = retriever.search("Python variables", top_k=3)

for chunk in chunks:
    print(chunk.content[:100])
```

---

## Practice Exercises

1. Build a minimal RAG system: load text, chunk, embed, query.

2. Compare retrieval quality: TF-IDF vs embedding-based search.

3. Add a reranker to improve retrieval precision.

4. Implement a feedback loop: user rates answers, improves retrieval.

---

## Key Takeaways

- RAG = Retrieve relevant docs → Inject into prompt → Generate answer
- Chunk size matters: too small loses context, too large dilutes relevance
- Embeddings enable semantic search beyond keyword matching
- A3 uses TF-IDF for lightweight, zero-dependency retrieval
