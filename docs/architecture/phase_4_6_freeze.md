# Phase 4.6 — Architecture Freeze

> **冻结日期**: 2026-07-17  
> **状态**: ✅ 所有测试通过 (385 passed, 0 failed)  
> **冻结范围**: Phase 4.1 → 4.6 全链路  

---

## 1. 当前完整架构图

```
                           ┌───────────────────────────┐
                           │        User Goal           │
                           │  "学习 Python Agent 开发"   │
                           └─────────────┬─────────────┘
                                         │
                           ┌─────────────▼─────────────┐
                           │       A3Workflow.run()     │
                           └─────────────┬─────────────┘
                                         │
         ┌───────────────────────────────┼───────────────────────────────┐
         │                               │                               │
         ▼                               ▼                               ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Step 1         │  │  Step 2         │  │  Step 3         │  │  Step 4         │
│  ProfileAgent   │  │  PlannerAgent   │  │  ResourceAgent  │  │  Evaluation     │
│                 │  │                 │  │                 │  │  Manager        │
│  六维画像        │──▶│  学习路径        │──▶│  资源推荐        │──▶│  评分+ReviewGate │
│  {knowledge,    │  │  {nodes,        │  │  [resource...]  │  │  {score,issues, │
│   cognitive,    │  │   rationale}    │  │                 │  │   explanations, │
│   error_bias...}│  │                 │  │                 │  │   review_gate?} │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └────────┬────────┘
                                                                        │
                                                              ┌─────────▼─────────┐
                                                              │  Step 5           │
                                                              │  ReflectionAgent  │
                                                              │                   │
                                                              │  执行后反思         │
                                                              │  {success,score,  │
                                                              │   achievements,   │
                                                              │   improvements}   │
                                                              └────────┬──────────┘
                                                                       │
                                              ┌────────────────────────┼────────────────────────┐
                                              │                        │                        │
                                    ┌─────────▼─────────┐    ┌─────────▼─────────┐    ┌─────────▼─────────┐
                                    │  Phase 4.6        │    │  Phase 4.6        │    │  Phase 4.6        │
                                    │  Adapter          │    │  MetaReflector    │    │  _save_to_memory  │
                                    │                   │    │                   │    │                   │
                                    │  should_trigger?  │───▶│  reflect()        │    │  StudentMemory    │
                                    │  (score<70 or     │    │  └─write _exp_    │    │  {profile,        │
                                    │   has_issues)     │    │     store         │    │   mastery,        │
                                    │                   │    │                   │    │   session}        │
                                    └───────────────────┘    └────────┬──────────┘    └───────────────────┘
                                                                      │
                                                            ┌─────────▼─────────┐
                                                            │  ExperienceMemory │
                                                            │                   │
                                                            │  经验库 (全局)      │
                                                            │  {records.json}   │
                                                            └───────────────────┘


┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                    WorkflowResult                                      │
│                                                                                       │
│  context        WorkflowContext   {session_id, user_goal, start_time}                  │
│  profile        Dict              ProfileAgent 六维画像                                 │
│  learning_plan  Dict              PlannerAgent 学习路径                                 │
│  resources      List[Dict]        ResourceAgent 资源列表                                │
│  evaluation     Dict              {score, passed, issues, explanations, review_gate?}  │
│  reflection     Dict              {success, score, achievements, improvements}         │
│  meta_reflection Optional[Dict]   Phase 4.6: {mistake, root_cause, severity, ...}      │
│  trace          List[Dict]        EventBus 完整时间线                                    │
│  memory_saved   bool              是否持久化                                            │
│  success        bool              整体成功状态                                          │
│  completed_at   str               ISO 时间戳                                            │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent 职责列表

| # | Agent | 文件 | 职责 | 输入 | 输出 |
|---|-------|------|------|------|------|
| 1 | **ProfileAgent** | `src/agents/profile_agent.py` | 从用户目标/对话中提取六维画像 | `user_goal`, `user_profile?` | `ProfileExtractionResult` |
| 2 | **PlannerAgent** | `src/agents/planner_agent.py` | 根据画像规划学习路径 | `DynamicProfile`, `goal_text` | `LearningPlan` (nodes, rationale) |
| 3 | **ResourceAgent** | `src/agents/resource_agent.py` | 推荐个性化学习资源 | `profile`, `goal`, `gaps` | `ResourceRecommendation` |
| 4 | **ReflectionAgent** | `src/agents/reflection_agent.py` | 执行后反思分析 (Phase 3) | `goal`, `plan`, `resources`, `feedback` | `ReflectionResult` |
| 5 | **MetaReflectorAgent** | `src/core/meta_reflector.py` | 系统级自我反思 + 教训持久化 (Phase 4) | `node_id`, `failure_context` | `ReflectionResult` → `ExperienceMemory` |

### 辅助组件

| 组件 | 文件 | 职责 |
|------|------|------|
| **MemoryManager** | `src/memory/memory_manager.py` | 统一 Memory 入口 (Student + Experience) |
| **ExperienceMemoryStore** | `src/memory/experience_memory.py` | JSON 经验库，支持关键词搜索 + 成功率追踪 |
| **StudentMemoryStore** | `src/memory/student_memory.py` | 学生画像 + 掌握度 + 反馈历史 |
| **EvaluationManager** | `src/evaluation/evaluator.py` | 统一评分: 规则评分 + ReviewGate + 决策解释 |
| **ReviewGateManager** | `src/core/review_gate.py` | 三道门禁: AST → Pytest → LLM-as-Judge |
| **MetaReflectionAdapter** | `src/core/meta_reflection_adapter.py` | Phase 4.6 新增: Evaluation → MetaReflector 输入转换 |
| **DecisionExplainer** | `src/core/decision_explainer.py` | Agent 决策解释引擎 |
| **FeedbackLoop** | `src/core/feedback_loop.py` | Phase 5.3: UserSim → MetaReflector → Prompt 优化 |
| **EventBus** | `src/core/event_bus.py` | 全管道事件收集 |
| **TraceCollector** | `src/core/event_trace.py` | 时间线渲染 + 统计 |

---

## 3. Evaluation → Reflection → MetaReflection → ExperienceMemory 数据流

```
EvaluationManager.evaluate()
  │
  ├─ Quality score (rule-based): plan.nodes + resources.types + total_minutes
  ├─ ReviewGate.evaluate_content_quality() [Phase 4.5]
  └─ DecisionExplainer explanations
  │
  ▼ 输出: {score, passed, issues[], explanations[], review_gate?}
  │
  ▼────────────────────────────────────────────────────────────────
  │  ReflectionAgent.reflect(goal, plan, resources, feedback)
  │    ├─ _determine_achievements()   → 成果列表
  │    ├─ _determine_improvements()   → 改进建议
  │    └─ _generate_summary() / LLM   → 综合总结
  │
  ▼ 输出: {success, score, achievements[], improvements[], summary}
  │
  ▼────────────────────────────────────────────────────────────────
  │  Phase 4.6 Trigger:
  │
  │  IF meta_reflector is not None:
  │    MetaReflectionAdapter.should_trigger(evaluation)
  │      → True when score < 70 OR issues non-empty
  │
  │    MetaReflectionAdapter.build_failure_context()
  │      → {mistake, student_id, scores, attempts, profile_type}
  │
  │    MetaReflectionAdapter.determine_severity()
  │      → CRITICAL(<40) | HIGH(<60) | MEDIUM(<70) | LOW(issues)
  │
  │    MetaReflectorAgent.reflect(node_id, failure_context, concept, severity)
  │      ├─ 根因分析 (基于 attempts 计数)
  │      ├─ 生成改进策略 + future_strategy
  │      └─ _exp_store.add_lesson(...)  ← 自动写入 ExperienceMemory
  │
  ▼ 输出: {mistake, root_cause, improvement, future_strategy, severity, ...}
  │         ↓
  │    ExperienceMemoryStore (records.json)
  │      {record_id, problem, cause, context, solution, source, severity, ...}
  │
  ▼────────────────────────────────────────────────────────────────
  │  A3Workflow._save_to_memory()
  │    → StudentMemoryStore: profile, mastery_updates, session
  │    (ExperienceMemory 已由 MetaReflector 在 reflect() 内写入)
