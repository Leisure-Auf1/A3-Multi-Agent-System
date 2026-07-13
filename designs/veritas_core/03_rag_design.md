# Veritas_Core — RAG 课程知识增强模块设计

> **定位:** RAG 不是项目主体，而是服务于学习资源生成的 **Course Knowledge Enhancement Module**  
> **核心原则:** RAG 为 ResourceAgent 提供可靠知识上下文，不是独立的知识平台

---

## 一、RAG 在 Veritas_Core 中的位置

```
                         课程资料
                (PDF / Markdown / PPT / 教材)
                            │
                            ▼
┌───────────────────────────────────────────┐
│              RAG ENGINE                     │
│                                             │
│  Parser ──→ Chunker ──→ Embedder ──→ VDB  │
│    │                                    │   │
│    └──────────── 离线索引 ──────────────┘   │
│                                             │
│  Retriever ──→ ContextBuilder (在线检索)    │
└───────────────────┬───────────────────────┘
                    │
                    ▼
            ┌───────────────┐
            │ KnowledgeAgent │  ← 知识检索入口
            └───────┬───────┘
                    │ KnowledgeContext
                    ▼
            ┌───────────────┐
            │ ResourceAgent  │  ← 注入LLM Prompt → 生成学习资源
            └───────────────┘
```

**RAG 的两个使用场景：**

| 场景 | 触发Agent | 检索目标 | 输出 |
|:-----|:----------|:---------|:-----|
| **知识诊断** | KnowledgeAgent.diagnose() | 课程知识结构 + 概念前置依赖 | KnowledgeGap |
| **资源生成** | KnowledgeAgent.retrieve() | 具体概念的知识细节 | KnowledgeContext |

---

## 二、文档处理 Pipeline

### 2.1 支持的格式

| 格式 | 解析器 | 策略 |
|:-----|:-------|:-----|
| **Markdown (.md)** | Python `markdown` + 自定义解析 | 按 `##` 标题层级切分，保留章节/小节 breadcrumb |
| **PDF 教材** | `pymupdf` (PyMuPDF) | 提取文本 + 表格，保留页码和章节结构 |
| **PPT** | `python-pptx` | 按幻灯片提取，保留标题层级 |
| **Python 源码** | AST 解析 | 提取 docstring + 函数签名 + 注释 |

### 2.2 Chunk 策略

```
策略 1: 语义分块 (默认)
  - 按 ## 标题边界切分
  - chunk_size: 512 tokens
  - overlap: 64 tokens
  - 保留父标题作为 breadcrumb (如: "Ch4: RAG > 4.2 Embedding")
  - Metadata: {chapter, section, concept, difficulty, prerequisites}

策略 2: 固定大小分块 (Fallback, 用于无结构文本)
  - chunk_size: 512, overlap: 64
  - 递归字符分割 (RecursiveCharacterTextSplitter)
```

### 2.3 Metadata 设计

```python
@dataclass
class ChunkMetadata:
    """每个 Chunk 携带的元数据 — 支持精准过滤"""
    source_file: str         # "ch04_rag.md"
    source_type: str         # "textbook" | "slides" | "lab"
    chapter: str             # "RAG Systems"
    section: str             # "4.2 Embedding Models"
    concept: str             # "text-embedding-ada-002" (核心概念)
    difficulty: str          # "beginner" | "intermediate" | "advanced"
    prerequisites: List[str] # ["vector_math", "transformer"]
    page_number: int         # 原始页码 (PDF溯源)
    chunk_index: int         # 在文档中的序号
```

---

## 三、Embedding 设计

```
┌────────────────────────────────────────────────┐
│           EmbeddingProvider (抽象)               │
│                                                │
│  embed(texts: List[str]) → List[List[float]]   │
│  embed_query(text: str) → List[float]          │
│  dimension: int                                 │
└───────────┬────────────────────────────────────┘
            │
     ┌──────┴──────┐
     ▼             ▼
┌──────────┐  ┌──────────────┐
│ Local    │  │ API          │
│ BGE-M3   │  │ DeepSeek     │
│ (768dim) │  │ (1024dim)    │
│          │  │              │
│ 零成本    │  │ 更高精度      │
│ 离线可用  │  │ 需要API Key   │
└──────────┘  └──────────────┘
```

