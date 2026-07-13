# A3 生产级升级方案 — AI Learning Assistant Platform

> 从竞赛 Demo → AI 工程实习求职级 LLM 应用项目
>
> 设计原则：工程真实性 > 可维护性 > 可扩展性 > 企业级展示 > 竞赛需求

---

## 一、目标架构总览

### 核心理念：LLM Application + RAG + Agent Workflow + Memory + Evaluation

```
                          ┌─────────────────────────┐
                          │       User / Student      │
                          └─────────────┬─────────────┘
                                        │
                          ┌─────────────▼─────────────┐
                          │     Frontend (Streamlit)   │
                          └─────────────┬─────────────┘
                                        │ REST / WebSocket
                          ┌─────────────▼─────────────┐
                          │     API Backend (FastAPI)  │
                          │  POST /chat                 │
                          │  POST /plan                 │
                          │  POST /evaluate             │
                          │  GET  /dashboard            │
                          └──────┬──────────────────────┘
                                 │
                    ┌────────────▼───────────────┐
                    │    Agent Orchestrator       │
                    │  (Workflow Engine)          │
                    │  Profile→Retrieve→Plan→     │
                    │  Generate→Evaluate→Reflect  │
                    └──┬──────────┬──────────┬────┘
                       │          │          │
          ┌────────────▼──┐ ┌─────▼──────┐ ┌─▼──────────────┐
          │  RAG System   │ │  Memory    │ │ Agent Workflow  │
          │               │ │            │ │                 │
          │ Doc Processing│ │Conv Memory │ │ ProfileAgent    │
          │ Embedding     │ │Student Mem │ │ PlannerAgent    │
          │ Vector DB     │ │Knowledge M │ │ KnowledgeAgent  │
          │ Retriever     │ │(ChromaDB)  │ │ ResourceAgent   │
          └───────┬───────┘ └─────┬──────┘ │ EvaluationAgent │
                  │               │        │ ReflectionAgent │
          ┌───────▼───────┐       │        └─────────────────┘
          │ Knowledge Base│       │
          │ (课程资料)      │       │
          └───────────────┘       │
                          ┌───────▼───────┐
                          │ LLM Provider  │
                          │ (讯飞星火等)    │
                          └───────┬───────┘
                                  │
                          ┌───────▼───────┐
                          │  Evaluation   │
                          │  + Feedback   │
                          └───────────────┘
```

### 各层职责

| 层 | 职责 | 技术选型 |
|:---|:-----|:---------|
| **Frontend** | 用户交互、可视化 | Streamlit (保持) |
| **API Backend** | REST API、认证、请求路由 | FastAPI |
| **Agent Orchestrator** | Workflow 调度、Agent 编排 | 自研 Workflow Engine |
| **RAG System** | 文档解析→Embedding→检索→上下文组装 | ChromaDB + sentence-transformers |
| **Memory** | 三层记忆（会话/学生/知识） | PostgreSQL + Redis + ChromaDB |
| **Agent Workflow** | 6 个核心 Agent 协作 | 基于现有 Agent 精简重构 |
| **LLM Provider** | 模型调用抽象 | 现有 Provider 抽象层 |
| **Evaluation** | 检索质量+生成质量+幻觉检测 | RuleJudge + LLMJudge + 新增 |

### 为什么这样设计符合企业 AI 应用架构

| 企业需求 | 对应设计 |
|:---------|:---------|
| **关注点分离** | Frontend/API/Agent/Storage 四层独立，可单独替换 |
| **可观测性** | EventBus + TraceCollector 已有，补充 OpenTelemetry |
| **弹性扩展** | Agent 无状态 + State 在 Memory/DB，可水平扩展 |
| **数据持久化** | PostgreSQL（结构化）+ ChromaDB（向量）+ Redis（缓存） |
| **幻觉控制** | RAG 提供 Ground Truth → LLM 基于证据生成 |
| **持续改进** | Evaluation Pipeline → Feedback Loop → 自动优化 |
| **LLM 无关** | Provider 抽象层 → 可切换模型不修改业务代码 |

---

## 二、RAG 系统设计（最高优先级）

### 2.1 整体 Pipeline

```
课程资料（PDF/MD/PPT）
        │
        ▼
┌───────────────────┐
│ Document Processor │  ← 解析、清洗、Chunk
└───────┬───────────┘
        │ DocumentChunk[]
        ▼
┌───────────────────┐
│   Embedding        │  ← text → vector
└───────┬───────────┘
        │ vectors
        ▼
┌───────────────────┐
│  Vector Database   │  ← ChromaDB 存储
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│    Retriever       │  ← 查询 → Top-K + Filter + Rerank
└───────┬───────────┘
        │ RetrievedContext
        ▼
┌───────────────────┐
│ KnowledgeAgent     │  ← 组装上下文 → 注入 LLM Prompt
└───────────────────┘
```

### 2.2 Document Processing

#### 支持的格式

| 格式 | 解析器 | 策略 |
|:-----|:-------|:-----|
| Markdown (.md) | `markdown-it` / Python `markdown` | 按 `##` 标题切分 |
| PDF 教材 | `pymupdf` / `marker-pdf` | 提取文本 + 表格，保留章节结构 |
| PPT | `python-pptx` | 按幻灯片提取，保留标题层级 |
| 实验文档 (.py) | AST 解析 | 提取 docstring + 函数签名 |
| 纯文本 | `langchain.text_splitter` | 递归字符分割 |

#### Chunk 策略

