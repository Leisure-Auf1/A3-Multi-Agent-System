# Veritas_Core — 工程化设计 & Observability

---

## 一、代码目录规划

```
veritas_core/
│
├── src/
│   ├── api/                        # FastAPI 层
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app 入口, middleware, CORS
│   │   ├── routes/
│   │   │   ├── session.py          # POST /api/session/start
│   │   │   ├── profile.py          # POST /api/profile/extract, GET /api/student/{id}
│   │   │   ├── learn.py            # POST /api/learn/plan, /generate, /evaluate, /feedback
│   │   │   ├── knowledge.py        # POST /api/knowledge/upload (课程资料上传)
│   │   │   └── dashboard.py        # GET /api/dashboard (系统可观测)
│   │   ├── schemas.py              # Pydantic models (请求/响应验证)
│   │   └── dependencies.py         # FastAPI Depends (session, memory, llm)
│   │
│   ├── orchestrator/               # 学习管线编排
│   │   ├── __init__.py
│   │   ├── engine.py               # LearningOrchestrator — 管线DAG引擎
│   │   ├── pipeline.py             # Pipeline: Profile→Knowledge→Plan→Generate→Eval→Reflect
│   │   └── state.py                # WorkflowState (session级状态管理)
│   │
│   ├── agents/                     # 6个核心Agent
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseAgent (生命周期 + EventBus记录)
│   │   ├── profile_agent.py        # ProfileAgent — 学生画像构建 (A3保留+升级)
│   │   ├── knowledge_agent.py      # KnowledgeAgent — RAG知识检索
│   │   ├── planner_agent.py        # PlannerAgent — 学习路径规划 (A3升级)
│   │   ├── resource_agent.py       # ResourceAgent — 资源生成 (核心Agent, 重建)
│   │   ├── evaluation_agent.py     # EvaluationAgent — 学习评估 (A3升级)
│   │   └── reflection_agent.py     # ReflectionAgent — 闭环优化 (A3 MetaReflector升级)
│   │
│   ├── rag/                        # RAG Engine (新模块)
│   │   ├── __init__.py
│   │   ├── parser.py               # DocumentParser: PDF/MD/PPT/源码解析
│   │   ├── chunker.py              # SemanticChunker: 语义分块 + metadata提取
│   │   ├── embedder.py             # EmbeddingProvider + EmbeddingFactory
│   │   ├── vector_store.py         # ChromaDB封装 (collection管理)
│   │   ├── retriever.py            # BaseRetriever + ChromaRetriever
│   │   ├── context_builder.py      # ContextBuilder: 检索结果 → LLM Prompt上下文
│   │   └── models.py               # Document, Chunk, RetrievalResult, KnowledgeContext
│   │
│   ├── memory/                     # 三层记忆 (A3升级)
│   │   ├── __init__.py
│   │   ├── manager.py              # MemoryManager (统一入口)
│   │   ├── conversation.py         # ConversationMemory (Redis)
│   │   ├── profile_store.py        # ProfileMemoryStore (PostgreSQL)
│   │   ├── history_store.py        # HistoryMemoryStore (PostgreSQL)
│   │   ├── experience_store.py     # ExperienceMemoryStore (ChromaDB)
│   │   └── models.py               # StudentProfile, MasteryRecord, ExperienceRecord, ...
│   │
│   ├── trust/                      # Trust Layer (新模块, 集成A3 ReviewGate)
│   │   ├── __init__.py
│   │   ├── pipeline.py             # TrustPipeline: 4-Gate编排
│   │   ├── source_check.py         # Gate 1: 知识来源检查 + AST验证
│   │   ├── grounding_check.py      # Gate 2: RAG引用验证 (NLI)
│   │   ├── hallucination.py        # Gate 3: 幻觉检测 (LLM-Judge + Self-Consistency)
│   │   ├── safety_filter.py        # Gate 4: 安全教育过滤
│   │   └── report.py               # TrustReport 生成
│   │
│   ├── observability/              # 可观测系统 (A3 TraceCollector升级)
│   │   ├── __init__.py
│   │   ├── trace_collector.py      # LearningTraceCollector (A3升级)
│   │   ├── prompt_logger.py        # Prompt日志 (LLM调用记录)
│   │   ├── token_tracker.py        # Token消耗追踪
│   │   ├── learning_analytics.py   # 学习分析 (画像演化/掌握度变化)
│   │   └── models.py               # TraceSpan, Trace, TokenUsage, ...
│   │
│   ├── providers/                  # LLM Provider (A3保留+扩展)
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseLLMProvider (A3保留)
│   │   ├── deepseek.py             # DeepSeek适配 (同 repository 现有模式)
│   │   ├── spark.py                # Xunfei Spark (A3保留)
│   │   ├── mock.py                 # MockLLMProvider (A3保留)
│   │   └── factory.py              # ProviderFactory (A3保留)
│   │
│   └── core/                       # 核心基础设施 (A3保留)
│       ├── __init__.py
│       ├── event_bus.py            # AgentEventBus (A3保留)
│       ├── contracts.py            # 共享数据契约 (A3保留)
│       └── config.py               # 全局配置管理
│
├── tests/                          # 测试
│   ├── conftest.py                 # 共享fixtures
│   ├── test_agents/
│   │   ├── test_profile_agent.py
│   │   ├── test_knowledge_agent.py
│   │   ├── test_planner_agent.py
│   │   ├── test_resource_agent.py
│   │   ├── test_evaluation_agent.py
│   │   └── test_reflection_agent.py
│   ├── test_rag/
│   │   ├── test_parser.py
│   │   ├── test_chunker.py
│   │   ├── test_retriever.py
│   │   └── test_context_builder.py
│   ├── test_memory/
│   │   ├── test_conversation.py
│   │   ├── test_profile_store.py
│   │   └── test_history_store.py
│   ├── test_trust/
│   │   ├── test_source_check.py
│   │   ├── test_hallucination.py
│   │   └── test_pipeline.py
│   ├── test_api/
│   │   └── test_routes.py
│   └── test_integration/
│       └── test_learning_loop.py   # 端到端闭环测试
│
├── knowledge_base/                 # 课程知识库 (A3保留)
│   └── artificial_intelligence_multi_agent_course/
│       ├── course_intro.md
│       ├── chapters/               # 6章markdown章节
│       ├── resources.json
│       └── exercises.json
│
├── storage/                        # 运行时数据
│   ├── chroma/                     # ChromaDB持久化
│   └── traces/                     # Trace JSON (A3保留)
│
├── web/                            # Streamlit Dashboard (A3保留)
│   └── app.py
│
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
│
├── docs/
│   ├── architecture.md
│   ├── agent-design.md
│   ├── rag-design.md
│   ├── memory-design.md
│   ├── learning-loop.md
│   ├── deployment.md
│   └── adr/
│       ├── ADR-001-why-multi-agent.md
│       ├── ADR-002-why-rag.md
│       ├── ADR-003-why-eventbus.md
│       └── ADR-004-why-memory-architecture.md
│
├── pyproject.toml
├── README.md
└── Makefile
```

