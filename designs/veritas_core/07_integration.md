# Veritas_Core — ADR · 迁移路线 · 开发优先级 · 风险分析 · GitHub方案

---

## 一、架构决策记录 (ADR)

### ADR-001: Why Multi-Agent? (6 Agents, not 12)

**状态:** Accepted  
**日期:** 2026-07-13

**背景:** A3 系统有 12 个 Agent。在升级为 Veritas_Core 时，是否需要维持或增加 Agent 数量？

**决策:** 缩减为 6 个核心 Agent，映射到学习闭环的 6 个关键环节：

```
ProfileAgent → KnowledgeAgent → PlannerAgent
                                     │
ResourceAgent ← ─────────────────────┘
     │
EvaluationAgent → ReflectionAgent → (循环)
```

**理由:**
1. **教育场景的环节是确定的:** 理解学生 → 诊断知识 → 规划路径 → 生成资源 → 评估效果 → 反思调整。6 个环节对应 6 个 Agent，多一个冗余，少一个断链
2. **Agent 是有状态的自主决策单元，不是函数:** ResourceRecommendation 不是独立 Agent — 它是 PlannerAgent 规划的一部分和 ResourceAgent 个性化的一部分
3. **Agent 间不需要"争论":** 学习路径是教学逻辑决定的，不是 Agent "协商"出来的。Council 模式对教育没有实际价值
4. **可独立评估:** 6 个 Agent 每个有明确的输入输出合约，可独立测试和替换
5. **评审视角:** 评审看的是 **为什么拆分** 和 **Agent 间如何协作**，不是 Agent 数量

**替代方案:**
- 12+ Agent (A3方案): 过度拆分，维护成本高，部分 Agent 对教育场景无价值 (Council/KG/Multimodal)
- Single LLM: 无评估、无反思、无审计 → 拒绝

---

### ADR-002: Why RAG?

**状态:** Accepted  
**日期:** 2026-07-13

**背景:** 学习内容的准确性是教育系统的生命线。纯 LLM 生成存在三个根本问题：幻觉 (编造不存在的事实)、知识截止日期、无法溯源。

**决策:** 以 RAG (Retrieval-Augmented Generation) 作为 ResourceAgent 的知识增强核心。所有生成的学习资源必须经过 RAG 检索 → 上下文增强 → LLM 生成 → Trust Layer 验证的全链路。

**RAG 的定位:** Course Knowledge Enhancement Module — 不是独立的知识问答平台，而是为 ResourceAgent 提供可靠的知识上下文。

**理由:**
1. **知识锚定:** 所有生成内容必须可溯源到课程知识库中的具体章节
2. **防止幻觉:** LLM 基于检索到的上下文生成，而非"凭记忆"
3. **可验证:** Trust Layer 可以检查生成内容是否能在知识库中找到支撑

**替代方案:**
- Fine-tuning: 更新成本高、无法溯源、不适合动态知识 → 拒绝
- Pure LLM: 幻觉不可控 → 拒绝
- 微调 + RAG: 过度工程化，当前阶段不需要 → 未来可考虑

---

### ADR-003: Why EventBus?

**状态:** Accepted  
**日期:** 2026-07-13

**背景:** 6 个 Agent 需要通信、Dashboard 需要观测所有 Agent 行为、TraceCollector 需要持久化执行记录。

**决策:** 保留 A3 的 Singleton AgentEventBus 模式。

**理由:**
1. **Agent 解耦:** Agent 不直接调用其他 Agent，只 emit 事件到 EventBus
2. **统一可观测入口:** Dashboard 通过 `get_timeline()` 读取所有 Agent 事件
3. **Trace 自动收集:** TraceCollector 订阅 EventBus，无需 Agent 感知
4. **经过 241 测试验证:** A3 中 EventBus + 12 Agent 稳定运行

**替代方案:**
- Direct function call: 紧耦合，难以追踪 → 拒绝
- Message Queue (RabbitMQ/Kafka): 过度工程化 → 拒绝
- gRPC: 引入额外复杂性 → 拒绝

---

### ADR-004: Why Three-Tier Memory Architecture?