**选型:**
- **开发/原型/零成本:** `BAAI/bge-small-zh-v1.5` (512维, 中文优化)
- **生产:** `BAAI/bge-m3` (1024维, 多语言, 多粒度, 本地部署) 或 API Embedding
- **切换:** EmbeddingFactory 一行配置切换，不影响上层代码

---

## 四、Vector Database

**选型: ChromaDB**

| 考量 | ChromaDB | FAISS | Milvus |
|:-----|:---------|:------|:-------|
| **安装** | `pip install` | `pip install` | Docker/K8s |
| **Metadata 过滤** | ✅ | ❌ 需自建 | ✅ |
| **持久化** | ✅ SQLite | ❌ | ✅ |
| **开发体验** | 极佳 (Python native) | 中 | 复杂 |
| **规模** | 单机 (<100K chunks) | 单机 (<10M) | 分布式 (>100M) |

**选择 ChromaDB 的理由：**
1. 零运维 — 不需要 Docker，`pip install chromadb` 即可
2. 内置 Metadata 过滤 — 按 difficulty/chapter/concept 精准过滤
3. SQLite 持久化 — 自动落盘，数据不丢失
4. 迁移路径 — 通过 `BaseRetriever` 接口，生产可升级至 Milvus

---

## 五、Retriever 设计

```python
class BaseRetriever(ABC):
    """检索器抽象接口"""

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5,
                 filters: Optional[Dict] = None) -> RetrievalResult:
        """
        检索流程:
        1. query → embedding (embed_query)
        2. VectorDB.search(query_embedding, top_k=top_k*2, filters)
        3. (可选) Cross-Encoder Reranking
        4. 返回 top_k 结果
        """
        ...

class ChromaRetriever(BaseRetriever):
    def retrieve(self, query, top_k=5, filters=None):
        # 1. Embed query
        q_embed = self.embedder.embed_query(query)

        # 2. Search with metadata filters
        # filters = {"difficulty": "intermediate", "chapter": "RAG Systems"}
        results = self.collection.query(
            query_embeddings=[q_embed],
            n_results=top_k * 2,
            where=filters,  # ChromaDB metadata filter
        )

        # 3. (Optional) Rerank with Cross-Encoder
        if self.reranker:
            results = self.reranker.rerank(query, results, top_k)

        # 4. Build RetrievalResult
        return RetrievalResult(
            query=query,
            chunks=[self._to_chunk(r) for r in results[:top_k]],
            scores=[r["distance"] for r in results[:top_k]],
            retrieval_method="hybrid" if filters else "dense",
        )
```

**检索策略：**

| 策略 | 方法 | 适用场景 |
|:-----|:-----|:---------|
| **Dense (默认)** | 向量相似度 (cosine) | 语义搜索，理解同义词 |
| **Metadata Filter** | ChromaDB `where` clause | 按难度/章节过滤 |
| **Hybrid (未来)** | Dense + BM25 关键词 | 精准 + 语义结合 |
| **Reranking** | Cross-Encoder | 对候选结果精排 |

---

## 六、Context Builder — 上下文组装

