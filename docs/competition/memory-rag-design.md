# Memory & RAG Design

## Memory Manager

The Memory Manager provides persistent, session-scoped storage for agent state and student profiles.

### Architecture

```
┌─────────────────────────────────────────────┐
│              MemoryManager                  │
│                                             │
│  ┌─────────────┐  ┌──────────────────────┐ │
│  │  Short-term  │  │    Long-term Store   │ │
│  │  (session)   │  │    (SQLite)          │ │
│  │             │  │                      │ │
│  │ · Profile   │  │ · Learning history   │ │
│  │ · Plan      │  │ · Quiz results       │ │
│  │ · Trace     │  │ · Profile snapshots  │ │
│  └─────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────┘
```

### Session Isolation
Each API request creates an independent MemoryManager instance with session-scoped storage. This prevents data leakage between concurrent users.

```python
# Request-scoped isolation
mm = MemoryManager(student_id="user_123")
mm.update_profile(profile)
mm.recall()  # Returns only user_123's data
```

### Persistence
Long-term memory is backed by SQLite in WAL mode for concurrent read access. Memory snapshots are stored as JSON blobs with timestamps for trend analysis.

## RAG (Retrieval-Augmented Generation)

### TF-IDF Retriever

A lightweight, zero-dependency TF-IDF retriever indexes knowledge base content for semantic search.

```
┌──────────────────────────────────────────────────────┐
│                   RAG Pipeline                        │
│                                                      │
│  Student Query                                       │
│       │                                              │
│       ▼                                              │
│  ┌──────────┐    ┌──────────────┐    ┌────────────┐ │
│  │TF-IDF    │───▶│ Top-K        │───▶│ Knowledge  │ │
│  │Vectorize │    │ Retrieval    │    │ Context    │ │
│  └──────────┘    └──────────────┘    └────────────┘ │
│                                                      │
│  Knowledge Base (Markdown chapters)                  │
│  ┌──────────────────────────────────────────────┐   │
│  │ Python Fundamentals · OOP · Decorators · ... │   │
│  │ Multi-Agent Architecture · EventBus · ...    │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

### Design Decisions

| Decision | Rationale |
|:---------|:----------|
| TF-IDF over embeddings | Zero external dependencies, fast, interpretable |
| Lazy singleton | Single index load, reused across requests |
| Markdown chapters | Human-readable, easy to update, version-controlled |
| Top-K = 3 | Balances relevance with context window limits |

### Knowledge Base Structure

```
knowledge_base/
├── python_curriculum/
│   ├── 01_basics.md         # Variables, types, operators
│   ├── 02_control_flow.md   # If/else, loops
│   ├── ...
│   └── 20_advanced.md       # Metaclasses, descriptors
└── multi_agent/
    ├── architecture.md
    ├── event_bus.md
    └── agent_patterns.md
```

### Fallback Chain

When RAG retrieval fails (empty KB, no matches):
1. TF-IDF search → if found, enrich prompt with context
2. Keyword matching → fallback to simple string matching
3. Rule-based → deterministic content generation
4. Mock → pre-seeded demo responses

## Performance

| Operation | Latency | Notes |
|:----------|:--------|:------|
| TF-IDF index build | ~200ms | One-time on first query |
| Top-K retrieval | <5ms | In-memory cosine similarity |
| Memory recall | <1ms | SQLite indexed lookup |
| Memory update | ~5ms | JSON serialization + INSERT |