**状态:** Accepted  
**日期:** 2026-07-13

**背景:** A3 的 Memory 系统为双层：StudentMemory (JSON) + ExperienceMemory (JSON)。存在三个问题：JSON 文件不支持复杂查询、关键词匹配召回精度低、无法记录画像演化历史。

**决策:** 升级为三层记忆，每层使用最合适的存储：

| 层 | 存储 | 为什么 |
|:---|:-----|:-------|
| Conversation Memory | Redis | 低延迟，TTL 自动过期，不需要持久化短期对话 |
| Profile Memory | PostgreSQL | 结构化数据，需要事务保证，需要复杂查询 (画像演化时间线) |
| History Memory | PostgreSQL + ChromaDB | 结构化学习记录 (PG) + 语义经验搜索 (Vector DB) |

**理由:**
1. **分离关注点:** 短期对话 vs 长期画像 vs 学习记录，各有不同的访问模式
2. **查询能力:** PostgreSQL 支持 SQL 查询 (如"最近一周错误率最高的概念")，JSON 文件做不到
3. **语义搜索:** ChromaDB 替代关键词匹配，经验召回质量质变
4. **画像演化可审计:** profile_evolution 表记录每次变化的 reason

---

### ADR-005: Why Memory Trust Layer?

**状态:** Accepted  
**日期:** 2026-07-13

**背景:** 教育系统中，学生可能口头声称掌握某个概念 (如 "我已经精通Transformer")，但实际并未掌握。如果用户的声明直接写入长期画像，会导致系统跳过关键学习内容 —— 这是 Memory Poisoning。

**决策:** 所有 Memory 写入必须经过 6 步 Validation Pipeline:
```
User Input → Extract → Source Classify → Consistency Check → Confidence Score → Dual-State Store
```

**关键设计:**
1. **来源分级:** exercise_result (权重0.35) > behavior_data (0.25) > rag_evidence (0.20) > system_inference (0.15) > user_statement (0.05)
2. **Dual-State Storage:** confirmed (可用于Agent决策) vs candidate (等待验证)
3. **ProfileAgent 只能写 candidate** — 用户声明不直接进入长期画像
4. **ReflectionAgent 可以写 confirmed** — 基于客观评估证据

**替代方案:**
- 直接信任用户输入: Memory Poisoning风险 → 拒绝
- 所有输入需人工审核: 不可扩展 → 拒绝

---

### ADR-006: Why Agent + Tool (not More Agents)?

**状态:** Accepted  
**日期:** 2026-07-13

**背景:** A3 有独立的 ResourceGenerationAgent、ContentAgent、ResourceRecommendationAgent 等多个 Agent 处理资源相关任务。是否应该继续拆分？

**决策:** 采用 Agent + Tool 架构。1个 ResourceAgent 负责决策，多个 Generator Tool 负责执行。

```
Agent (决策)         Tool (执行)
ResourceAgent  ──→  DocumentGenerator
              ──→  PPTGenerator
              ──→  QuizGenerator
              ──→  CodeLabGenerator
              ──→  MindMapGenerator
```

**理由:**
1. **决策统一:** "这个学生需要什么资源？怎么个性化？" — 一个Agent统一决策
2. **执行多样:** "怎么生成这些资源？" — 多个Tool分别执行
3. **Agent是有状态的决策单元，Tool是无状态的执行单元**
4. **避免Agent爆炸:** 5种资源 ≠ 5个Agent。新增资源类型 = 新增Tool即可

**Skill Router 作为调度层:** Agent不直接选择Tool，由Router根据 intent 匹配、权限检查、Token预算控制。

---

## 二、迁移路线 (5 Phase)

### Phase 1: 核心学习闭环 (5天)

```
目标: 让系统能够跑通 "画像→诊断→规划→生成→评估" 最小闭环

□ ProfileAgent — 规则引擎 + LLM双模式 (A3迁移+升级)
□ PlannerAgent — 知识缺口驱动规划 (A3升级)
□ ResourceAgent + 3 Generator Tools
  □ DocumentGenerator (Markdown讲义)
  □ QuizGenerator (3级难度习题)
  □ MindMapGenerator (Mermaid思维导图)
□ EvaluationAgent — 多维度评估 (A3升级)
□ AgentEventBus — 通信基础 (A3保留)
□ LLMProvider — 模型抽象 (A3保留)
□ 简易Streamlit入口 (A3复用)
```