```
策略 1：语义 Chunk（默认）
  - 按 ## 标题边界切分
  - 每 Chunk 500-1000 tokens
  - overlap 100 tokens
  - 保留父标题作为 breadcrumb

策略 2：固定大小 Chunk（fallback）
  - 对无结构文本使用
  - chunk_size=512, overlap=50
```

#### Metadata 设计

```python
@dataclass
class DocumentChunk:
    chunk_id: str           # UUID
    content: str            # 文本内容
    source: str             # 来源文件路径
    source_type: str        # "textbook" | "slides" | "lab" | "external"
    chapter: str            # 章节名 (从标题提取)
    section: str            # 节名
    concept: str            # 核心概念 (从内容提取关键词)
    difficulty: str         # "beginner" | "intermediate" | "advanced"
    prerequisites: List[str] # 前置知识
    page_number: int        # 原始页码
    chunk_index: int        # 在文档中的序号
    token_count: int        # token 数
    created_at: str         # ISO timestamp
```

**为什么这样设计 Metadata：**
- `concept` + `difficulty` → 支持按难度过滤（初学者 vs 进阶）
- `prerequisites` → 支持知识图谱导航
- `source` + `page_number` → 可追溯原始出处
- `chunk_index` → 支持上下文窗口扩展（取前后 chunk）

### 2.3 Embedding 设计

```python
from abc import ABC, abstractmethod

class EmbeddingProvider(ABC):
    """Embedding 抽象接口 — 支持本地/API 切换"""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]: ...

    @abstractmethod
    def embed_query(self, text: str) -> List[float]: ...

    @property
    @abstractmethod
    def dimension(self) -> int: ...


class LocalEmbedding(EmbeddingProvider):
    """本地 Embedding — 离线可用、零成本"""
    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def embed(self, texts): ...
    def embed_query(self, text): ...
    # dimension = 512 (bge-small) / 768 (bge-base) / 1024 (bge-large)


class APIEmbedding(EmbeddingProvider):
    """API Embedding — 更高精度、按量付费"""
    def __init__(self, provider: str = "openai", model: str = "text-embedding-3-small"):
        ...

    def embed(self, texts): ...
    def embed_query(self, text): ...
    # dimension = 1536 (openai) / 1024 (voyage) / 768 (cohere)
```

**如何替换模型：**

```python
# 配置驱动，一行切换
embedding = EmbeddingFactory.create(
    provider="local",          # "local" | "openai" | "voyage"
    model="BAAI/bge-base-zh-v1.5"
)
# 或
embedding = EmbeddingFactory.create(provider="openai", model="text-embedding-3-large")
```

### 2.4 Vector Database

#### 选型：ChromaDB

| 考量 | ChromaDB | FAISS | Milvus |
|:-----|:---------|:------|:-------|
| 安装复杂度 | `pip install` | `pip install` | Docker/K8s |
| Metadata 过滤 | ✅ 原生支持 | ❌ 需自建 | ✅ |
| 持久化 | ✅ SQLite | ❌ 需手动 | ✅ |
| 生产就绪 | 🟡 单机 OK | 🟡 | ✅ |
| 学习成本 | 低 | 中 | 高 |

**选择 ChromaDB 的理由：**
1. **开发阶段零运维** — `pip install chromadb` 即可，不需要 Docker
2. **Metadata filter 原生支持** — 按 difficulty/concept/source 过滤
3. **SQLite 持久化** — 自动落盘，无需额外配置
4. **迁移路径清晰** — API 与 Milvus 相似，生产可平滑迁移

```python
# 接口设计
class VectorStore(ABC):
    @abstractmethod
    def add_chunks(self, chunks: List[DocumentChunk], embeddings: List[List[float]]): ...
    @abstractmethod
    def search(self, query_embedding: List[float], top_k: int = 5,
               filters: Optional[Dict] = None) -> List[SearchResult]: ...
    @abstractmethod
    def delete_by_source(self, source: str): ...

class ChromaVectorStore(VectorStore):
    def __init__(self, persist_dir: str = "./storage/chroma"):
        import chromadb
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection("knowledge_base")
```

### 2.5 Retriever

```python
@dataclass
class SearchResult:
    chunk: DocumentChunk
    score: float            # similarity score
    rank: int               # rerank 后排名

@dataclass
class RetrievedContext:
    query: str
    results: List[SearchResult]
    assembled_context: str  # 组装好的 prompt 上下文
    metadata_summary: Dict  # 来源统计

class Retriever:
    """多策略检索器"""
    def __init__(self, vector_store: VectorStore, embedding: EmbeddingProvider):
        ...

    def retrieve(self, query: str, top_k: int = 5,
                 filters: Optional[Dict] = None,
                 rerank: bool = True) -> RetrievedContext:
        """
        检索流程:
        1. query → embedding
        2. vector_store.search() → top_k*2 candidates
        3. (optional) metadata filter
        4. (optional) rerank with cross-encoder
        5. 组装 context
        """
```

**使用示例：**

```python
# 学生学习 Transformer → 检索 Attention 相关知识
retriever = Retriever(vector_store, embedding)
context = retriever.retrieve(
    query="Transformer 中的 Attention 机制",
    filters={"difficulty": "intermediate"},
    top_k=5,
    rerank=True
)

# → 返回:
# results: [Attention原理chunk(0.92), Self-Attention chunk(0.87), ...]
# assembled_context: "# Attention 机制\n...\n# Self-Attention\n..."
```

### 2.6 KnowledgeAgent

