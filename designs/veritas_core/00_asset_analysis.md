# Veritas_Core — A3 资产盘点与迁移决策

> **Veritas_Core 定位:** 可信个性化学习多智能体系统  
> **核心目标:** 根据学生个人特点，自动分析学习需求，生成个性化学习资源和学习路径  

---

## 一、资产四分类评估

### KEEP（直接保留）

| 模块 | 文件 | 行数 | 保留理由 |
|:------|:-----|:-----|:---------|
| **AgentEventBus** | `src/core/event_bus.py` | 199 | 成熟的 Singleton 解耦通信机制，Agent间松耦合核心基础设施。AgentEvent/AgentEventBus 数据模型完善，支持 session 生命周期管理。直接在 Veritas_Core 复用。 |
| **LLMProvider Interface** | `src/llm/provider.py` | ~120 | 良好的 Provider 抽象层，`generate(prompt, system_prompt, temperature, max_tokens)` 接口清晰。支持多模型可替换，已在 A3 中验证 Spark/Mock 双实现。 |
| **ProviderFactory** | `src/core/provider_factory.py` | 175 | 环境驱动工厂模式，`LLM_PROVIDER` env 配置 + 自动 fallback。直接复用。 |
| **TraceCollector** | `src/core/agent_trace.py` | ~250 | 核心可观测资产。Event → 增强 Trace → JSON 持久化链路完整。需升级 Schema（见下文 REFINE）。 |
| **ReviewGate (3-gate)** | `src/core/review_gate.py` | 741 | 独有的内容安全校验管线：AST静态语法检测 → Pytest双向动态验证 → LLM-Judge教学质量评分。直接作为 Trust Layer 的子模块。 |
| **KnowledgeBase Loader** | `src/core/course_kb_loader.py` | 449 | Markdown 章节解析 + 概念提取 + 资源映射。直接对接 RAG 的 Document Parser。 |

**为什么这些模块适合个性化学习系统：**
- EventBus = Agent 协作的"神经系统"，6个Agent通过EventBus通信而非硬编码调用，每个Agent独立可替换
- LLMProvider = 教育场景需要多模型切换（不同的生成任务可能需要不同模型），Provider抽象层让切换零代码
- ReviewGate = 学习内容必须可信，3层校验保证了给学生的内容经过了AST、动态运行、语义三个维度的检查
- KnowledgeBase = 课程知识是教育系统的"锚点"，所有生成内容需要与课程知识对齐

---

### REFINE（升级设计）

| 模块 | 当前形态 | → 升级为 | 升级内容 |
|:------|:---------|:---------|:---------|
| **StudentMemory** | JSON + EMA α=0.5 掌握度追踪 | → **Student Profile Memory** (PostgreSQL) | 从文件JSON升级到结构化数据库；画像维度从6维扩展到8维（新增：学习动机、时间投入）；支持画像演化历史查询 |
| **ExperienceMemory** | JSON + 关键词召回 | → **Learning History Memory** (PostgreSQL + Vector DB) | 关键词匹配 → 语义向量搜索；分离"错题记录""资源反馈""学习行为"为独立表 |
| **ProfileAgent** | 6-dim 规则引擎 + LLM提取 | → **ProfileAgent** (会话式 + 动态更新) | 保留规则引擎+LLM双模式；新增画像动态更新API（学习后自动刷新）；新增画像演化时间线 |
| **PlannerAgent** | 规则表路径规划 (614行) | → **PlannerAgent** (知识诊断驱动) | 保留规则引擎（确定性+零成本）；新增 KnowledgeAgent 诊断缺口 → 精准定位起点；新增路径自适应调整（根据评估反馈重排节点） |
| **MetaReflector** | 尝试次数启发式诊断 (245行) | → **ReflectionAgent** | 新增LLM深度语义分析（补充启发式）；新增画像更新逻辑（学习后自动修正掌握度、薄弱点）；融合 ImprovementLoop 策略注入 |
| **AgentEvaluator** | RuleJudge 4-dim 评分 (209行) | → **EvaluationAgent** (集成 ReviewGate) | 保留 RuleJudge 确定性评分；集成 ReviewGate 的 3-gate 作为内容质量评估；新增学习行为分析维度 |
| **TraceCollector** | JSON 持久化 | → **Learning Process Trace** | Schema 升级：新增 RAG检索记录、资源生成详情、学习行为事件、反馈结果；支持学习分析查询 |
| **ConversationMemory** | 无独立实现 | → **Conversation Memory** (Redis) | 新增会话上下文管理，TTL=24h，最近N轮对话窗口 |