### Phase 2: RAG + Memory 升级 (4天)

```
目标: 知识检索 + 结构化存储

□ RAG Engine 完整链路
  □ Parser (Markdown)
  □ Chunker (语义分块)
  □ Embedder (BGE local + API)
  □ ChromaDB Vector Store
  □ Retriever (dense + metadata filter)
  □ ContextBuilder
□ KnowledgeAgent — RAG检索封装
□ Memory Layer v1
  □ ProfileMemoryStore (PostgreSQL)
  □ HistoryMemoryStore (PostgreSQL)
  □ ConversationMemory (Redis)
  □ MemoryManager 统一入口
□ migration: student_profiles, mastery_tracking, weak_points, ...
```

### Phase 3: Security + Trust Layer (5天)

```
目标: Memory安全 + Agent权限 + Prompt注入防御

□ Memory Trust Layer
  □ Validation Pipeline (6-step)
  □ Dual-State Storage (candidate/confirmed)
  □ memory_candidates 表 + memory_audit_log 表
  □ Source Classification + Confidence Scoring
□ Agent Permission System
  □ Agent-Capability Matrix
  □ Tool Call Gateway (Identity→Parameter→Scope→Audit)
□ Prompt Injection Defense
  □ Input Sanitizer (pattern detection)
  □ Context Isolation (3-field prompt template)
□ Trust Layer (content)
  □ 4-Gate: Source/Grounding/Hallucination/Safety
□ EventBus 安全升级 (trace_id + permission + audit_id)
```

### Phase 4: Skill Manager + Generator Tools (4天)

```
目标: Skill生命周期管理 + 完整Generator Tools

□ Skill Registry + Skill Router
□ Skill Lifecycle: REGISTER→DISCOVER→LOAD→EXECUTE→EVALUATE→CACHE→UNLOAD
□ 完整 Generator Tools
  □ PPTGenerator (python-pptx)
  □ CodeLabGenerator (Python + test stubs)
□ 扩展 Generators
  □ VideoScriptGenerator
  □ AnimationDescGenerator
□ ReflectionAgent (画像更新 + 路径调整)
□ Orchestrator (Pipeline DAG Engine)
```

### Phase 5: API + Deployment + Docs (4天)

```
目标: 可部署 + 完整文档

□ FastAPI Layer (routes: session/profile/learn/knowledge/dashboard)
□ Docker Compose (api + postgres + redis + chroma + streamlit)
□ Learning Analytics (画像演化/掌握度变化/资源效果分析)
□ 集成测试 (端到端闭环)
□ 文档: architecture/agent/rag/memory/security/skill/deployment
□ ADR × 6
□ README + Demo GIF
```

**总预计: 22 天 (约 4.5 周)**

---

## 三、开发优先级

### P0 — 必须 (核心闭环)

| 模块 | 为什么是P0 |
|:-----|:-----------|
| Memory Layer (Profile) | 画像存储是一切个性化的基础 |
| RAG Engine | 知识准确性是 Veritas 的核心承诺 |
| ProfileAgent | 学习闭环的第一步 |
| KnowledgeAgent | RAG检索的Agent封装 |
| ResourceAgent (5种资源) | 核心价值交付 |
| Trust Layer (4-Gate) | Veritas = 可信内容 |
| AgentEventBus | Agent通信基础设施 |
| LLMProvider | LLM调用抽象 |

### P1 — 重要 (完善闭环)

| 模块 | 优先级理由 |
|:-----|:-----------|
| PlannerAgent | 路径规划是学习体验的核心 |
| EvaluationAgent | 评估是闭环的反馈传感器 |
| ReflectionAgent | 闭环优化的最后一步 |
| ConversationMemory | 短期上下文改善Agent推理 |
| HistoryMemory | 长期数据分析的基础 |

### P2 — 重要但可后移