```

---

## 4. Workflow 执行流程

```
A3Workflow.run(user_goal, user_profile?, knowledge_gaps?, session_id?)
│
├─ 0. 初始化
│     context = WorkflowContext(session_id, user_goal)
│     result  = WorkflowResult(context)
│     EventBus.start_session()
│
├─ 1. ProfileAgent          ── _run_profile_agent()
│     result.profile = {profile: {...}, source, confidence}
│     emits: "profile_extracted"
│
├─ 2. PlannerAgent          ── _run_planner_agent()
│     result.learning_plan = {nodes, total_minutes, strategy_rationale, metadata}
│     emits: "plan_generated"
│
├─ 3. ResourceAgent         ── _run_resource_agent()
│     result.resources = [{type, title, url, ...}]
│     emits: "resources_recommended"
│
├─ 4. EvaluationManager     ── _run_evaluation()
│     result.evaluation = {score, passed, issues, explanations, review_gate?}
│     emits: "review_completed"
│
├─ 5. ReflectionAgent       ── _run_reflection_agent()
│     result.reflection = {success, score, achievements, improvements, summary}
│     emits: "reflection_completed"
│
├─ 5.5 MetaReflectorAgent   ── [NEW Phase 4.6]
│     IF meta_reflector ≠ None AND adapter.should_trigger():
│       meta_result = meta_reflector.reflect(...)
│       result.meta_reflection = meta_result.to_dict()
│       emits: "meta_reflection_completed"
│
├─ 6. Memory                ── _save_to_memory()
│     StudentMemory: profile + mastery + session
│     result.memory_saved = True
│     emits: "experience_saved"
│
├─ 7. Finalize
│     result.success = len(errors) == 0
│     result.trace = TraceCollector.to_dict_list()
│     emits: "pipeline_completed"
│
└─ return result
```

### DI (Dependency Injection) 矩阵

| 参数 | 默认值 | 注入时机 |
|------|--------|----------|
| `memory_manager` | `MemoryManager()` | `__init__` |
| `profile_agent` | `ProfileAgent()` | `__init__` |
| `planner_agent` | `PlannerAgent()` | `__init__` |
| `resource_agent` | `ResourceAgent()` | `__init__` |
| `reflection_agent` | `ReflectionAgent()` | `__init__` |
| `meta_reflector` | `None` | `__init__` → `set_experience_store()` |
| `llm_provider` | `None` (rule mode) | `__init__` → 注入所有 Agent |
| `bus` | `AgentEventBus.get_instance()` | `__init__` |

---

## 5. Memory 体系说明

```
MemoryManager
├── StudentMemoryStore     (students/<id>.json)
│   ├── profile_history     [{knowledge_base, cognitive_style, ...}]
│   ├── mastery_map         {node_id: float (EMA)}
│   ├── weak_points         [{concept, error_type, occurrence_count}]
│   ├── feedback_history    [{node_id, score, issues}]
│   └── session_history     [{course_id, nodes_completed, total_score}]
│
└── ExperienceMemoryStore  (experience/records.json)
    ├── seed_default_lessons()   5 条预置通用教训
    ├── add_lesson()             去重: 相同 problem+cause → usage_count++
    ├── search_similar()         关键词 + 成功率加权
    ├── get_relevant_lessons()   node_id + profile_type 优先匹配
    ├── update_success_rate()    EMA 更新方案成功率
    └── stats()                  {total_lessons, by_source, by_severity}