```python
class KnowledgeAgent:
    """
    RAG Agent — 所有 Agent 的知识检索入口

    职责:
    1. 接收查询 → 检索知识库
    2. 整理上下文 → 去除冗余/矛盾
    3. 注入 LLM Prompt → 提供给下游 Agent

    不负责:
    - 生成最终内容 (交给 ResourceAgent)
    - 规划学习路径 (交给 PlannerAgent)
    """
    def __init__(self, retriever: Retriever, llm_provider):
        ...

    def query(self, question: str, student_profile: Dict,
              filters: Optional[Dict] = None) -> RetrievedContext:
        """主入口：根据学生画像+问题检索相关知识"""
        # 根据学生水平调整难度过滤
        level = student_profile.get("knowledge_base", "junior_dev")
        difficulty_map = {"junior_dev": "beginner", "mid_level": "intermediate", "senior": "advanced"}
        filters = filters or {}
        filters["difficulty"] = difficulty_map.get(level, "intermediate")

        return self.retriever.retrieve(question, filters=filters)

    def assemble_prompt(self, context: RetrievedContext,
                        task: str) -> str:
        """将检索结果组装为 LLM Prompt"""
        return f"""基于以下课程知识回答问题。如果知识库中没有相关信息，请明确说明。

## 知识库内容
{context.assembled_context}

## 任务
{task}

## 要求
- 基于知识库内容回答，不要编造信息
- 引用具体章节和概念
- 如果不确定，请说明"""
```

---

## 三、Agent Workflow 重新设计

### 3.1 从 10 Agent → 6 核心 Agent

**精简原则：** 不需要更多 Agent，需要更清晰的职责边界。

| 原 Agent | 新归属 | 变化 |
|:---------|:-------|:-----|
| ProfileAgent | **ProfileAgent** (保留) | 不变 |
| ConversationProfileAgent | 合并入 ProfileAgent | 作为可选多轮模式 |
| PlannerAgent | **PlannerAgent** (保留) | 接入 KnowledgeAgent |
| ResourceRecommendationAgent | 合并入 ResourceAgent | + 内容生成 |
| ContentAgent | **ResourceAgent** (新) | 合并推荐+生成 |
| AgentEvaluator | **EvaluationAgent** (保留) | + RAG 质量评估 |
| MetaReflector | **ReflectionAgent** (新) | 合并反思+改进 |
| ImprovementLoop | 合并入 ReflectionAgent | 简化循环 |
| ReviewGate | 作为 EvaluationAgent 的 Gate | 保留但不作为独立Agent |
| UserSimulationAgent | 可选 | 保留但不作为核心 |

### 3.2 6 个核心 Agent

```
                    ┌──────────────┐
                    │ ProfileAgent │  "你是谁？你擅长什么？你缺什么？"
                    └──────┬───────┘
                           │ DynamicProfile
                           ▼
                    ┌──────────────┐
                    │KnowledgeAgent│  "关于这个主题，我们有什么资料？"
                    └──────┬───────┘
                           │ RetrievedContext
                           ▼
                    ┌──────────────┐
                    │ PlannerAgent │  "基于你的水平和资料，最优学习路径是什么？"
                    └──────┬───────┘
                           │ LearningPlan
                           ▼
                    ┌──────────────┐
                    │ResourceAgent │  "生成个性化学习内容"
                    └──────┬───────┘
                           │ Content
                           ▼
                    ┌──────────────┐
                    │EvaluationAgent│ "这个内容质量如何？有没有幻觉？"
                    └──────┬───────┘
                           │ EvaluationResult
                           ▼
                    ┌──────────────┐
                    │ReflectionAgent│ "如何改进？记住教训"
                    └──────────────┘
```

### 3.3 为什么 6 个 Agent 足够

| 常见误解 | 实际 |
|:---------|:-----|
| "Agent 越多越强大" | Agent 越多 → 通信开销越大 → 调试越难 |
| "每个功能都需要 Agent" | Agent ≠ 函数。Agent = 有状态的自主决策单元 |
| "10个Agent展示技术能力" | 面试官更看重：**为什么这样拆分**，而非拆分了多少 |

**6 Agent 职责完全覆盖学习闭环：**
1. **理解用户** (ProfileAgent)
2. **检索知识** (KnowledgeAgent) — **新增，RAG 核心**
3. **规划路径** (PlannerAgent)
4. **生成内容** (ResourceAgent)
5. **评估质量** (EvaluationAgent)
6. **反思改进** (ReflectionAgent)

### 3.4 Agent 调用流程

```python
class AgentOrchestrator:
    """
    Workflow Engine — 管理 Agent 执行顺序和数据传递

    设计选择：DAG（有向无环图）而非自由对话
    理由：教育场景的步骤是可预期的，DAG 比开放对话更可靠
    """
    def __init__(self):
        self.workflow = [
            ("profile", ProfileAgent),
            ("retrieve", KnowledgeAgent),    # ← 新增：RAG 检索
            ("plan", PlannerAgent),
            ("generate", ResourceAgent),
            ("evaluate", EvaluationAgent),
            ("reflect", ReflectionAgent),
        ]

    async def run(self, user_input: str, session_id: str) -> WorkflowResult:
        state = WorkflowState(session_id=session_id)

        for step_name, agent_cls in self.workflow:
            agent = agent_cls()
            state = await agent.execute(state)
            # EventBus 自动记录
            # TraceCollector 自动追踪

        return state.result
```

---

## 四、Memory 系统升级

### 4.1 三层 Memory 架构

