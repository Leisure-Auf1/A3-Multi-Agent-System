# Veritas_Core — Trustworthy Agentic AI Platform

> **定位：** 面向真实工程场景的可信 Agentic AI 平台  
> **核心命题：** 知识可靠性 × 模型幻觉治理 × 可解释 Agent 工作流 × 三层记忆架构 × 全链路可观测  
> **前身：** A3 Multi-Agent Learning System → 从教育 Demo 升华为通用 AI 工程平台  
> **设计原则：** 保留核心资产，渐进式重构，工程优先，模块解耦

---

## 目录

1. [资产盘点与迁移决策](#1-资产盘点与迁移决策)
2. [总体架构](#2-总体架构)
3. [RAG Knowledge Engine](#3-rag-knowledge-engine)
4. [Agent Workflow 系统](#4-agent-workflow-系统)
5. [Memory Architecture](#5-memory-architecture)
6. [Trust Layer — 评估与可信机制](#6-trust-layer--评估与可信机制)
7. [Observability 系统](#7-observability-系统)
8. [Research Agent 扩展](#8-research-agent-扩展)
9. [工程化部署](#9-工程化部署)
10. [代码目录设计](#10-代码目录设计)
11. [迁移方案](#11-迁移方案)
12. [ADR — 架构决策记录](#12-adr--架构决策记录)
13. [升级路线图](#13-升级路线图)
14. [风险分析](#14-风险分析)
15. [GitHub 展示方案](#15-github-展示方案)
16. [AI Engineer 实习价值分析](#16-ai-engineer-实习价值分析)

---

## 1. 资产盘点与迁移决策

### 1.1 现有 A3 资产分析

| 模块 | 当前形态 | 决策 | 理由 |
|:---|:---|:---|:---|
| **EventBus** | Singleton AgentEventBus | ✅ **保留** | 成熟的解耦通信机制，生产级可用 |
| **TraceCollector** | AgentTraceCollector + JSON | ✅ **保留+升级** | 核心可观测资产，升级 Schema 支持 RAG/LLM 链 |
| **LLMProvider** | Interface + XunfeiSpark/Mock | ✅ **保留+扩展** | 抽象层设计良好，扩展 OpenAI/Anthropic 适配器 |
| **ReviewGate** | 3-gate (AST/Pytest/Judge) | ✅ **保留** | 独有的内容安全校验管线，迁移到 Trust Layer |
| **StudentMemory** | JSON + EMA mastery | 🔄 **抽象升级** | → UserStateMemory (通用化) |
| **ExperienceMemory** | 关键词召回 JSON | 🔄 **抽象升级** | → KnowledgeMemory (Vector DB) |
| **ProfileAgent** | 6-dim 规则引擎 | 🔄 **保留+通用化** | → UserProfileAgent (不限教育场景) |
| **PlannerAgent** | 规则表路径规划 | 🔄 **重构** | → WorkflowPlanner (通用任务规划) |
| **ResourceGenAgent** | 6 类教育资源 | 🔄 **降级为插件** | → 不再是核心 Agent，作为 ContentPlugin |
| **AgentEvaluator** | 4-dim 评分 | 🔄 **升级** | → TrustEvaluator (多维度可信评估) |
| **MetaReflector** | 根因分析 | 🔄 **保留+升级** | → ReflectionAgent |
| **ImprovementLoop** | 策略注入 | 🔄 **保留+升级** | → 融入 Trust Layer 反馈闭环 |
| **ConversationProfileAgent** | 多轮对话画像 | ❌ **移除** | 教育场景专用，非通用平台需要 |
| **ResourceRecommendationAgent** | 教育资源推荐 | ❌ **移除** | 教育场景专用 |
| **KnowledgeBase loader** | Markdown 解析 | 🔄 **升级** | → DocumentParser (通用文档解析) |
| **ContentAgent** | 5-asset 生成 | 🔄 **降级为插件** | → ContentPlugin |
| **Council** (v4) | Agent 协商 | ❌ **暂不纳入** | 竞赛特性，非生产优先级 |
| **KG** (v4) | NetworkX 知识图谱 | ❌ **暂不纳入** | 领域特定，RAG 已覆盖知识检索 |

### 1.2 迁移原则

```
保留 (KEEP):      EventBus, TraceCollector, LLMProvider, ReviewGate
抽象升级 (REFINE): Memory → 3-Tier, Profile → UserProfile, Evaluator → TrustLayer
重构 (REBUILD):   Planner → Workflow, ResourceGen → Plugin system
移除 (DROP):      教育专用模块, Council, KG (这些留在 A3 分支)
新增 (NEW):       RAG Engine, FastAPI Layer, Docker部署, Research Agent
```

---

## 2. 总体架构

### 2.1 分层架构图

```
┌──────────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                      │
│                                                                       │
│   ┌──────────────────┐    ┌──────────────────┐                       │
│   │ Web UI (Streamlit)│    │ API Consumers     │                      │
│   │ Debug Dashboard   │    │ (CLI / SDK / 3rd) │                      │
│   └────────┬─────────┘    └────────┬─────────┘                       │
└────────────┼──────────────────────┼──────────────────────────────────┘
             │                      │
             └──────────┬───────────┘
                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         API LAYER (FastAPI)                            │
│                                                                       │
│   ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐       │
│   │ /chat     │  │ /rag/query│  │ /agent/run│  │ /eval     │       │
│   │ WebSocket │  │ REST      │  │ Async Job │  │ Report    │       │
│   └───────────┘  └───────────┘  └───────────┘  └───────────┘       │
└─────────────────────────┬────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    AGENT ORCHESTRATOR                                  │
│                                                                       │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    Workflow Engine                            │   │
│   │   User Intent → Task Decomposition → Agent Dispatch → Result │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│   ┌───────────┐  ┌────────────┐  ┌───────────┐  ┌────────────┐     │
│   │ProfileAgent│  │KnowledgeAgent│  │PlannerAgent│  │ExecutionAgent│  │
│   │用户理解     │  │知识检索      │  │任务规划     │  │任务执行      │  │
│   └───────────┘  └────────────┘  └───────────┘  └────────────┘     │
│                                                                       │
│   ┌───────────────┐  ┌──────────────────┐                            │
│   │EvaluationAgent│  │ReflectionAgent    │                            │
│   │质量评估        │  │策略优化           │                            │
│   └───────────────┘  └──────────────────┘                            │
└──────────────────┬───────────────────────────────────────────────────┘
                   │
     ┌─────────────┼─────────────┬──────────────┐
     ▼             ▼             ▼              ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│   RAG    │ │  MEMORY  │ │  TRUST   │ │ OBSERVABILITY│
│  ENGINE  │ │  LAYER   │ │  LAYER   │ │   LAYER      │
│          │ │          │ │          │ │              │
│ Parser   │ │Conv Mem  │ │Retrieval │ │ TraceCollector│
│ Chunker  │ │User State│ │Generation│ │ Prompt Logger │
│ Embedder │ │Knowl Mem │ │Hallucina │ │ Token Tracker │
│ Retriever│ │          │ │Safety    │ │ Decision Log  │
│ Context  │ │          │ │Feedback  │ │ Latency Metric│
└────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘
     │            │            │               │
     └────────────┼────────────┼───────────────┘
                  │            │
                  ▼            ▼
         ┌────────────┐  ┌──────────┐
         │  Vector DB │  │PostgreSQL│
         │ (ChromaDB) │  │ + Redis  │
         └────────────┘  └──────────┘
                  │
                  ▼
         ┌────────────────┐
         │  LLM PROVIDER  │
         │ (OpenAI/Spark/ │
         │  Anthropic/    │
         │  Local vLLM)   │
         └────────────────┘
```

### 2.2 模块职责

| 层 | 职责 | 关键设计 |
|:---|:---|:---|
| **Frontend** | 用户交互界面 + Debug 仪表盘 | Streamlit (复用) + REST API 消费者 |
| **API Layer** | REST + WebSocket 网关 | FastAPI, async/await, 请求验证 |
| **Orchestrator** | Agent 工作流调度 | Workflow Engine: Intent→Decompose→Dispatch→Collect |
| **RAG Engine** | 知识检索与上下文构建 | Parser→Chunker→Embedder→Retriever→ContextBuilder |
| **Memory Layer** | 三层记忆管理 | ConvMem(Redis) / UserState(PostgreSQL) / KnowMem(VectorDB) |
| **Trust Layer** | 可信评估与安全 | RetrievalEval + GenerationEval + HallucinationDetect + SafetyCheck |
| **Observability** | 全链路追踪 | TraceCollector + PromptLog + TokenTracker + DecisionLog |

### 2.3 数据流

```
User Input
    │
    ▼
API Layer (FastAPI) ──→ validate + auth
    │
    ▼
Orchestrator.receive(intent)
    │
    ├──→ ProfileAgent: 加载用户画像 (UserStateMemory)
    │
    ├──→ KnowledgeAgent: RAG 检索相关知识 (Vector DB)
    │
    ├──→ PlannerAgent: 任务分解为子步骤
    │
    ├──→ ExecutionAgent: 逐步骤执行 (LLM call / Tool call)
    │       │
    │       └──→ Trust Layer: 评估每次执行输出
    │              ├── Retrieval eval (检索相关性)
    │              ├── Generation eval (生成质量)
    │              ├── Hallucination check (幻觉检测)
    │              └── Safety check (安全审查)
    │
    ├──→ ReflectionAgent: 若评估分数低, 触发反思
    │
    └──→ Observability: 全程 Trace 记录
    │
    ▼
Response → User
    │
    ▼
Memory Update: ConversationMemory + UserStateMemory 异步更新
```

### 2.4 为什么符合现代 LLM 应用架构

| 特征 | Veritas_Core 实现 | 业界对标 |
|:---|:---|:---|
| **RAG 为核心** | 独立 RAG Engine 层, Parser/Chunker/Embedder/Retriever 完整链路 | LangChain / LlamaIndex |
| **Agent 工作流** | Orchestrator + 6 Agent 职责分明, 非管线式 | CrewAI / AutoGen |
| **多层记忆** | ConvMem(短期) + UserState(长期) + KnowMem(资产) | MemGPT / Letta |
| **可信评估** | Retrieval+Generation+Hallucination+Safety 四维独立评分 | TruLens / DeepEval |
| **全链路可观测** | TraceCollector + PromptLog + TokenTracker + DecisionLog | LangSmith / Phoenix |
| **Provider 抽象** | LLMProvider 接口, 多后端可替换 | LiteLLM |
| **API 化** | FastAPI REST + WebSocket, 非单体 Streamlit | 生产级部署 |

---

## 3. RAG Knowledge Engine

### 3.1 完整流程

```
Documents (PDF / MD / PPT / Web)
    │
    ▼
┌──────────┐
│  Parser  │  按类型解析: PDF→PyMuPDF, MD→markdown, PPT→python-pptx, Web→HTML2Text
└────┬─────┘
     │
     ▼
┌──────────┐
│ Chunker  │  语义分块: 按段落 + 重叠窗口 (chunk_size=512, overlap=64)
└────┬─────┘  + 保留层级元数据 (章节/页码)
     │
     ▼
┌──────────┐
│ Embedder │  text → vector (OpenAI text-embedding-3-small / local BGE)
└────┬─────┘
     │
     ▼
┌──────────────┐
│ Vector DB    │  ChromaDB (开发/小规模) → Milvus (生产/大规模)
└────┬─────────┘
     │
     ▼
┌──────────┐
│ Retriever│  混合检索: Dense (向量相似度) + Sparse (BM25 关键词)
└────┬─────┘  + 重排序 (Cross-Encoder Reranker)
     │
     ▼
┌────────────────┐
│ Context Builder│  拼装检索片段 → System Prompt → LLM
└────────────────┘
```

### 3.2 数据模型

```python
@dataclass
class Document:
    """文档 — RAG 的最小输入单元"""
    doc_id: str
    source_type: str          # "pdf" | "markdown" | "pptx" | "web"
    source_path: str          # 原始路径
    title: str
    raw_text: str
    metadata: Dict[str, Any]  # {author, date, page_count, url, ...}
    chunks: List['Chunk'] = field(default_factory=list)

@dataclass
class Chunk:
    """文档分块 — 检索的基本单元"""
    chunk_id: str
    doc_id: str
    content: str
    chunk_index: int          # 在文档中的序号
    start_page: int
    end_page: int
    section_title: str        # 所属章节标题
    token_count: int
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RetrievalResult:
    """检索结果"""
    query: str
    chunks: List[Chunk]
    scores: List[float]          # 相关性分数
    retrieval_method: str        # "dense" | "hybrid"
    latency_ms: float
    total_candidates: int        # 候选池大小
```

### 3.3 Retriever 接口

```python
class BaseRetriever(ABC):
    """检索器抽象接口"""

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5,
                 filters: Optional[Dict] = None) -> RetrievalResult:
        """基础检索"""
        ...

    @abstractmethod
    def hybrid_retrieve(self, query: str, top_k: int = 5,
                        dense_weight: float = 0.7) -> RetrievalResult:
        """混合检索: Dense + Sparse"""
        ...

    @abstractmethod
    def rerank(self, query: str, candidates: List[Chunk],
               top_k: int = 5) -> List[Chunk]:
        """重排序 (Cross-Encoder)"""
        ...

class ChromaRetriever(BaseRetriever):
    """ChromaDB 实现 — 开发/小规模 (< 10K chunks)"""
    ...

class MilvusRetriever(BaseRetriever):
    """Milvus 实现 — 生产/大规模 (> 10K chunks), 支持分布式索引"""
    ...
```

### 3.4 Vector DB 选型

| 方案 | 适用场景 | 优势 | 劣势 |
|:---|:---|:---|:---|
| **ChromaDB** | 开发/原型/<10K chunks | 零配置, Python native, 嵌入式 | 不支持分布式, 大规模性能下降 |
| **FAISS** | 嵌入式计算(<1M vectors) | 极快, Meta 维护, GPU 加速 | 无持久化(需自建), 无元数据过滤 |
| **Milvus** | 生产/大规模/>100K chunks | 分布式, 混合检索, 元数据过滤, 云原生 | 部署复杂, 资源消耗大 |

**推荐: ChromaDB (开发) → Milvus (生产)**, 通过 `BaseRetriever` 接口无缝切换。

---

## 4. Agent Workflow 系统

### 4.1 6 Agent 设计 (为什么足够)

| Agent | 职责 | 为什么不需要更多 |
|:---|:---|:---|
| **ProfileAgent** | 用户意图理解 + 画像加载 | 替代了原来的多轮对话 Agent, 通过 UserStateMemory 一次加载 |
| **KnowledgeAgent** | RAG 检索 + 上下文构建 | 专注检索, 不负责生成 — 单职责 |
| **PlannerAgent** | 任务分解为子步骤 | 替代原来的管线式多 Agent, 一个 Planner 分解任务即可 |
| **ExecutionAgent** | 逐步骤执行 (LLM/Tool) | 统一执行入口, 具体能力通过 Tool Registry 扩展 |
| **EvaluationAgent** | 4 维质量评估 | 合并原来的 AgentEvaluator + ReviewGate, 单一评估入口 |
| **ReflectionAgent** | 失败反思 + 策略优化 | 保留 MetaReflector + ImprovementLoop, 作为独立反思 Agent |

**核心原则: Agent 是角色, 不是流水线节点。6 个 Agent 覆盖"理解→检索→规划→执行→评估→反思"全链路, 不需要更多。**

### 4.2 Agent 生命周期

```
┌──────────────────────────────────────────────────┐
│                 Agent Lifecycle                    │
│                                                    │
│  ① RECEIVE                                         │
│     │ 接收 Orchestrator 分发的任务 + 上下文          │
│     ▼                                              │
│  ② REASON                                          │
│     │ Agent 推理: 分析任务 + 加载 Memory + 查询 RAG │
│     ▼                                              │
│  ③ ACT                                             │
│     │ 执行: LLM 调用 / Tool 调用 / 子 Agent 委托    │
│     ▼                                              │
│  ④ OBSERVE                                         │
│     │ 收集结果 + 评估质量 (Trust Layer)              │
│     ▼                                              │
│  ⑤ OUTPUT                                          │
│     │ 输出结构化结果 + 置信度 + 推理链               │
│     ▼                                              │
│  ⑥ FEEDBACK                                        │
│       接收外部反馈 → 更新 Memory → 策略调整         │
│                                                    │
└──────────────────────────────────────────────────┘
```

### 4.3 Agent 基类设计

```python
class BaseAgent(ABC):
    """Agent 基类 — 统一生命周期"""

    agent_name: str
    memory: MemoryManager
    event_bus: AgentEventBus

    @abstractmethod
    def receive(self, task: AgentTask) -> None:
        """接收任务"""
        ...

    @abstractmethod
    def reason(self) -> ReasoningResult:
        """推理: 分析任务 + 加载上下文"""
        ...

    @abstractmethod
    def act(self, reasoning: ReasoningResult) -> ActionResult:
        """执行: LLM call / Tool call"""
        ...

    @abstractmethod
    def observe(self, result: ActionResult) -> Observation:
        """观察: 评估结果质量"""
        ...

    def run(self, task: AgentTask) -> AgentOutput:
        """完整生命周期执行"""
        self.receive(task)
        reasoning = self.reason()
        result = self.act(reasoning)
        observation = self.observe(result)
        output = AgentOutput(
            agent=self.agent_name,
            result=result,
            observation=observation,
            trace_id=self.event_bus.current_trace_id,
        )
        self.event_bus.emit(...)
        return output
```

---

## 5. Memory Architecture

### 5.1 三层记忆架构

```
┌─────────────────────────────────────────────────────────┐
│                   Veritas Memory Layer                    │
│                                                           │
│  ┌─────────────────────┐                                 │
│  │ Conversation Memory  │  ← Redis                       │
│  │ (会话级, TTL=24h)    │     Key: session:{id}:messages  │
│  │                      │     Value: List<Message>        │
│  │ • 最近 N 轮对话       │     TTL: 86400                 │
│  │ • 短期上下文窗口      │                                 │
│  └─────────┬───────────┘                                 │
│            │                                              │
│            ▼                                              │
│  ┌─────────────────────┐                                 │
│  │ User State Memory    │  ← PostgreSQL                  │
│  │ (用户级, 持久)        │     Table: user_profiles       │
│  │                      │     Table: user_preferences     │
│  │ • 用户画像            │     Table: interaction_history │
│  │ • 偏好设置            │                                 │
│  │ • 交互历史摘要        │                                 │
│  │ • 长期学习状态        │                                 │
│  └─────────┬───────────┘                                 │
│            │                                              │
│            ▼                                              │
│  ┌─────────────────────┐                                 │
│  │ Knowledge Memory     │  ← Vector DB (ChromaDB/Milvus) │
│  │ (资产级, 永久)        │     Collection: knowledge_chunks│
│  │                      │     Collection: agent_experience│
│  │ • 文档知识库          │                                 │
│  │ • Agent 经验教训      │                                 │
│  │ • FAQ / 最佳实践      │                                 │
│  └─────────────────────┘                                 │
│                                                           │
│                MemoryManager (统一入口)                    │
└─────────────────────────────────────────────────────────┘
```

### 5.2 存储方案对比

| 层级 | 存储 | 为什么 | 更新时机 |
|:---|:---|:---|:---|
| **Conversation Memory** | Redis | 低延迟, TTL 自动过期, 不需要持久化短期对话 | 每轮对话后追加, 超过 N 轮自动 FIFO 截断 |
| **User State Memory** | PostgreSQL | 结构化数据, 需要事务保证, 需要复杂查询 | 会话结束后异步批量更新; 画像变化时即时写入 |
| **Knowledge Memory** | Vector DB | 非结构化文本, 需要语义搜索, 高维向量索引 | 文档上传时离线 Embedding; Agent 经验按需追加 |

### 5.3 数据结构

```sql
-- User State Memory (PostgreSQL)
CREATE TABLE user_profiles (
    user_id        UUID PRIMARY KEY,
    display_name   TEXT,
    expertise_level TEXT,           -- novice | intermediate | expert
    preferences    JSONB,           -- {language, response_style, ...}
    domain_tags    TEXT[],          -- {python, devops, ml, ...}
    created_at     TIMESTAMPTZ,
    updated_at     TIMESTAMPTZ
);

CREATE TABLE interaction_history (
    id             BIGSERIAL PRIMARY KEY,
    user_id        UUID REFERENCES user_profiles(user_id),
    session_id     UUID,
    intent         TEXT,            -- 用户意图分类
    agent_chain    TEXT[],          -- 涉及的 Agent 列表
    outcome        TEXT,            -- success | partial | failure
    eval_scores    JSONB,           -- {retrieval: 0.9, generation: 0.85, ...}
    summary        TEXT,            -- LLM 生成的交互摘要
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_interaction_user ON interaction_history(user_id, created_at DESC);
```

---

## 6. Trust Layer — 评估与可信机制

### 6.1 Evaluation Pipeline

```
                     ┌─────────────────────┐
                     │   TRUST LAYER        │
                     │                     │
  Agent Output ──────►                     │
                     │  ┌───────────────┐  │
                     │  │① Retrieval    │  │  → 检索相关性 (NDCG, MRR, Precision@k)
                     │  │  Evaluation   │  │  → 是否检索到了正确的知识
                     │  └───────┬───────┘  │
                     │          │          │
                     │          ▼          │
                     │  ┌───────────────┐  │
                     │  │② Generation   │  │  → 生成质量 (Faithfulness, Relevance)
                     │  │  Evaluation   │  │  → 输出是否忠于检索到的上下文
                     │  └───────┬───────┘  │
                     │          │          │
                     │          ▼          │
                     │  ┌───────────────┐  │
                     │  │③ Hallucination│  │  → 幻觉检测 (LLM-as-Judge + NLI)
                     │  │  Detection    │  │  → 输出是否包含未在上下文中出现的事实
                     │  └───────┬───────┘  │
                     │          │          │
                     │          ▼          │
                     │  ┌───────────────┐  │
                     │  │④ Safety Check │  │  → 内容安全 (PII, Toxicity, Policy)
                     │  │               │  │  → 规则引擎 + 安全模型
                     │  └───────┬───────┘  │
                     │          │          │
                     │          ▼          │
                     │  ┌───────────────┐  │
                     │  │⑤ User Feedback│  │  → 用户评分 + 隐式信号 (复制/停留时间)
                     │  │               │  │  → EMA 更新 Agent 经验 success_rate
                     │  └───────┬───────┘  │
                     │          │          │
                     │          ▼          │
                     │  ┌───────────────┐  │
                     │  │⑥ Trace        │  │  → 完整决策链可解释
                     │  │  Explanation  │  │  → "为什么给出这个答案" 溯源
                     │  └───────────────┘  │
                     │                     │
                     └─────────┬───────────┘
                               │
                               ▼
                     Trust Report {
                       overall_score: 0.85,
                       retrieval: {ndcg: 0.92, precision@3: 1.0},
                       generation: {faithfulness: 0.88, relevance: 0.90},
                       hallucination: {detected: false, confidence: 0.95},
                       safety: {passed: true, flags: []},
                       trace: "决策链: RAG检索→3个chunk→LLM生成→事实校验"
                     }
```

### 6.2 Hallucination Detection 策略

```python
class HallucinationDetector:
    """
    幻觉检测 — 三层检测策略。

    L1: NLI (Natural Language Inference)
        → 将生成的断言与检索到的上下文做蕴含判断
        → 未蕴含 = 可能是幻觉

    L2: LLM-as-Judge
        → 让 LLM 逐句检查生成内容是否可在上下文中找到支撑
        → 标注 confidence level

    L3: Self-Consistency
        → 同一问题多次采样 (temperature>0)
        → 答案不一致的断言 = 高风险幻觉
    """
```

---

## 7. Observability 系统

### 7.1 Trace Schema

```python
@dataclass
class TraceSpan:
    """一次操作的追踪跨度"""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    span_type: str              # "agent" | "rag" | "llm" | "tool" | "eval"
    agent_name: Optional[str]
    operation: str              # "retrieve" | "generate" | "evaluate" | ...
    input_summary: str
    output_summary: str
    status: str                 # "success" | "error" | "warning"
    duration_ms: float
    token_usage: TokenUsage     # {prompt_tokens, completion_tokens, total_tokens}
    metadata: Dict[str, Any]    # {prompt_text, retrieval_scores, decision_reasoning}
    start_time: str
    end_time: str

@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str

@dataclass
class Trace:
    """完整请求的追踪链"""
    trace_id: str
    session_id: str
    user_id: str
    spans: List[TraceSpan]
    total_duration_ms: float
    total_tokens: int
    estimated_cost_usd: float
    created_at: str
```

### 7.2 可观测维度

| 维度 | 记录内容 | 存储 |
|:---|:---|:---|
| **Agent 调用链** | TraceSpan 树: Orchestrator → Agent → LLM → Tool | JSONL / PostgreSQL |
| **Prompt 日志** | 每个 LLM call 的完整 prompt (system + user) | PostgreSQL (压缩) |
| **Retrieval 结果** | 检索到的 chunks, scores, latency | 内嵌在 TraceSpan.metadata |
| **Token 消耗** | 每次调用的 token 计数 + 模型 | PostgreSQL timeseries |
| **Decision 过程** | Agent 推理链 (ReasoningResult), 为什么做这个决策 | JSONB in TraceSpan.metadata |
| **Latency 分布** | 每层的延迟 (RAG检索 / LLM推理 / Agent总耗时) | PostgreSQL |

---

## 8. Research Agent 扩展

### 8.1 定位

Research Agent 是**高级插件**, 不是核心 Agent。

**与 RAG 的区别:**

| 维度 | RAG (KnowledgeAgent) | Research Agent |
|:---|:---|:---|
| **知识来源** | 内部可信知识库 (已上传文档) | 外部动态知识 (Web / API) |
| **检索方式** | 向量相似度 + BM25 | 搜索引擎 / API 调用 / 网页抓取 |
| **时效性** | 知识库上传时的快照 | 实时获取 |
| **可信度** | 高 (来源可控) | 中 (需要额外验证) |
| **使用场景** | "根据公司文档回答" | "调研最新技术趋势" |

### 8.2 架构

```
User Question
    │
    ▼
Research Planner
    │ 将问题分解为子查询
    │ "调研2024年Vector DB趋势" →
    │   子查询1: "2024 Vector Database benchmark"
    │   子查询2: "Milvus vs Pinecone 2024 comparison"
    │   子查询3: "Vector DB market report 2024"
    │
    ▼
Search Engine (Tavily / SerpAPI / Bing)
    │ 每个子查询 → Top 5 URLs
    ▼
Content Fetcher
    │ URL → HTML → Text (trafilatura / readability)
    ▼
RAG Pipeline (复用)
    │ 外部内容 → Chunk → Embed → 存入临时 Vector DB
    ▼
Analyzer (LLM)
    │ 整合检索结果 → 分析 → 交叉验证 → 生成研究报告
    ▼
Research Report
    │ 带引用的结构化报告
    ▼
 存入 Knowledge Memory (可选)
```

---

## 9. 工程化部署

### 9.1 技术栈

| 组件 | 选型 | 理由 |
|:---|:---|:---|
| **API 框架** | FastAPI | 高性能 async, 自动 OpenAPI doc, WebSocket 支持 |
| **数据库** | PostgreSQL 16 | 成熟的关系型数据库, JSONB 支持 |
| **缓存** | Redis 7 | 会话存储, TTL 管理, 低延迟 |
| **向量库** | ChromaDB → Milvus | 开发/生产两阶段 |
| **LLM 网关** | LiteLLM (Proxy) | 统一多模型接入, 成本追踪, 速率限制 |
| **容器化** | Docker + Compose | 一键部署, 环境一致 |
| **监控** | Prometheus + Grafana | 生产级指标监控 |
| **Dashboard** | Streamlit (保留) | Debug/演示用, 非生产核心 |

### 9.2 Docker Compose

```yaml
services:
  api:
    build: .
    ports: ["8000:8000"]
    depends_on: [postgres, redis, chroma]
    env_file: .env

  postgres:
    image: postgres:16-alpine
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine

  chroma:
    image: chromadb/chroma:latest

  litellm:
    image: ghcr.io/berriai/litellm:main
    env_file: .env.litellm

  streamlit:
    build: .
    command: streamlit run web/app.py
    ports: ["8501:8501"]

volumes:
  pgdata:
```

---

## 10. 代码目录设计

```
veritas-core/
├── src/
│   ├── api/                    # FastAPI 层
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app 入口
│   │   ├── routes/
│   │   │   ├── chat.py         # /chat (WebSocket + REST)
│   │   │   ├── rag.py          # /rag/query, /rag/upload
│   │   │   ├── agent.py        # /agent/run (异步任务)
│   │   │   └── eval.py         # /eval/report
│   │   └── middleware.py       # Auth, Logging, Rate Limit
│   │
│   ├── orchestrator/           # Agent 工作流调度
│   │   ├── __init__.py
│   │   ├── engine.py           # Workflow Engine (A3 EventBus 保留)
│   │   └── task.py             # AgentTask 定义
│   │
│   ├── agents/                 # 6 个核心 Agent
│   │   ├── __init__.py
│   │   ├── base.py             # BaseAgent (生命周期)
│   │   ├── profile_agent.py    # 用户理解 (从 A3 迁移)
│   │   ├── knowledge_agent.py  # RAG 检索封装
│   │   ├── planner_agent.py    # 任务规划 (从 A3 升级)
│   │   ├── execution_agent.py  # 任务执行 (Tool Registry)
│   │   ├── evaluation_agent.py # 质量评估
│   │   └── reflection_agent.py # 策略优化 (从 A3 MetaReflector 迁移)
│   │
│   ├── rag/                    # RAG Engine
│   │   ├── __init__.py
│   │   ├── parser.py           # PDF/MD/PPT/Web 解析
│   │   ├── chunker.py          # 语义分块
│   │   ├── embedder.py         # Embedding 生成
│   │   ├── retriever.py        # BaseRetriever + Chroma/Milvus 实现
│   │   ├── context_builder.py  # 上下文拼装
│   │   └── models.py           # Document, Chunk, RetrievalResult
│   │
│   ├── memory/                 # 三层记忆
│   │   ├── __init__.py
│   │   ├── manager.py          # MemoryManager (统一入口, A3 升级)
│   │   ├── conversation.py     # ConversationMemory (Redis)
│   │   ├── user_state.py       # UserStateMemory (PostgreSQL)
│   │   ├── knowledge_memory.py # KnowledgeMemory (Vector DB)
│   │   └── models.py           # 数据模型
│   │
│   ├── evaluation/             # Trust Layer
│   │   ├── __init__.py
│   │   ├── retrieval_eval.py   # 检索评估 (NDCG, MRR)
│   │   ├── generation_eval.py  # 生成评估 (Faithfulness, Relevance)
│   │   ├── hallucination.py    # 幻觉检测 (NLI + LLM-Judge)
│   │   ├── safety.py           # 安全审查 (PII, Toxicity)
│   │   ├── feedback.py         # 用户反馈收集 + EMA 更新
│   │   └── report.py           # Trust Report 生成
│   │
│   ├── observability/          # 可观测系统
│   │   ├── __init__.py
│   │   ├── trace_collector.py  # TraceCollector (A3 保留+升级)
│   │   ├── prompt_logger.py    # Prompt 日志
│   │   ├── token_tracker.py    # Token 消耗追踪
│   │   └── models.py           # TraceSpan, Trace, TokenUsage
│   │
│   ├── providers/              # LLM Provider (A3 保留+扩展)
│   │   ├── __init__.py
│   │   ├── base.py             # BaseLLMProvider
│   │   ├── openai.py           # OpenAI / Azure
│   │   ├── anthropic.py        # Anthropic Claude
│   │   ├── spark.py            # Xunfei Spark (A3 保留)
│   │   └── factory.py          # ProviderFactory (A3 保留)
│   │
│   ├── plugins/                # 插件系统
│   │   ├── __init__.py
│   │   ├── registry.py         # PluginRegistry (通用注册表)
│   │   ├── content.py          # ContentPlugin (从 A3 ResourceGen 迁移)
│   │   └── research.py         # ResearchAgent 插件
│   │
│   └── core/                   # 核心基础设施 (A3 保留)
│       ├── __init__.py
│       ├── event_bus.py        # AgentEventBus (保留)
│       └── contracts.py        # 共享数据契约 (保留)
│
├── tests/                      # 测试
│   ├── test_api/
│   ├── test_agents/
│   ├── test_rag/
│   ├── test_memory/
│   └── test_evaluation/
│
├── docs/                       # 文档
│   ├── architecture.md
│   ├── rag-design.md
│   ├── memory-design.md
│   ├── agent-design.md
│   ├── deployment.md
│   └── adr/                    # Architecture Decision Records
│       ├── ADR-001-why-rag.md
│       ├── ADR-002-why-eventbus.md
│       ├── ADR-003-why-multi-agent.md
│       └── ADR-004-why-chromadb-then-milvus.md
│
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
│
├── web/                        # Streamlit Dashboard (A3 保留)
│   └── app.py
│
├── pyproject.toml
├── README.md
└── Makefile
```

---

## 11. 迁移方案

### 11.1 文件级映射

| A3 源文件 | Veritas_Core 目标 | 操作 |
|:---|:---|:---|
| `src/core/event_bus.py` | `src/core/event_bus.py` | ✅ **直接复制** |
| `src/core/contracts.py` | `src/core/contracts.py` | ✅ **直接复制** |
| `src/core/agent_trace.py` | `src/observability/trace_collector.py` | 🔄 **迁移+升级** |
| `src/llm/provider.py` | `src/providers/base.py` | 🔄 **迁移+扩展** |
| `src/llm/xunfei_provider.py` | `src/providers/spark.py` | ✅ **直接复制** |
| `src/llm/mock_provider.py` | `src/providers/mock.py` | ✅ **直接复制** |
| `src/llm/__init__.py` + `provider_factory.py` | `src/providers/factory.py` | 🔄 **合并+扩展** |
| `src/agents/profile_agent.py` | `src/agents/profile_agent.py` | 🔄 **通用化** (去教育专用) |
| `src/agents/planner_agent.py` | `src/agents/planner_agent.py` | 🔄 **重构** (规则表→任务分解) |
| `src/memory/student_memory.py` | `src/memory/user_state.py` | 🔄 **抽象升级** |
| `src/memory/experience_memory.py` | `src/memory/knowledge_memory.py` | 🔄 **抽象升级** |
| `src/memory/memory_manager.py` | `src/memory/manager.py` | 🔄 **升级为三层** |
| `src/evaluation/agent_evaluator.py` | `src/evaluation/generation_eval.py` | 🔄 **迁移+拆分** |
| `src/evaluation/judge.py` | `src/evaluation/hallucination.py` | 🔄 **迁移+升级** |
| `src/core/meta_reflector.py` | `src/agents/reflection_agent.py` | 🔄 **迁移** |
| `src/core/improvement_loop.py` | 融入 `src/evaluation/feedback.py` | 🔄 **合并** |
| `src/core/review_gate.py` | `src/evaluation/safety.py` | 🔄 **迁移** |
| `src/agents/resource_generation_agent.py` | `src/plugins/content.py` | ⬇️ **降级为插件** |
| `src/agents/conversation_profile_agent.py` | ❌ | ❌ **移除** |
| `src/agents/resource_recommendation_agent.py` | ❌ | ❌ **移除** |
| `src/core/content_agent.py` | `src/plugins/content.py` | ⬇️ **降级为插件** |
| — | `src/rag/*` (全部) | 🆕 **全新** |
| — | `src/api/*` (全部) | 🆕 **全新** |
| — | `src/orchestrator/*` | 🆕 **全新** |
| — | `docker/*` | 🆕 **全新** |

### 11.2 迁移分阶段

| 阶段 | 内容 | 时间 |
|:---|:---|:---|
| **Phase 1: 核心迁移** | 复制 EventBus + TraceCollector + LLMProvider + Contracts | 2d |
| **Phase 2: RAG Engine** | 新建 RAG 全线 (Parser→Chunker→Embedder→Retriever→Context) | 5d |
| **Phase 3: Memory 升级** | 三层记忆 (Redis + PostgreSQL + Vector DB) | 3d |
| **Phase 4: Agent 重构** | 6 Agent + Orchestrator + BaseAgent 生命周期 | 4d |
| **Phase 5: Trust Layer** | 评估管线 (Retrieval/Generation/Hallucination/Safety) | 4d |
| **Phase 6: API + Deploy** | FastAPI + Docker Compose + README | 3d |
| **Phase 7: Docs** | architecture.md + ADR + 各模块设计文档 | 2d |

---

## 12. ADR — 架构决策记录

### ADR-001: Why RAG?

**状态:** Accepted  
**日期:** 2026-07-13

**背景:** Veritas_Core 的核心价值是"知识可靠性"。纯 LLM 存在幻觉、知识截止日期、无法溯源三个根本问题。

**决策:** 以 RAG 作为知识检索的核心范式，所有对外输出必须经过 RAG 检索→上下文增强→LLM 生成→事实校验全链路。

**替代方案:**
- Fine-tuning: 更新成本高, 无法溯源, 不适合动态知识 → 拒绝
- Pure LLM: 幻觉不可控 → 拒绝

**后果:** 需要维护 Vector DB 和 Embedding pipeline, 增加了系统复杂度, 但换来了可溯源和可验证的知识输出。

---

### ADR-002: Why EventBus?

**状态:** Accepted  
**日期:** 2026-07-13

**背景:** 需要一种解耦的 Agent 间通信机制, 同时支持全链路追踪。

**决策:** 保留 A3 的 Singleton AgentEventBus 模式。

**替代方案:**
- Direct function call: 紧耦合, 难以追踪 → 拒绝
- Message Queue (RabbitMQ/Kafka): 过度工程化, 当前规模不需要 → 拒绝
- Callback chain: 嵌套地狱 → 拒绝

**后果:** Singleton 全局状态需要测试清理, 但换来了统一的可观测入口和 Agent 解耦。

---

### ADR-003: Why Multi-Agent (6)?

**状态:** Accepted  
**日期:** 2026-07-13

**背景:** 为什么需要多 Agent 而不是单个 LLM?

**决策:** 6 个 Agent 各司其职 (Profile/Knowledge/Plan/Execute/Evaluate/Reflect), 不追求数量追求职责明确。

**理由:**
1. 职责分离 = 可独立评估和替换
2. 每个 Agent 的 prompt 更短更精准
3. EvaluationAgent 可独立评估其他 Agent 输出
4. ReflectionAgent 的改进可精确到具体 Agent

**替代方案:**
- Single LLM with system prompt: 无评估, 无反思, 无审计 → 拒绝
- 12+ Agents (A3): 过度拆分, 维护成本高 → 降为 6

---

### ADR-004: Why ChromaDB → Milvus?

**状态:** Accepted  
**日期:** 2026-07-13

**背景:** 需要选择 Vector DB。

**决策:** 开发阶段 ChromaDB (零配置), 生产阶段 Milvus (分布式)。

**理由:**
- ChromaDB: Python native, 嵌入运行, 开发体验极佳
- Milvus: 支持 10B+ vectors, 混合检索, 云原生
- 通过 `BaseRetriever` 接口切换, 业务代码不受影响

---

## 13. 升级路线图

```
Phase 1 ──── Phase 2 ──── Phase 3 ──── Phase 4 ──── Phase 5 ──── Phase 6
(Week 1)     (Week 2)     (Week 2-3)   (Week 3-4)   (Week 4)     (Week 4-5)

核心迁移      RAG Engine   Memory升级   Agent重构    Trust Layer  API+Deploy
──────────────────────────────────────────────────────────────────────────→

Phase 1: EventBus + Trace + LLMProvider + Contracts 复制    [2d] P0
Phase 2: Parser/Chunker/Embedder/Retriever/ContextBuilder  [5d] P0
Phase 3: Redis + PostgreSQL + Vector DB 三层 Memory        [3d] P1
Phase 4: 6 Agent + Orchestrator + BaseAgent                [4d] P1
Phase 5: Retrieval/Generation/Hallucination/Safety Eval    [4d] P2
Phase 6: FastAPI + Docker Compose + README + Docs          [3d] P2
```

---

## 14. 风险分析

| 风险 | 概率 | 影响 | 缓解措施 |
|:---|:---|:---|:---|
| **迁移破坏现有 A3 功能** | 低 | 高 | 新项目独立仓库, A3 保留为 archive 分支 |
| **Vector DB 性能瓶颈** | 中 | 中 | BaseRetriever 接口支持切换, ChromaDB→Milvus 迁移路径明确 |
| **6 Agent 覆盖不足** | 低 | 中 | Agent 职责定义清晰, 不足可扩展 Tool Registry |
| **多模型成本失控** | 中 | 中 | LiteLLM Proxy 统一管控 + TokenTracker 实时监控 |
| **RAG 检索质量问题** | 中 | 高 | Trust Layer 的 Retrieval Eval 持续监控, Chunker 参数可调 |

---

## 15. GitHub 展示方案

### README 结构

```markdown
# Veritas_Core — Trustworthy Agentic AI Platform

> A production-grade platform for building reliable, explainable,
  and self-improving AI agents with built-in RAG, Memory, and Trust layers.

## Architecture
[ASCII diagram]

## Core Capabilities
- **RAG Knowledge Engine** — PDF/MD/PPT/Web → Chunk → Vector → Retrieve
- **Agent Workflow** — 6 specialized agents with lifecycle management
- **3-Tier Memory** — Conversation (Redis) / User State (PostgreSQL) / Knowledge (Vector DB)
- **Trust Layer** — Retrieval eval + Generation eval + Hallucination detection + Safety check
- **Full Observability** — Trace spans, prompt logging, token tracking, decision explanations

## Tech Stack
Python 3.11+ | FastAPI | PostgreSQL | Redis | ChromaDB | Streamlit | Docker

## Quick Start
```bash
git clone https://github.com/user/veritas-core
cd veritas-core
docker-compose up -d
# API: http://localhost:8000/docs
# Dashboard: http://localhost:8501
```

## Project Structure
[directory tree]

## Roadmap
- [x] Core Agent Workflow
- [x] RAG Engine
- [ ] Multi-turn conversation memory
- [ ] Research Agent plugin
- [ ] Production Milvus integration
- [ ] Multi-tenant support

## License
MIT
```

---

## 16. AI Engineer 实习价值分析

### Veritas_Core 体现的工程能力

| 能力域 | 在项目中的体现 | 面试价值 |
|:---|:---|:---|
| **LLM Application Engineering** | RAG 全链路, Agent 生命周期, Prompt 管理 | 直接对应 AI Engineer 核心 JD |
| **RAG Engineering** | Parser/Chunker/Embedder/Retriever/Reranker 自研 | 超过 90% 的"调包侠" |
| **Agent Architecture** | Orchestrator + 6 Agent + EventBus + Memory | 展示对 Multi-Agent 范式的深度理解 |
| **Backend Engineering** | FastAPI, PostgreSQL, Redis, Docker, async/await | 全栈后端能力 |
| **AI System Design** | Trust Layer, Observability, ADR | 系统思维, 非功能需求优先 |
| **Production Readiness** | Docker Compose, LiteLLM Proxy, Prometheus | 从 Demo 到生产的能力 |

### 简历亮点

> **Veritas_Core — 可信 Agentic AI 平台 (开源项目)**
>
> 独立设计并实现了一个生产级的 LLM 应用平台，包含自研 RAG Engine（支持 PDF/MD/PPT 解析、语义分块、混合检索、Cross-Encoder 重排序）、6 Agent 工作流系统（Profile/Knowledge/Plan/Execute/Evaluate/Reflect）、三层记忆架构（Redis/PostgreSQL/Vector DB）、以及完整的 Trust Layer（检索评估/生成评估/幻觉检测/安全审查/用户反馈闭环）。
>
> **技术栈:** Python, FastAPI, PostgreSQL, Redis, ChromaDB, Docker, Streamlit  
> **代码量:** ~8,000 lines (core) · 70+ tests · 20+ docs pages

---

*Veritas_Core — Trustworthy Agentic AI Platform*  
*Architecture Design Document · 2026-07-13*