| 模块 | 优先级理由 |
|:-----|:-----------|
| FastAPI Layer | 可先用Streamlit直接调用Agent |
| Docker Compose | 可手动安装依赖运行 |
| Learning Analytics | 数据积累后再做分析 |
| VideoScript + AnimationDesc | 核心5种资源足够演示 |

### P3 — 锦上添花

| 模块 | 优先级理由 |
|:-----|:-----------|
| PPT生成 (python-pptx) | Markdown讲义可替代 |
| 多格式文档解析 (PDF/PPT) | Markdown已覆盖核心场景 |
| 多学生并发支持 | 当前为单学生场景 |
| Dashboard升级 | Streamlit现有Dashboard可用 |

---

## 四、风险分析

| 风险 | 概率 | 影响 | 缓解措施 |
|:-----|:----:|:----:|:---------|
| **RAG 检索质量不稳定** | 中 | 高 | ① Trust Layer 的 Grounding Check 持续监控；② Chunk 参数可调；③ 保留A3的确定性规则引擎作为fallback |
| **LLM 生成内容不可信** | 中 | 高 | ① 4-Gate Trust Layer (来源验证 + 引用检查 + 幻觉检测)；② 最多3轮自动修正；③ 教育内容是相对确定的知识，比开放对话容易验证 |
| **Migration 破坏现有A3功能** | 低 | 中 | ① Veritas_Core 作为独立项目目录 (projects/veritas-core/)；② A3 保留为 archive 分支；③ 按Phase渐进迁移，每Phase可独立验证 |
| **Agent 协作链路断裂** | 低 | 中 | ① 使用DAG而非自由对话，执行顺序确定；② Agent有明确的输入输出dataclass合约；③ EventBus记录每一步，便于调试 |
| **多模型成本** | 中 | 低 | ① TokenTracker 实时监控消耗；② 规则引擎 (ProfileAgent/PlannerAgent) 零LLM成本覆盖70%场景；③ Local Embedding 零成本 |
| **ChromaDB 大规模瓶颈** | 低 | 低 | ① 教育场景的知识库规模有限 (数十个文档)；② BaseRetriever 接口支持切换到 Milvus |
| **时间不足 (3周)** | 中 | 高 | ① 按P0→P1→P2→P3优先级推进；② 核心闭环 (P0) 可在2周内完成；③ P2/P3 模块可逐步补充 |

---

## 五、竞赛要求映射 (Veritas_Core覆盖)

| # | 要求 | Veritas_Core 实现 | 状态 |
|:--|:-----|:--------------------|:----:|
| 1 | **自然语言学生画像** | ProfileAgent: 学生自然语言 → 8维DynamicProfile, 规则+LLM双模式 | ✅ |
| 2 | **6维以上画像** | 8维: 知识基础/学习目标/认知风格/薄弱点/学习习惯/资源偏好/学习动机/时间投入 | ✅ |
| 3 | **多智能体协同** | 6 Agent通过EventBus协作: Profile→Knowledge→Plan→Resource→Eval→Reflect | ✅ |
| 4 | **5种以上资源生成** | 5种: 讲义/PPT/思维导图/练习题/代码实验 + 扩展: 视频脚本/动画描述 | ✅ |
| 5 | **动态学习路径** | PlannerAgent根据KnowledgeGap+画像生成路径; ReflectionAgent根据评估动态调整 | ✅ |
| 6 | **多模态支持** | Markdown/Mermaid/PPTX/Python代码; 预留视频脚本+动画描述 | ✅ |
| 7 | **学习效果反馈** | EvaluationAgent 4维评估 → ReflectionAgent 画像+路径调整 → 完整闭环 | ✅ |
| 8 | **防幻觉** | 4-Gate Trust Layer: 来源检查/引用验证/幻觉检测/安全过滤 | ✅ |
| 9 | **可解释** | EventBus记录所有Agent决策; TraceCollector持久化; Trust Report溯源码 | ✅ |
| 10 | **RAG增强** | RAG Engine: Parser→Chunker→Embedder→ChromaDB→Retriever→ContextBuilder | ✅ |
| 11 | **三层记忆** | Conversation(Redis)/Profile(PG)/History(PG+VectorDB), 每层独立更新策略 | ✅ |