两种 Lesson 来源:
  1. FailurePatternLesson    (contracts.py)
     ├── _LocalMemoryStore   (MetaReflector 内置)
     └── 5 条 BUILTIN_LESSONS (预置)

  2. ExperienceRecord        (experience_memory.py)
     ├── source: "usersim" | "reviewgate" | "metareflector"
     └── 5 条 seed 教训 (seed_default_lessons)

写入路径:
  FeedbackLoop.run_one_cycle()     → MetaReflector.recall_lessons()  [读取]
  MetaReflector.reflect()          → _exp_store.add_lesson()         [写入]
  MetaReflector.store_lesson()     → _sync_to_experience()           [写入]
  MemoryManager.store_experience() → experience.add_lesson()         [写入]

Phase 4.6 新增写入路径:
  A3Workflow MetaReflector Trigger → MetaReflector.reflect()
    └─ _exp_store.add_lesson()     → ExperienceMemoryStore
```

---

## 6. 测试覆盖统计

### 全量 (Phase 4.1 → 4.6)

```
总计: 385 tests, 0 failed, 1 warning (Starlette deprecation, 非本项目)
```

### 分模块

| 模块 | 文件 | 测试数 | Phase |
|------|------|--------|-------|
| MetaReflection Pipeline | `test_meta_reflection_pipeline.py` | 17 | 4.6 ✨ |
| MetaReflectionAdapter 单元 | (内部) | 10 | 4.6 ✨ |
| Workflow + MetaReflector 集成 | (内部) | 3 | 4.6 ✨ |
| 向后兼容 | (内部) | 2 | 4.6 ✨ |
| Phase 4.5 兼容 | (内部) | 2 | 4.6 ✨ |
| Evaluation Pipeline | `test_evaluation_pipeline.py` | 18 | 4.4 |
| ReviewGate Runtime | `test_review_gate_runtime.py` | 12 | 4.5 |
| ReviewGate | `test_review_gate.py` | 18 | 4.3 |
| LLM Workflow Integration | `test_llm_workflow_integration.py` | 14 | 4.2 |
| Memory Integration | `test_memory_integration.py` | 12 | 4.0 |
| Memory Changes Behavior | `test_memory_changes_behavior.py` | 8 | 4.0 |
| Experience Memory | `test_experience_memory.py` | 10 | 4.0 |
| Student Memory | `test_student_memory.py` | 15 | 3.0 |
| EventBus Isolation | `test_eventbus_isolation.py` | 7 | 4.2.6 |
| Agent Evaluation | `test_agent_evaluation.py` | 16 | 4.0 |
| Feedback Loop | `test_feedback_loop.py` | 11 | 5.3 |
| Full Pipeline (integration) | `tests/integration/test_full_pipeline.py` | 55 | 3-4 |
| Profile Agent | `test_profile_agent.py` | 28 | 2-4 |
| Planner Agent | `test_planner_agent.py` | 25 | 2-4 |
| Resource Agent | `test_resource_recommendation_agent.py` | 11 | 3 |
| RAG Retriever | `test_rag_retriever.py` | 13 | 4.3 |
| API Runtime | `test_api_runtime.py` | 9 | 4.2 |
| User Simulation | `test_user_simulation.py` | 15 | 5 |
| Conversation Profile | `test_conversation_profile_agent.py` | 16 | 4.2 |
| Event Bus | `test_event_bus.py` | 11 | 4.2 |
| Agent Trace | `test_agent_trace.py` | 15 | 4.2 |

### Phase 4.6 测试覆盖详情

```
TestMetaReflectionAdapter
  ✅ test_should_trigger_low_score          — 低分触发
  ✅ test_should_trigger_issues_only        — 有问题即触发
  ✅ test_should_not_trigger_high_score     — 高分没问题不触发
  ✅ test_should_not_trigger_none           — None 不崩溃
  ✅ test_build_failure_context             — 构建正确 failure 结构
  ✅ test_build_failure_context_fallback    — issues 为空时 fallback
  ✅ test_determine_severity_critical       — <40 → CRITICAL
  ✅ test_determine_severity_high           — <60 → HIGH
  ✅ test_determine_severity_medium         — <70 → MEDIUM
  ✅ test_determine_severity_low            — issues only → LOW