---

## 二、各模块职责详表

| 模块 | 目录 | 职责 | 从A3迁移 |
|:-----|:-----|:-----|:---------|
| **API Layer** | `src/api/` | REST接口、请求验证、会话管理、认证 | 全新 |
| **Orchestrator** | `src/orchestrator/` | 管线DAG调度、状态管理、Agent编排 | 重构A3 AgentRouter |
| **ProfileAgent** | `src/agents/profile_agent.py` | 学生画像构建 (规则+LLM双模式) | A3 profile_agent.py → 升级 |
| **KnowledgeAgent** | `src/agents/knowledge_agent.py` | RAG检索封装、知识诊断 | 全新 |
| **PlannerAgent** | `src/agents/planner_agent.py` | 学习路径规划 (知识缺口驱动) | A3 planner_agent.py → 升级 |
| **ResourceAgent** | `src/agents/resource_agent.py` | 5种学习资源生成 (RAG增强LLM) | A3 resource_generation_agent.py → 重建 |
| **EvaluationAgent** | `src/agents/evaluation_agent.py` | 学习效果多维度评估 | A3 agent_evaluator.py → 升级 |
| **ReflectionAgent** | `src/agents/reflection_agent.py` | 闭环优化：画像更新+路径调整 | A3 meta_reflector + improvement_loop → 融合 |
| **RAG Engine** | `src/rag/` | 课程资料→向量索引→语义检索 | 全新 (基于A3 course_kb_loader) |
| **Memory Layer** | `src/memory/` | 三层记忆管理 | A3 memory → PostgreSQL + Redis + ChromaDB |
| **Trust Layer** | `src/trust/` | 4-Gate内容可信保障 | A3 review_gate.py → 扩展为Trust Layer |
| **Observability** | `src/observability/` | 学习过程追踪+分析 | A3 agent_trace.py → 升级 |
| **Providers** | `src/providers/` | LLM多模型抽象 | A3 llm/ + provider_factory → 保留+扩展 |
| **Core** | `src/core/` | EventBus + 全局配置 | A3 event_bus.py → 直接保留 |

---

## 三、Docker Compose 部署

```yaml
# docker/docker-compose.yml
services:
  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://veritas:veritas@postgres:5432/veritas
      - REDIS_URL=redis://redis:6379
      - CHROMA_PERSIST_DIR=/data/chroma
      - LLM_PROVIDER=deepseek
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - chroma_data:/data/chroma
      - ./knowledge_base:/app/knowledge_base:ro

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: veritas
      POSTGRES_PASSWORD: veritas
      POSTGRES_DB: veritas
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U veritas"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  streamlit:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    command: streamlit run web/app.py --server.port 8501
    ports:
      - "8501:8501"
    environment:
      - API_BASE_URL=http://api:8000
    depends_on:
      - api

volumes:
  pgdata:
  redis_data:
  chroma_data:
```