---

## 六、GitHub 展示方案

### README.md 定位

```markdown
# Veritas_Core — Trustworthy Personalized Learning Multi-Agent System

> A LLM-powered personalized learning system combining Multi-Agent architecture,
> RAG, Memory, and Trust mechanisms for reliable educational AI.

[![Python](https://img.shields.io/badge/python-3.11+-blue)]()
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

## ✨ Features

- **🧠 Dynamic Student Profiling** — 8-dimension profiles with Memory Trust validation
- **🔍 RAG-Enhanced Knowledge** — Course content as ground truth, not LLM hallucination
- **🤖 Agent+Tool Architecture** — 6 cognitive agents + Generator tools, Skill Router
- **📚 5 Resource Types** — Notes, PPT, MindMaps, Exercises, Code Labs
- **🔄 Adaptive Learning Loop** — Profile→Diagnose→Plan→Generate→Evaluate→Reflect
- **🛡️ Trust Architecture**
  - Memory Trust Layer — Anti-poisoning, source validation, dual-state storage
  - Agent Permission System — Capability matrix, Tool Call Gateway
  - Prompt Injection Defense — 4-layer: Sanitize→Detect→Isolate→Validate
- **📊 Full Observability** — Trace audit, memory audit log, security alerts

## 🏗 Architecture

[架构图 — 从设计文档中提取]

## 🚀 Quick Start

docker compose up

## 📂 Project Structure

[目录树]

## 📖 Documentation

- [Architecture](docs/architecture.md)
- [Agent Design](docs/agent-design.md)
- [RAG Design](docs/rag-design.md)
- [Memory Architecture](docs/memory-design.md)
- [Learning Loop](docs/learning-loop.md)
- [ADR](docs/adr/)

## 🧪 Demo

[Demo GIF/截图]

## 🛠 Tech Stack

| Layer | Technology |
|:------|:-----------|
| API | FastAPI |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Vector DB | ChromaDB |
| LLM | DeepSeek / Xunfei Spark (via LLMProvider) |
| Frontend | Streamlit |
| Deployment | Docker Compose |
| Testing | pytest |

## 📝 License

MIT
```

### 展示要点

1. **架构图放在最前面:** 一眼看出系统的复杂度和设计质量
2. **Features 列出 6 个核心价值:** 对应系统最突出的工程能力
3. **Quick Start 极简:** `docker compose up` 一行命令就能跑起来 (目标)
4. **Demo GIF:** 展示一个完整的学生学习闭环 (从输入自然语言到获取个性化资源)
5. **Tech Stack 表格:** 展示技术选型广度
6. **文档完整:** 4 个 ADR + 6 个设计文档 + 部署指南
7. **测试覆盖:** 标注测试通过率 (目标 >90%)

---

## 七、Veritas_Core 核心价值总结

| 维度 | 体现 |
|:-----|:-----|
| **LLM Application Engineering** | RAG Engine 完整链路 + 三层记忆架构 (Redis/PG/ChromaDB) + FastAPI + Docker Compose |
| **Multi-Agent Architecture** | 6 Agent 职责清晰的 DAG 协作 + Agent+Tool 分离 + Skill Router 调度 + EventBus 安全通信 |
| **RAG Engineering** | 课程知识增强模块 (Parser/Chunker/Embedder/Retriever/ContextBuilder) + Hybrid检索 + Metadata过滤 |
| **AI Security** | Memory Trust Layer (anti-poisoning) + Agent Permission Matrix + Tool Call Gateway + Prompt Injection 4层防御 + Trace Audit |
| **Memory Engineering** | Dual-State Storage (candidate/confirmed) + Source Classification + Confidence Scoring + TTL管理 |
| **Educational AI** | 完整学习闭环 (画像→诊断→规划→生成→评估→反思→画像更新) + 掌握度EMA + 画像演化审计 |

**Veritas_Core 不是一个 Agent Demo，而是一个体现 LLM Application Engineering + Multi-Agent Architecture + RAG Engineering + AI Security + Educational AI 能力的真实工程项目。**