TestWorkflowWithMetaReflector
  ✅ test_meta_reflector_wired_to_experience   — _exp_store 注入成功
  ✅ test_meta_reflection_populated_on_low_score — 低分 → meta_reflection 非空
  ✅ test_no_trigger_when_score_high            — 高分不触发

TestBackwardCompat
  ✅ test_workflow_runs_without_meta_reflector  — 不传 meta_reflector 正常运行
  ✅ test_workflow_result_has_meta_reflection_field — 字段存在

TestPhase45Compat
  ✅ test_evaluation_still_has_review_gate      — evaluation 结构不变
  ✅ test_workflow_result_explanations_property — explanations 属性不变
```

---

## 7. Phase 4.7 规划

### 未解决的问题

| # | 问题 | 说明 |
|---|------|------|
| 1 | ReviewGate 评分未回传 MetaReflector | `review_gate` score 仅在 EvaluationManager 内部使用，未作为 failure_context 的一部分传给 MetaReflector |
| 2 | 双 ReflectionResult 类型 | `reflection_agent.ReflectionResult` vs `decision_explainer.ReflectionResult` 字段不同，存在语义混淆风险 |
| 3 | MetaReflector 仅在低分时触发 | 高分但有 issues 也触发已解决，但"满分但 ReviewGate 发现教学问题"场景未覆盖 |

### 候选任务

```
Phase 4.7a — ReviewGate → MetaReflector 精化
  将 ReviewGate.evaluate_content_quality() 的详细评分 (colloquialism/clarity/progression)
  注入 failure_context，使 MetaReflector 能生成更精准的教训。

Phase 4.7b — ReflectionResult 统一
  合并两个 ReflectionResult 或建立 adapter，减少类型混淆。

Phase 4.7c — ExperienceMemory 查询优化
  当前为 JSON + 关键词匹配，考虑升级至 embeddings/vector search。
```

---

## 附录: 文件清单

### 本次 Phase 4.6 修改

| 文件 | 动作 | 行数 |
|------|------|------|
| `src/core/meta_reflection_adapter.py` | **新建** | 151 |
| `src/workflow/result.py` | +4 行 (meta_reflection 字段) | 153 |
| `src/workflow/__init__.py` | +35 行 (DI + trigger) | 525 |
| `tests/test_meta_reflection_pipeline.py` | **新建** | 273 |

### 未修改 (接口完备)

| 文件 | 原因 |
|------|------|
| `src/core/meta_reflector.py` | `set_experience_store` + `reflect` 已就绪 |
| `src/memory/memory_manager.py` | `self.experience` 公开属性可直接传递 |
| `src/memory/experience_memory.py` | `add_lesson` 接口完备 |
| `src/agents/reflection_agent.py` | 与 MetaReflector 职责正交 |
| `src/evaluation/evaluator.py` | 输出格式已含 score/issues |
| `src/core/review_gate.py` | 通过 EvaluationManager 间接调用 |
| `src/core/feedback_loop.py` | FeedbackLoop 独立于 A3Workflow |