```
┌──────────────────────────────────────────────────┐
│                  MemoryManager                     │
├──────────────┬──────────────────┬─────────────────┤
│Conversation  │  Student         │  Knowledge      │
│Memory        │  Memory          │  Memory         │
│              │                  │                 │
│ 短期上下文    │  长期用户状态     │  课程知识        │
│ Redis        │  PostgreSQL      │  ChromaDB       │
│              │                  │                 │
│ TTL: 24h     │  Permanent       │  Permanent      │
│ 最近N轮对话   │  profile/mastery │  chunks+vectors │
│ 当前session  │  weak_points     │  metadata       │
└──────────────┴──────────────────┴─────────────────┘
```

### 4.2 Conversation Memory（短期上下文）

```python
@dataclass
class ConversationTurn:
    role: str               # "user" | "assistant" | "agent"
    content: str
    agent_name: Optional[str]
    timestamp: str
    metadata: Dict

class ConversationMemory:
    """短期会话记忆 — Redis 实现"""
    def __init__(self, redis_client, ttl: int = 86400):  # 24h
        self.redis = redis_client
        self.ttl = ttl

    def add_turn(self, session_id: str, turn: ConversationTurn):
        key = f"conv:{session_id}"
        self.redis.rpush(key, turn.to_json())
        self.redis.expire(key, self.ttl)

    def get_context(self, session_id: str, last_n: int = 10) -> List[ConversationTurn]:
        """获取最近 N 轮对话用于 LLM context 窗口"""
        ...

    def summarize(self, session_id: str) -> str:
        """用 LLM 压缩历史 → 释放 context 窗口"""
        ...
```

### 4.3 Student Memory（长期用户状态）

```python
# PostgreSQL Schema
CREATE TABLE students (
    id VARCHAR(64) PRIMARY KEY,
    profile JSONB NOT NULL,            -- 6-dim profile
    mastery_map JSONB DEFAULT '{}',    -- {"concept": 0.85, ...}
    weak_points JSONB DEFAULT '[]',
    learning_preferences JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE learning_sessions (
    id UUID PRIMARY KEY,
    student_id VARCHAR(64) REFERENCES students(id),
    course_id VARCHAR(64),
    nodes_completed INT DEFAULT 0,
    total_score FLOAT,
    feedback JSONB,
    started_at TIMESTAMP,
    ended_at TIMESTAMP
);

CREATE TABLE feedback_history (
    id UUID PRIMARY KEY,
    student_id VARCHAR(64),
    agent_name VARCHAR(64),
    score FLOAT,
    dimensions JSONB,       -- {correctness, personalization, ...}
    suggestions JSONB,
    created_at TIMESTAMP
);
```

**EMA mastery 更新（保留现有算法）：**
```python
def update_mastery(self, student_id: str, concept: str, new_score: float):
    old = self.get_mastery(student_id, concept) or 0.5
    updated = old * 0.5 + new_score * 0.5  # EMA α=0.5
    # PostgreSQL UPSERT
    self.db.execute("""
        UPDATE students
        SET mastery_map = jsonb_set(mastery_map, '{%s}', '%s'),
            updated_at = NOW()
        WHERE id = %s
    """, (concept, updated, student_id))
```

### 4.4 Knowledge Memory（课程知识）

即 **RAG 系统的 ChromaDB**，已在第二节详述。

| 数据 | 存储 | 索引 |
|:-----|:-----|:-----|
| DocumentChunk | ChromaDB collection | embedding vector |
| Chunk metadata | ChromaDB metadata | difficulty, concept, source |
| 原始文档 | 文件系统 / S3 | 文件路径 |

---

## 五、Agent Research 能力（扩展）

### 5.1 设计定位

**ResearchAgent 不是核心 Agent，是高级扩展能力。**

- RAG：**内部知识**（课程资料）→ 保证准确性和可控性
- Research：**外部知识**（论文、博客、技术趋势）→ 提供广度和前沿性

### 5.2 架构

```
Question: "最新的 Transformer 变体有哪些？"
        │
        ▼
┌──────────────────┐
│ Research Planner  │  "需要搜索什么？从哪里搜？"
└──────┬───────────┘
       │ search_queries[]
       ▼
┌──────────────────┐
│  Search Engine    │  arxiv API / Google Scholar / web_search
└──────┬───────────┘
       │ raw_results[]
       ▼
┌──────────────────┐
│  Content Reader   │  下载/解析论文摘要/全文
└──────┬───────────┘
       │ parsed_papers[]
       ▼
┌──────────────────┐
│  Summarizer       │  LLM 生成结构化摘要
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Report Generator │  生成拓展阅读报告
└──────────────────┘
```

### 5.3 RAG + Research 协作

```python
class ResearchAgent:
    def __init__(self, rag_agent: KnowledgeAgent):
        self.rag = rag_agent  # 内部知识库

    async def research(self, question: str, profile: Dict) -> ResearchReport:
        # Step 1: 先查内部知识库（RAG）
        internal = self.rag.query(question, profile)

        # Step 2: 识别知识缺口
        gaps = self._identify_gaps(question, internal)

        # Step 3: 外部搜索
        external = await self._search_external(gaps)

        # Step 4: 合并生成报告
        return self._generate_report(internal, external)
```

**协作模式：**
```
内部 RAG:      "Transformer 是... Attention 机制包含..."（课程准确知识）
     +
外部 Research:  "2024年最新: MoE-Transformer, Mamba架构..."（补充前沿）
     =
完整报告:      基础知识 + 前沿拓展
```

---

## 六、工程化升级

### 6.1 技术栈