---

### REBUILD（重新实现）

| 模块 | 重建为 | 原因 |
|:------|:-------|:-----|
| **ResourceGenerationAgent** (508行) | → **ResourceAgent** (核心重建) | A3的6类生成器是规则驱动的模板填充。重建为 RAG增强的LLM生成：检索相关课程知识 → 注入学生画像 → 生成个性化资源。保留5种资源类型 + 扩展视频脚本 |
| **AgentRouter** | → **LearningOrchestrator** | A3的Router是前后端双引擎路由。重建为专用学习编排器：管理"画像→诊断→规划→生成→评估→反思"全链路，每个节点由 EventBus 驱动 |
| **ContentAgent** (243行) | → 融入 ResourceAgent | 5-asset生成合约融入 ResourceAgent，作为资源生成的一种模式 |
| **KnowledgeAgent** | → 全新实现 | RAG检索Agent：课程资料 → Parser → Chunk → Embedding → Vector DB → Retriever → KnowledgeContext。独立RAG模块 |

---

### DROP（移除/降级）

| 模块 | 处理 | 原因 |
|:------|:-----|:-----|
| **ConversationProfileAgent** (545行) | ❌ 移除 | 多轮对话画像采集功能合并到 ProfileAgent，作为其"会话式采集"模式 |
| **ResourceRecommendationAgent** (444行) | ❌ 移除 | 推荐逻辑融入 PlannerAgent（路径规划时已包含资源选择）+ ResourceAgent（根据画像定制化） |
| **ImprovementLoop** (195行) | → 融入 ReflectionAgent | 独立的循环调度器不需要单独存在，反思Agent内部完成策略注入 |
| **Council** (v4) | ❌ 暂不纳入 | Agent协商特性对教育场景没有明确价值——学习路径不需要Agent"争论" |
| **KG (Knowledge Graph)** (v4) | ❌ 暂不纳入 | NetworkX知识图谱 → RAG + Vector DB 已覆盖知识检索需求；知识图谱作为未来增强 |
| **Multimodal占位模块** | ❌ 移除 | v4的空壳模块，无实质内容 |
| **Evolution占位模块** | ❌ 移除 | v4的空壳模块，无实质内容 |
| **UserSimulationAgent** | → 可选插件 | 不纳入核心Agent，作为 EvaluationAgent 的可选测试模式 |

---

## 二、资产迁移总结

```
A3 (12 Agents, 22 Modules, ~6500 lines)
        │
        ▼ 四分类
        │
KEEP:    EventBus · LLMProvider · ProviderFactory · ReviewGate · KB Loader
        │
REFINE:  StudentMemory · ExperienceMemory · ProfileAgent · PlannerAgent
         MetaReflector · AgentEvaluator · TraceCollector
        │
REBUILD: ResourceGenerationAgent · ContentAgent → ResourceAgent
         AgentRouter → LearningOrchestrator
         New: KnowledgeAgent(RAG)
        │
DROP:    ConversationProfileAgent · ResourceRecommendationAgent
         ImprovementLoop · Council · KG · Multimodal · Evolution

─────────────────────────────────────────────────
Veritas_Core (6 Agents, ~8 Modules, 目标 ~8000 lines)
─────────────────────────────────────────────────
```

**迁移原则：**
1. **教育场景为核心** — 移除通用化尝试，聚焦个性化学习全链路
2. **保留验证过的资产** — EventBus/ReviewGate/LLMProvider 经过241测试用例验证，直接复用
3. **重构不兼容的部分** — 规则模板生成 → RAG增强LLM生成，从文件JSON → 数据库
4. **移除对教育无价值的模块** — Council/KG/Multimodal 等竞赛展示性模块不纳入核心
5. **渐进式升级** — A3 保持为 archive 分支，Veritas_Core 作为独立项目目录启动