```python
class ContextBuilder:
    """将检索到的 Chunks 组装为 LLM 可用的 Prompt 上下文"""

    def build(self, results: RetrievalResult,
              task_type: str = "notes") -> str:
        """
        组装上下文文本。

        根据 task_type 调整格式:
        - "notes": 详细的知识陈述, 保留层级结构
        - "exercises": 提取关键概念和事实, 用于出题
        - "mindmap": 提取概念关系和层级
        - "code_lab": 提取代码示例和实现细节
        """
        context_parts = []
        for i, (chunk, score) in enumerate(zip(results.chunks, results.scores)):
            part = f"""[Source {i+1}: {chunk.metadata['section']}]
Relevance: {score:.2f}

{chunk.content}
"""
            context_parts.append(part)

        return "\n---\n".join(context_parts)

    def build_prompt(self, context: str, task: str,
                     profile: DynamicProfile) -> str:
        """组装完整的 LLM Prompt"""
        return f"""基于以下课程知识回答。如果知识库中没有相关信息，请明确说明。

## 知识库内容 (来自课程 "{profile.learning_goal}")
{context}

## 任务
{task}

## 学生背景
- 知识水平: {profile.knowledge_base}
- 认知风格: {profile.cognitive_style}
- 资源偏好: {profile.resource_preference}

## 要求
- 基于知识库内容回答，不要编造信息
- 引用具体章节 (标注 [Source N])
- 适配学生的知识水平和认知风格
- 如果不确定，请说明而非猜测
"""
```

---

## 七、ChromaDB Collection 设计

```python
# 初始化
import chromadb
client = chromadb.PersistentClient(path="./storage/chroma")

# 课程知识 Collection
collection = client.get_or_create_collection(
    name="course_knowledge",
    metadata={
        "description": "课程知识库 — 所有课程资料的分块向量",
        "embedding_model": "BAAI/bge-small-zh-v1.5",
        "chunk_size": 512,
        "overlap": 64,
    }
)

# 添加文档
collection.add(
    ids=[chunk.chunk_id for chunk in chunks],
    documents=[chunk.content for chunk in chunks],
    metadatas=[{
        "source": chunk.metadata.source_file,
        "chapter": chunk.metadata.chapter,
        "section": chunk.metadata.section,
        "concept": chunk.metadata.concept,
        "difficulty": chunk.metadata.difficulty,
    } for chunk in chunks],
    embeddings=embeddings,
)

# 带过滤的查询示例
results = collection.query(
    query_texts=["Attention机制的工作原理"],
    n_results=5,
    where={"difficulty": "intermediate"},  # 只看中级难度
)
```

---

## 八、RAG 模块接口

```python
# src/rag/__init__.py — 对外暴露的接口

from .parser import DocumentParser
from .chunker import SemanticChunker
from .embedder import EmbeddingFactory
from .retriever import ChromaRetriever, RetrievalResult
from .context_builder import ContextBuilder

# KnowledgeAgent 使用示例
class KnowledgeAgent(BaseAgent):
    def __init__(self, ctx: AgentContext):
        self.retriever = ChromaRetriever(
            embedder=EmbeddingFactory.create("local", "BAAI/bge-small-zh-v1.5"),
            persist_dir="./storage/chroma",
        )
        self.context_builder = ContextBuilder()

    def retrieve(self, query: str, student_level: str) -> KnowledgeContext:
        difficulty_map = {
            "junior_dev": "beginner",
            "mid_level": "intermediate",
            "senior": "advanced",
        }
        results = self.retriever.retrieve(
            query=query,
            top_k=5,
            filters={"difficulty": difficulty_map.get(student_level, "intermediate")},
        )
        context_text = self.context_builder.build(results, task_type="notes")
        return KnowledgeContext(
            chunks=results.chunks,
            assembled_text=context_text,
            sources=[c.metadata["source_file"] for c in results.chunks],
        )
```

---

## 九、RAG 不是独立平台 — 设计边界

| ✅ RAG 做的事 | ❌ RAG 不做的事 |
|:-------------|:---------------|
| 解析课程资料，建立向量索引 | 通用文档搜索 |
| 根据学生查询检索相关知识 | 对话式问答 |
| 为 ResourceAgent 提供知识上下文 | 独立的知识问答服务 |
| 按难度/章节过滤检索结果 | 知识图谱推理 |
| 记录检索来源（可溯源） | 动态网页抓取 |