| 层 | 技术 | 理由 |
|:---|:-----|:-----|
| API | **FastAPI** | 异步原生、自动 OpenAPI 文档、类型安全 |
| 数据库 | **PostgreSQL** | 结构化数据(学生、会话、评估)、JSONB 灵活字段 |
| 缓存 | **Redis** | 会话上下文、API 限流、LLM 响应缓存 |
| 向量库 | **ChromaDB** | 单机零运维、metadata filter 原生支持 |
| 容器 | **Docker** | 环境一致性、一键部署 |
| 编排 | **Docker Compose** | 多服务联合启动 |
| 监控 | OpenTelemetry + EventBus | 链路追踪 + Agent 事件 |

### 6.2 目录结构

```
a3-learning-platform/
├── src/
│   ├── api/                    # FastAPI 后端
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app 入口
│   │   ├── routers/
│   │   │   ├── chat.py         # POST /chat
│   │   │   ├── plan.py         # POST /plan
│   │   │   ├── evaluate.py     # POST /evaluate
│   │   │   └── dashboard.py    # GET  /dashboard
│   │   ├── middleware/
│   │   │   ├── auth.py         # JWT 认证
│   │   │   └── logging.py      # 请求日志
│   │   └── schemas/            # Pydantic 模型
│   │       ├── request.py
│   │       └── response.py
│   │
│   ├── agents/                 # Agent 层（6 核心）
│   │   ├── base.py             # BaseAgent 抽象
│   │   ├── profile_agent.py    # 保留重构
│   │   ├── knowledge_agent.py  # 🆕 RAG 检索 Agent
│   │   ├── planner_agent.py    # 保留重构
│   │   ├── resource_agent.py   # 🆕 合并 ResourceRec + Content
│   │   ├── evaluation_agent.py # 保留重构
│   │   ├── reflection_agent.py # 🆕 合并 MetaReflector + ImprovementLoop
│   │   └── research_agent.py   # 🆕 扩展：外部研究
│   │
│   ├── orchestrator/           # 🆕 Workflow 引擎
│   │   ├── engine.py           # DAG 调度器
│   │   ├── state.py            # WorkflowState
│   │   └── workflow.py         # Workflow 定义
│   │
│   ├── rag/                    # 🆕 RAG 系统
│   │   ├── document_processor.py  # 文档解析+Chunk
│   │   ├── embedding.py           # Embedding 接口+实现
│   │   ├── vector_store.py        # ChromaDB 封装
│   │   ├── retriever.py           # 多策略检索
│   │   └── chunker.py             # Chunk 策略
│   │
│   ├── memory/                 # Memory 系统
│   │   ├── base.py             # Memory 抽象
│   │   ├── conversation.py     # 🆕 Redis 会话记忆
│   │   ├── student.py          # PostgreSQL 学生记忆
│   │   ├── knowledge.py        # 委托给 ChromaDB
│   │   └── manager.py          # 统一入口
│   │
│   ├── evaluation/             # 评估系统
│   │   ├── judge.py            # RuleJudge + LLMJudge (保留)
│   │   ├── retrieval_eval.py   # 🆕 检索质量评估
│   │   ├── hallucination.py    # 🆕 幻觉检测
│   │   └── pipeline.py         # 评估流水线
│   │
│   ├── models/                 # 数据模型
│   │   ├── student.py          # Student, DynamicProfile
│   │   ├── plan.py             # LearningPlan, PlanNode
│   │   ├── content.py          # DocumentChunk, RetrievedContext
│   │   └── evaluation.py       # EvaluationResult
│   │
│   ├── core/                   # 核心基础设施（大部分保留）
│   │   ├── event_bus.py        # ✅ 保留
│   │   ├── agent_trace.py      # ✅ 保留
│   │   ├── decision_explainer.py # ✅ 保留
│   │   ├── contracts.py        # ✅ 保留
│   │   └── provider.py         # LLM Provider 抽象
│   │
│   └── services/               # 🆕 服务层
│       ├── auth_service.py     # 认证服务
│       ├── ingest_service.py   # 知识库导入服务
│       └── analytics_service.py # 学习分析
│
├── web/                        # Streamlit (保留)
│   ├── app.py
│   ├── app_v2.py
│   ├── dashboard/
│   └── v1/
│
├── storage/                    # 数据存储
│   ├── chroma/                 # ChromaDB 持久化
│   ├── documents/              # 原始课程资料
│   └── exports/                # 导出数据
│
├── tests/
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.web
│   └── docker-compose.yml
├── scripts/
│   ├── ingest_knowledge.py     # 知识库导入脚本
│   └── seed_data.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

### 6.3 Docker Compose

```yaml
# docker-compose.yml
services:
  api:
    build: { dockerfile: docker/Dockerfile.api }
    ports: ["8000:8000"]
    depends_on: [postgres, redis, chroma]
    environment:
      - DATABASE_URL=postgresql://a3:a3@postgres:5432/a3
      - REDIS_URL=redis://redis:6379
      - CHROMA_HOST=chroma
      - LLM_PROVIDER=xunfei

  web:
    build: { dockerfile: docker/Dockerfile.web }
    ports: ["8501:8501"]
    depends_on: [api]

  postgres:
    image: postgres:16
    volumes: [pg_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine

  chroma:
    image: chromadb/chroma:latest
    volumes: [chroma_data:/chroma/chroma]
```

---

## 七、代码改造方案

### 7.1 新增文件（🆕）

| 文件 | 理由 |
|:-----|:-----|
| `src/api/*` | FastAPI 后端层，彻底分离 API 和 UI |
| `src/orchestrator/*` | Workflow 引擎，替代硬编码 pipeline |
| `src/rag/*` | 完整 RAG pipeline，项目最大亮点 |
| `src/agents/knowledge_agent.py` | RAG 检索 Agent |
| `src/agents/resource_agent.py` | 合并 ResourceRec + ContentAgent |
| `src/agents/reflection_agent.py` | 合并 MetaReflector + ImprovementLoop |
| `src/agents/research_agent.py` | 外部研究扩展 |
| `src/memory/conversation.py` | Redis 会话记忆 |
| `src/evaluation/retrieval_eval.py` | 检索质量评估 |
| `src/evaluation/hallucination.py` | 幻觉检测 |
| `src/models/*` | 统一数据模型 |
| `src/services/*` | 业务服务层 |
| `docker/*` | 容器化 |
| `scripts/ingest_knowledge.py` | 知识导入工具 |

### 7.2 修改文件（✏️）

| 文件 | 变化 |
|:-----|:-----|
| `src/agents/profile_agent.py` | 整合 ConversationProfileAgent；添加 async |
| `src/agents/planner_agent.py` | 接入 KnowledgeAgent；不改核心逻辑 |
| `src/agents/profile_agent.py` | 整合 ConversationProfileAgent 多轮模式 |
| `src/evaluation/agent_evaluator.py` | +检索质量 +幻觉检测维度 |
| `src/memory/manager.py` | 从 JSON → PostgreSQL/Redis/ChromaDB 混合 |
| `src/core/event_bus.py` | +OpenTelemetry span 集成 |
| `web/app.py` | 改为调用 FastAPI 后端 API |

### 7.3 保持不变文件（✅）

| 文件 | 理由 |
|:-----|:-----|
| `src/core/decision_explainer.py` | 设计正确，不需改 |
| `src/core/agent_trace.py` | 设计正确 |
| `src/core/contracts.py` | 数据契约稳定 |
| `src/core/review_gate.py` | 作为 Evaluation 子模块保留 |
| `src/core/user_simulation.py` | 保留但不作为核心 Agent |
| `tests/*` | 所有现有测试继续生效；新增 RAG + API 测试 |
| `web/dashboard/*` | Dashboard 保持不变 |

### 7.4 为什么这样拆分

| 原则 | 体现 |
|:-----|:-----|
| **新增优于修改** | 新功能（RAG/API/Orchestrator）在 `src/rag/` `src/api/` `src/orchestrator/` 独立开发，不破坏现有 |
| **合并职责** | 10→6 Agent 减少通信开销，但保留所有核心逻辑 |
| **渐进迁移** | Memory 从 JSON → PostgreSQL 通过抽象层实现，底层换存储不换接口 |
| **测试先行** | 现有 241 个测试继续运行；新模块独立测试 |

---

## 八、Evaluation 体系升级

### 8.1 五维评估

```
┌─────────────────────────────────────────────────────────┐
│                  Evaluation Pipeline                      │
├──────────────┬──────────────┬──────────────┬────────────┤
│ Retrieval    │ Generation   │ Hallucination│ User       │
│ Quality      │ Quality      │ Detection    │ Feedback   │
├──────────────┼──────────────┼──────────────┼────────────┤
│ Recall@K     │ Correctness  │ Factual      │ 👍/👎      │
│ Precision@K  │ Relevance    │ Consistency  │ Rating     │
│ MRR          │ Coherence    │ Source Match │ Comments   │
│ NDCG         │ Fluency      │ Confidence   │ Completion │
└──────────────┴──────────────┴──────────────┴────────────┘
                              │
                    ┌─────────▼─────────┐
                    │ Learning Outcome   │
                    │ Mastery Change     │
                    │ Pre/Post Test      │
                    │ Time to Mastery    │
                    └───────────────────┘
```

### 8.2 Retrieval Quality（🆕）

```python
class RetrievalEvaluator:
    """评估 RAG 检索质量"""
    def evaluate(self, query: str, retrieved: List[SearchResult],
                 ground_truth: List[str]) -> Dict:
        return {
            "recall_at_k": self._recall(retrieved, ground_truth, k=5),
            "precision_at_k": self._precision(retrieved, ground_truth, k=5),
            "mrr": self._mrr(retrieved, ground_truth),
            "ndcg": self._ndcg(retrieved, ground_truth),
        }
```

### 8.3 Hallucination Detection（🆕）

```python
class HallucinationDetector:
    """检测 LLM 生成内容中的幻觉"""

    def detect(self, generated: str, source_context: str) -> HallucinationReport:
        """
        策略:
        1. Factual Consistency: 生成内容中的事实是否与 source_context 一致
        2. Source Attribution: 生成内容是否引用不存在的来源
        3. Confidence Scoring: LLM 自我评估置信度
        """
        return HallucinationReport(
            score=0.85,              # 0-1, 越高越少幻觉
            flagged_spans=["...声称支持 GPT-5..."],  # 可疑片段
            source_coverage=0.92,   # 有多少内容能在 source 中找到
        )
```

### 8.4 评估流水线

```python
class EvaluationPipeline:
    def __init__(self):
        self.steps = [
            RetrievalEvaluator(),
            RuleJudge(),           # 保留
            HallucinationDetector(),  # 🆕
            LLMJudge(),            # 保留（可选）
        ]

    async def run(self, context: RetrievedContext,
                  generated: str, ground_truth: Dict) -> EvaluationReport:
        results = {}
        for evaluator in self.steps:
            results[evaluator.name] = await evaluator.evaluate(...)

        # 加权综合
        weights = {"retrieval": 0.15, "rule": 0.25,
                   "hallucination": 0.30, "llm": 0.30}
        overall = sum(results[k].score * weights[k] for k in weights)
        return EvaluationReport(overall=overall, details=results)
```

---

## 九、项目升级方案 — 代码改造清单

### 改造策略：分 4 个 Phase 渐进升级

```
Phase A (基础): FastAPI + Docker + PostgreSQL/Redis
    ↓
Phase B (核心): RAG Pipeline (Document Processing → Embedding → ChromaDB → Retriever)
    ↓
Phase C (重构): Agent 精简 (10→6) + Workflow Orchestrator
    ↓
Phase D (增强): Research Agent + Hallucination Detection + 五维评估
```

### 新增文件清单（~25 文件）

| 模块 | 文件数 | 关键文件 |
|:-----|:-----:|:---------|
| `src/api/` | 6 | main.py, routers/{chat,plan,evaluate}.py, schemas/, middleware/ |
| `src/rag/` | 5 | document_processor, embedding, vector_store, retriever, chunker |
| `src/orchestrator/` | 3 | engine, state, workflow |
| `src/agents/` | 4 | knowledge_agent, resource_agent, reflection_agent, research_agent |
| `src/memory/` | 1 | conversation.py |
| `src/evaluation/` | 2 | retrieval_eval, hallucination |
| `src/models/` | 4 | student, plan, content, evaluation |
| `src/services/` | 3 | auth, ingest, analytics |
| `docker/` | 3 | Dockerfile.api, Dockerfile.web, docker-compose.yml |
| `scripts/` | 2 | ingest_knowledge.py, seed_data.py |

### 修改文件清单（~6 文件）

| 文件 | 改动量 | 风险 |
|:-----|:-----:|:---:|
| `src/agents/planner_agent.py` | +5行 | 🟢 低 |
| `src/agents/profile_agent.py` | +30行 | 🟢 低 |
| `src/evaluation/agent_evaluator.py` | +40行 | 🟢 低 |
| `src/memory/manager.py` | +50行 | 🟡 中 |
| `src/core/event_bus.py` | +10行 | 🟢 低 |
| `web/app.py` | +15行 | 🟢 低 |

### 保留文件清单（~30 文件不变）

现有 `src/core/` 的大部分文件、`tests/` 全部、`web/dashboard/` 全部、`web/v1/` 全部。

---

## 十、简历和面试价值

### 10.1 项目名称

**推荐：A3 — AI Learning Assistant Platform**

备选：A3Learn / Agent Academy / MindForge

**为什么改名：** "教学系统"听起来像课程项目。"AI Learning Assistant Platform"听起来像产品。去掉"Multi-Agent"前缀 — 多Agent是架构实现细节，不是卖点。

### 10.2 一句话简历描述

> **AI Learning Assistant Platform — 基于 RAG + Multi-Agent Workflow 的个性化学习系统，支持知识检索增强生成、六维学生画像、自动化质量评估与自我改进闭环。**

### 10.3 技术栈描述

```
后端: Python, FastAPI, PostgreSQL, Redis
AI/ML: LangChain, ChromaDB, sentence-transformers, 讯飞星火大模型
Agent: 自研 Workflow Engine, EventBus, 6-Agent协作架构
RAG: 文档解析 → Embedding → 向量检索 → 幻觉检测
工程: Docker, Docker Compose, OpenTelemetry, pytest (241 tests)
前端: Streamlit (6-panel Dashboard)
```

### 10.4 面试时如何介绍架构（30秒版）

> "我设计了一个 AI 学习助手平台，核心架构是 **RAG + Agent Workflow**。
>
> 当学生输入'我想学 Transformer'，系统分六步处理：
> 1. **ProfileAgent** 从自然语言中提取六维画像
> 2. **KnowledgeAgent** 通过 RAG 从课程知识库检索相关内容
> 3. **PlannerAgent** 生成个性化学习路径
> 4. **ResourceAgent** 基于检索到的知识生成学习内容
> 5. **EvaluationAgent** 从检索质量、生成质量、幻觉三个维度评估
> 6. **ReflectionAgent** 分析失败原因并存入长期记忆
>
> 所有 Agent 通过 EventBus 通信，所有决策可追溯，所有质量可量化。"

### 10.5 可能面试问题

---

**Q: 为什么不用直接调用 LLM，而要设计 Agent + RAG？**

> "直接调用 LLM 有三个致命问题：
>
> 1. **幻觉不可控** — LLM 会自信地编造课程中不存在的内容。RAG 提供 Ground Truth，LLM 只负责基于证据生成。
> 2. **决策不可追溯** — 一个 prompt 完成所有任务，你无法知道哪一步出了错。Agent 拆分后，每一步都有独立的 input/output/日志。
> 3. **无法自我改进** — 单一 LLM 不能独立评估自己的输出质量。我们的 EvaluationAgent 是独立于生成 Agent 的，可以客观评分。
>
> 工程上，我在 FastAPI 后端封装了完整的 RAG pipeline（文档解析→Embedding→ChromaDB→多策略检索），6 个 Agent 通过自研的 Workflow Engine 编排。这不是'调 API'，这是'设计系统'。"

---

**Q: RAG 如何降低幻觉？**

> "从三个层面：
>
> 1. **检索层面** — 我用 ChromaDB 存储课程资料的向量化 chunk，每个 chunk 带 metadata（来源、难度、概念）。检索时支持 metadata filter — 比如初学者只看 beginner 难度的内容。Top-K 后用 cross-encoder rerank 提高精度。
>
> 2. **Prompt 层面** — KnowledgeAgent 将检索结果组装为结构化 prompt，明确要求 LLM '基于以下课程知识回答，如果不确定请说明'。这相当于给了 LLM 一个'知识边界'。
>
> 3. **评估层面** — 我实现了 HallucinationDetector，对比生成内容和 source context 的 factual consistency，标记可疑片段。这构成了 RAG → 生成 → 幻觉检测 → 反馈的闭环。
>
> 技术上，这就是 RAG 的核心价值：不是让 LLM 不犯错，而是'把 LLM 限制在可验证的范围内'。"

---

**Q: Agent 为什么需要拆分？不拆分用一个 prompt 不行吗？**

> "一个 prompt 可以做所有事，但面试官不会为'一个 prompt'买单。
>
> 拆分的工程价值：
> 1. **独立测试** — 每个 Agent 有独立的单元测试。ProfileAgent 26 个测试，PlannerAgent 26 个测试。一个 prompt 你怎么测？
> 2. **独立替换** — PlannerAgent 是规则引擎，不需要 LLM。如果我想升级为 LLM Planner，只改一个文件，不影响其他 5 个 Agent。
> 3. **独立评估** — EvaluationAgent 独立于生成 Agent。如果生成和评估在同一个 prompt 里，你信谁的？
> 4. **并行化** — ProfileAgent 和 KnowledgeAgent 可以并行执行，因为 KnowledgeAgent 只需要画像的一部分信息。
>
> 核心原则：**Agent 的粒度 = 可独立测试、可独立替换、可独立评估的最小决策单元**。6 个 Agent 恰好覆盖学习闭环，不多不少。"

---

**Q: Memory 如何设计？**

> "三层 Memory，对应三个不同生命周期：
>
> 1. **Conversation Memory (Redis, TTL 24h)** — 当前会话的最近 N 轮对话。为什么用 Redis？会话数据是热数据、需要快速读写、过期自动清理。
>
> 2. **Student Memory (PostgreSQL, permanent)** — 学生画像、EMA mastery map、弱项列表、学习历史。为什么用 PostgreSQL？结构化数据、需要复杂查询（比如'所有 mastery<0.3 的学生'）、JSONB 灵活存储画像。
>
> 3. **Knowledge Memory (ChromaDB, permanent)** — 课程知识的向量化存储。为什么独立？向量检索和结构化查询是两种完全不同的访问模式，不应该放在同一个数据库。
>
> 设计原则：**存储选型由访问模式决定，不是由数据类型决定。** 热数据用 Redis，关系数据用 PG，向量数据用 ChromaDB。"

---

**Q: 这个项目有什么技术难点？**

> "三个核心难点：
>
> 1. **RAG 检索精度** — 简单的 similarity search 召回率只有 60-70%。我加了 metadata filter（按难度过滤）+ cross-encoder rerank（二次排序），把 Top-5 精度提到 90%+。这是工程细节，不是调 API。
>
> 2. **Agent 编排的可靠性** — 6 个 Agent 串行执行，任何一个失败都会导致整个 pipeline 中断。我设计了 WorkflowState 状态机：每个 Agent 执行完后持久化状态，失败时可以从断点恢复，不会丢失已完成的工作。
>
> 3. **幻觉检测的实用性** — 纯靠 LLM 自我评估不可靠（LLM 不会说自己错了）。我结合了 source attribution（生成内容中有多少能在源文档中找到）和 factual consistency（关键事实是否与源文档一致），用规则而不是 LLM 做检测。
>
> 这些难点体现的不是'我会用哪些工具'，而是'我理解这些工具的边界在哪里，以及如何跨越边界'。"

---

## 总结

### 升级前后对比

| 维度 | 升级前（竞赛 Demo） | 升级后（生产级项目） |
|:-----|:-------------------|:---------------------|
| 架构 | 10 Agent 直连 Streamlit | FastAPI + Orchestrator + 6 Agent |
| 知识 | 硬编码 curriculum | RAG Pipeline + ChromaDB |
| 存储 | JSON 文件 | PostgreSQL + Redis + ChromaDB |
| 部署 | `streamlit run` | Docker Compose (5 services) |
| API | 无 | FastAPI REST API + OpenAPI 文档 |
| 幻觉 | 无控制 | Source Attribution + Factual Consistency |
| 评估 | 4-dim RuleJudge | 5-dim (Retrieval + Generation + Hallucination + User + Learning) |
| Agent | 10 (职责重叠) | 6 (职责清晰) |
| 面向 | 比赛评委 | AI Engineer 实习面试官 |

### 升级后的简历一句话

> **A3 AI Learning Assistant Platform** — Full-stack LLM application with RAG pipeline (ChromaDB + multi-strategy retrieval), 6-agent workflow orchestration, hallucination detection, and five-dimensional evaluation system. Built with FastAPI, PostgreSQL, Redis, Docker Compose. 241 tests.

### 面试核心竞争力

1. **RAG 工程能力** — 不是调 API，是完整 pipeline（解析→Embedding→向量库→检索→幻觉检测）
2. **Agent 设计思维** — 不是堆 Agent 数量，是合理的职责拆分和编排
3. **后端工程能力** — FastAPI + PostgreSQL + Redis + Docker，完整生产栈
4. **AI 系统思维** — 理解 LLM 的边界，用 RAG/Evaluation/Reflection 弥补