---

## 四、Observability — Learning Process Trace

### 4.1 从 A3 TraceCollector 升级

A3 已有的 `TraceCollector` (记录 Agent 事件 → JSON 持久化) 升级为 **Learning Process Trace**：

| 维度 | A3 TraceCollector | Veritas_Core TraceCollector |
|:-----|:------------------|:---------------------------|
| **记录范围** | Agent执行事件 | Agent执行 + RAG检索 + LLM调用 + 学习行为 |
| **Schema** | AgentEvent | TraceSpan (树形结构, 支持父子) |
| **存储** | JSON文件 | PostgreSQL (结构化) + JSONL (归档) |
| **查询** | 文件读取 | SQL查询 (按student/agent/time) |
| **分析** | 无 | 学习分析 (画像演化/掌握度变化/资源使用) |

### 4.2 Trace Schema

```python
@dataclass
class TraceSpan:
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    span_type: str              # "agent" | "rag" | "llm" | "resource" | "student_action"
    agent_name: Optional[str]   # 所属Agent
    operation: str              # "extract_profile" | "rag_retrieve" | "llm_generate" | ...
    input_summary: str
    output_summary: str
    status: str                 # "success" | "error" | "retry"
    duration_ms: float
    token_usage: Optional[TokenUsage]
    metadata: dict              # {prompt_text, retrieval_scores, decisions, ...}
    start_time: str
    end_time: str

@dataclass
class Trace:
    trace_id: str
    session_id: str
    student_id: str
    spans: List[TraceSpan]      # 树形结构
    total_duration_ms: float
    total_tokens: int
    estimated_cost_usd: float
    created_at: str
```

### 4.3 可观测维度

| 维度 | 记录什么 | 存储 | 用途 |
|:-----|:---------|:-----|:-----|
| **Agent调用链** | 完整TraceSpan树: Orchestrator→Agent→RAG→LLM | PostgreSQL | 调试、性能分析 |
| **RAG检索** | 检索query, top-k结果, relevance scores, latency | 内嵌在TraceSpan.metadata | 检索质量分析 |
| **LLM调用** | 完整prompt (system+user), response, token数, 模型 | PostgreSQL (prompt_log表) | 成本追踪、Prompt优化 |
| **资源生成** | 生成的资源类型, Trust Report, 重试次数 | TraceSpan.metadata | 生成质量分析 |
| **学习行为** | 学生操作: 打开/关闭/作答/评分/停留时间 | learning_records表 | 学习投入度分析 |
| **决策链路** | Agent推理过程, 为什么做某个决策 | TraceSpan.metadata.decision_reasoning | 可解释性 |
| **画像演化** | 画像每次变化的时间线 (profile_evolution表) | 结构化SQL查询 | 学习效果追踪 |

### 4.4 Learning Analytics

```python
class LearningAnalytics:
    """学习分析 — 基于Trace数据"""

    def get_profile_evolution(self, student_id: str) -> List[ProfileSnapshot]:
        """画像演化时间线: 展示学生画像如何随时间变化"""
        return self.db.query(
            "SELECT * FROM profile_evolution WHERE student_id=%s ORDER BY created_at",
            (student_id,)
        )

    def get_mastery_timeline(self, student_id: str) -> Dict[str, List[float]]:
        """掌握度变化曲线: 每个概念的EMA变化"""
        ...

    def get_learning_velocity(self, student_id: str) -> float:
        """学习速度: 掌握度提升/时间投入"""
        ...

    def get_engagement_metrics(self, student_id: str) -> Dict:
        """投入度指标: 完成率/跳过率/平均停留时间/资源类型偏好"""
        ...

    def get_resource_effectiveness(self, resource_type: str) -> float:
        """资源效果: 各资源类型对应的掌握度提升量"""
        ...
```

---

## 五、技术栈总览

| 组件 | 选型 | 从A3迁移 |
|:-----|:-----|:---------|
| **API框架** | FastAPI | 全新 |
| **数据库** | PostgreSQL 16 | 全新 (A3用JSON文件) |
| **缓存** | Redis 7 | 全新 |
| **向量库** | ChromaDB | 全新 |
| **LLM接入** | LLMProvider Interface + Factory | A3保留+扩展 |
| **Agent通信** | AgentEventBus (Singleton) | A3保留 |
| **内容安全** | ReviewGate → Trust Layer | A3升级 |
| **Dashboard** | Streamlit | A3保留 |
| **容器化** | Docker + Compose | 全新 |
| **测试** | pytest | A3保留 (241→目标300+) |
| **代码质量** | ruff + mypy | 新增 |
