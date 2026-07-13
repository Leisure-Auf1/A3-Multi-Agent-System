# Veritas_Core — 多智能体设计

> **6个核心Agent，覆盖学习全链路：** 画像 → 知识 → 规划 → 生成 → 评估 → 反思  

---

## 一、设计原则

| 原则 | 说明 |
|:-----|:-----|
| **Agent服务于教育流程** | 每个Agent映射到学习的一个关键环节，不是为了"展示多Agent"而拆分 |
| **单职责** | 每个Agent只做一件事：画像构建不做知识检索，资源生成不做学习评估 |
| **状态通过Memory共享** | Agent之间不直接调用，通过Orchestrator + Memory层交换数据 |
| **EventBus解耦通信** | 所有Agent emit事件到Singleton EventBus，Dashboard/TraceCollector订阅 |
| **可独立运行** | 每个Agent的输入输出有明确定义的dataclass合约，可独立测试 |

---

## 二、6个核心Agent

### Agent 1: ProfileAgent — 学生画像构建

```
┌─────────────────────────────────────────────────────────────┐
│                      ProfileAgent                            │
│                                                              │
│  输入: 学生自然语言描述                                          │
│  "我是网络工程大三学生，视觉型学习者，Python基础还不错，           │
│   但对异步编程比较困惑，每周能投入10小时，想系统学Agent开发"        │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │            双模式处理引擎                             │    │
│  │                                                     │    │
│  │  规则引擎 (70%置信度, 零延迟)                         │    │
│  │  ├─ 关键词提取: "大三" → mid_level                  │    │
│  │  ├─ 关键词提取: "视觉型" → visual_dominant          │    │
│  │  ├─ 关键词提取: "异步编程困惑" → weak_point          │    │
│  │  └─ 优先级评分 → 6维初步画像                         │    │
│  │                                                     │    │
│  │  LLM增强 (85%置信度, 细粒度理解)                      │    │
│  │  ├─ 自然语言理解 → 深度维度提取                       │    │
│  │  ├─ 缺失维度推断 → 补充画像                           │    │
│  │  └─ 输出结构化JSON → 候选值validation                │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  输出: DynamicProfile (≥8维度)                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 1. knowledge_base (知识基础): mid_level              │    │
│  │ 2. learning_goal (学习目标): Multi-Agent Systems     │    │
│  │ 3. cognitive_style (认知风格): visual_dominant       │    │
│  │ 4. weak_points (薄弱点): [async_io, decorators]     │    │
│  │ 5. learning_habit (学习习惯): code_sandbox           │    │
│  │ 6. resource_preference (资源偏好): diagram+code     │    │
│  │ 7. learning_motivation (学习动机): career_advancement│    │
│  │ 8. time_budget (时间投入): 10h/week                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  动态更新:                                                    │
│    ReflectionAgent 触发 → ProfileAgent.update()              │
│    mastery_map EMA更新 → weak_points增删 → 画像演化记录       │
│                                                              │
│  数据合约:                                                    │
│    Input:  StudentInput {text, source, session_id}            │
│    Output: DynamicProfile {8 dims, confidence, source, ts}    │
│                                                              │
│  A3继承: src/agents/profile_agent.py (470行) → 保留+扩展      │
│    保留: 规则引擎关键词表, LLM提取, dataclass合约              │
│    扩展: +2维度(动机/时间), +动态更新API, +演化时间线           │
└─────────────────────────────────────────────────────────────┘
```

---

### Agent 2: KnowledgeAgent — 课程知识检索 (RAG)

```
┌─────────────────────────────────────────────────────────────┐
│                      KnowledgeAgent                          │
│                                                              │
│  职责: 不是独立知识平台，而是为ResourceAgent提供可靠知识上下文    │
│                                                              │
│  两种模式:                                                    │
│                                                              │
│  Mode 1: 知识诊断 (diagnose)                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 输入: DynamicProfile + 目标课程                        │    │
│  │ 处理:                                                 │    │
│  │   1. RAG检索: 课程知识结构 (章节/概念/前置依赖)         │    │
│  │   2. 画像映射: 学生当前水平 → 知识图谱位置               │    │
│  │   3. 缺口计算: 目标掌握度 - 当前掌握度 = 学习缺口        │    │
│  │ 输出: KnowledgeGap                                     │    │
│  │   {                                                    │    │
│  │     prerequisite_chain: ["python_basics"→"async_io"   │    │
│  │                          →"message_passing"→"agent"],  │    │
│  │     known: [python_basics, functions],                 │    │
│  │     gaps: [async_io(EMA:0.3), agent_patterns(0.1)],   │    │
│  │     recommended_start: "chapter_03_prompt"             │    │
│  │   }                                                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Mode 2: 资源检索 (retrieve)                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 输入: query + student_level + resource_type            │    │
│  │ 处理:                                                 │    │
│  │   1. query → embedding → Vector DB search             │    │
│  │   2. 难度过滤: student_level → difficulty filter       │    │
│  │   3. 重排序: Cross-Encoder Reranking                  │    │
│  │   4. 上下文组装: 多个chunk → 结构化上下文               │    │
│  │ 输出: KnowledgeContext                                 │    │
│  │   {                                                    │    │
│  │     chunks: [Chunk, Chunk, ...],                      │    │
│  │     assembled_text: "## Attention机制\n...\n...",     │    │
│  │     sources: ["ch04_rag.md", "ch05_agent.md"],        │    │
│  │     relevance_scores: [0.92, 0.87, 0.81]             │    │
│  │   }                                                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  数据合约:                                                    │
│    Input:  KnowledgeQuery {query, filters, mode}             │
│    Output: KnowledgeContext | KnowledgeGap                    │
│                                                              │
│  依赖: RAG Engine (Parser/Chunker/Embedder/VectorDB/Retriever)│
│  注意: KnowledgeAgent 不生成内容, 只返回检索到的知识上下文      │
└─────────────────────────────────────────────────────────────┘
```

---

### Agent 3: PlannerAgent — 学习路径规划

```
┌─────────────────────────────────────────────────────────────┐
│                      PlannerAgent                            │
│                                                              │
│  输入:                                                        │
│    - DynamicProfile (8维画像)                                  │
│    - KnowledgeGap (知识缺口)                                    │
│    - HistoryMemory (历史学习数据, 可选)                          │
│                                                              │
│  处理流程:                                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Step 1: 知识缺口 → 学习模块映射                        │    │
│  │   gap_concepts + prerequisite_chain → 拓扑排序       │    │
│  │                                                      │    │
│  │ Step 2: 画像约束应用                                  │    │
│  │   cognitive_style=visual → 每节点映射视觉教学策略       │    │
│  │   knowledge_base=mid → 基线难度+标准深度               │    │
│  │   time_budget=10h → 每节点30-90min, 总计≤10h          │    │
│  │   learning_habit=code_sandbox → 每节点含代码实验       │    │
│  │                                                      │    │
│  │ Step 3: 历史自适应                                    │    │
│  │   mastery_map ≥ 0.8 → 跳过节点 (已掌握)               │    │
│  │   mastery_map ≤ 0.3 → 加大深度 + 增加练习量           │    │
│  │   weak_points ∈ node概念 → 增加针对性练习              │    │
│  │                                                      │    │
│  │ Step 4: 生成PlanNode序列                              │    │
│  │   每个节点: title, concepts, depth, exercises_count,  │    │
│  │            teaching_strategy, estimated_minutes,      │    │
│  │            resource_types[], rationale                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  输出: LearningPlan                                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ PlanNode[]                                            │    │
│  │ ├─ Node 1: LLM回顾 (快进, 30min, notes+mindmap)       │    │
│  │ ├─ Node 2: Prompt Engineering (标准, 60min,            │    │
│  │ │           notes+exercises+code)                     │    │
│  │ ├─ Node 3: RAG原理 (深度, 90min,                       │    │
│  │ │           notes+diagram+code+exercises)              │    │
│  │ ├─ Node 4: Agent通信 (深度, 90min,                     │    │
│  │ │           notes+code+exercises+mindmap)              │    │
│  │ ├─ Node 5: 多Agent架构 (深度, 90min,                   │    │
│  │ │           notes+diagram+case_study)                 │    │
│  │ └─ Node 6: 综合项目 (强化, 120min,                     │    │
│  │             project+code+exercises)                    │    │
│  │ total_minutes: 480, visual_strategy: true              │    │
│  │ rationale: "基于视觉型学习者特点,所有节点增强图表..."     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  A3继承: src/agents/planner_agent.py (614行) → 升级            │
│    保留: 规则引擎, 课程自动检测, pace/cognitive/mastery调整表   │
│    新增: KnowledgeGap驱动起点定位, 历史数据自适应, 路径调整API   │
└─────────────────────────────────────────────────────────────┘
```

---

### Agent 4: ResourceAgent — 个性化资源生成（核心Agent）

```
┌─────────────────────────────────────────────────────────────┐
│                      ResourceAgent                           │
│                                                              │
│  这是 Veritas_Core 的核心生成Agent。                            │
│                                                              │
│  输入:                                                        │
│    - PlanNode (学习节点定义)                                    │
│    - DynamicProfile (学生画像 → 个性化参数)                      │
│    - KnowledgeContext (RAG检索到的知识上下文)                     │
│                                                              │
│  5种核心资源 + 2种扩展:                                        │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 1. CourseNotes (课程讲义)                             │    │
│  │    生成: KnowledgeContext → LLM结构化生成               │    │
│  │    格式: Markdown, 含标题层级/关键概念/代码示例/总结      │    │
│  │    个性化: 根据knowledge_base调整深度和术语难度           │    │
│  │                                                      │    │
│  │ 2. PPT (演示文稿)                                      │    │
│  │    生成: CourseNotes → python-pptx 自动排版             │    │
│  │    格式: .pptx, 每页含标题/要点/图表占位                 │    │
│  │    个性化: visual_dominant → 增加图表页;                │    │
│  │            text_linear → 增加文字说明页                  │    │
│  │                                                      │    │
│  │ 3. MindMap (思维导图)                                   │    │
│  │    生成: concepts → Mermaid 语法树                      │    │
│  │    格式: Mermaid markdown → 可渲染为SVG                  │    │
│  │    个性化: 按学习节奏展开不同分支深度                     │    │
│  │                                                      │    │
│  │ 4. Exercises (练习题)                                   │    │
│  │    生成: concepts → 3级难度题目                          │    │
│  │    类型: 概念理解/代码实现/案例分析/调试题                │    │
│  │    个性化: weak_points 概念 → 额外练习                   │    │
│  │    格式: 含答案、提示、评分标准                           │    │
│  │                                                      │    │
│  │ 5. CodeLab (代码实验)                                   │    │
│  │    生成: concept → starter_code + expected_output       │    │
│  │    个性化: learning_habit=code_sandbox → 扩展实验       │    │
│  │    格式: Python文件 + test stub + 渐进式hints            │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  扩展资源 (Phase 2):                                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 6. VideoScript (视频脚本)                              │    │
│  │    scene-by-scene 旁白 + 视觉描述 (可对接视频生成)        │    │
│  │                                                      │    │
│  │ 7. AnimationDesc (动画描述)                             │    │
│  │    数学/算法概念的动画描述 (可对接Manim)                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  生成流程 (per resource):                                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 1. KnowledgeAgent.retrieve() → 知识上下文              │    │
│  │ 2. Profile注入 → 难度/风格/语言适配                    │    │
│  │ 3. LLM生成 → 结构化输出 (JSON/Markdown/Code)           │    │
│  │ 4. Trust Layer检查 → 内容可信度评估                     │    │
│  │    4a. 知识引用验证 (生成内容是否基于检索到的知识)        │    │
│  │    4b. 幻觉检测 (是否有未在上下文中的断言)               │    │
│  │    4c. 内容安全过滤 (无不当内容)                        │    │
│  │ 5. 通过 → 返回; 未通过 → 重新生成 (最多3轮)              │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  A3继承: src/agents/resource_generation_agent.py (508行)      │
│    重建: 规则模板填充 → RAG增强LLM生成                         │
│    保留: 5种资源类型的数据合约 (CourseNotes/MindMap/dataclass)  │
│    新增: Trust Layer集成, 画像深度注入, PPT生成能力             │
└─────────────────────────────────────────────────────────────┘
```

---

### Agent 5: EvaluationAgent — 学习效果评估

```
┌─────────────────────────────────────────────────────────────┐
│                     EvaluationAgent                          │
│                                                              │
│  职责: 综合分析学习结果，输出多维度评价                          │
│                                                              │
│  输入:                                                        │
│    - 答题结果 (ExerciseResponse[])                              │
│    - 学习行为 (LearningBehavior {停留时间, 跳过, 重试次数})       │
│    - 资源反馈 (ResourceFeedback {难度自评, 质量评分})            │
│    - ReviewGate 报告 (内容生成质量)                              │
│                                                              │
│  评估维度:                                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 1. 正确性评估 (Correctness)                            │    │
│  │    RuleJudge: 客观题自动判分                            │    │
│  │    LLMJudge: 主观题/代码题语义评估                      │    │
│  │    来源对比: 答案是否与RAG知识上下文一致                  │    │
│  │                                                      │    │
│  │ 2. 知识掌握度 (Knowledge Mastery)                      │    │
│  │    EMA更新: new = old×0.5 + new_score×0.5             │    │
│  │    概念级追踪: 每个概念的掌握度独立计算                   │    │
│  │    输出: mastery_map 更新数据                          │    │
│  │                                                      │    │
│  │ 3. 学习投入度 (Engagement)                             │    │
│  │    行为分析: 停留时间/跳过率/重试率/完成率               │    │
│  │    模式识别: 是否在特定类型内容上停留更长                 │    │
│  │                                                      │    │
│  │ 4. 资源质量反馈 (Resource Quality)                     │    │
│  │    学生自评: "这个讲义难度是否合适?"                     │    │
│  │    使用数据: 思维导图被打开次数 vs 讲义被阅读时长         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  输出: EvaluationResult                                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ {                                                     │    │
│  │   overall_score: 0.78,                               │    │
│  │   correctness: 0.85,                                 │    │
│  │   knowledge_gain: {                                  │    │
│  │     async_io: {before: 0.3, after: 0.6, delta: +0.3},│    │
│  │     message_passing: {before: 0.1, after: 0.45, ...}│    │
│  │   },                                                 │    │
│  │   engagement: 0.90,                                  │    │
│  │   resource_quality: 0.82,                            │    │
│  │   weak_points_updated: [                             │    │
│  │     {concept: "decorators", action: "resolved"},     │    │
│  │     {concept: "message_queue", action: "added"}      │    │
│  │   ],                                                 │    │
│  │   suggestions: ["加强message_passing练习",            │    │
│  │                 "建议增加可视化辅助理解agent_patterns"] │    │
│  │ }                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  A3继承: src/evaluation/agent_evaluator.py (209行) +          │
│         src/evaluation/judge.py                              │
│    保留: RuleJudge确定性评分, 4维评分框架                      │
│    新增: 学习行为分析, 知识掌握度追踪, 资源反馈分析            │
└─────────────────────────────────────────────────────────────┘
```

---

### Agent 6: ReflectionAgent — 闭环优化

```
┌─────────────────────────────────────────────────────────────┐
│                     ReflectionAgent                          │
│                                                              │
│  职责: 根据评估结果，调整画像+路径+资源推荐 → 形成学习闭环       │
│                                                              │
│  输入:                                                        │
│    - EvaluationResult (评估报告)                                │
│    - DynamicProfile (当前画像)                                  │
│    - LearningPlan (当前学习路径)                                 │
│    - HistoryMemory (历史学习数据)                                │
│                                                              │
│  处理流程:                                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Step 1: 画像调整                                      │    │
│  │   掌握度更新: knowledge_gain → ProfileMemory.update   │    │
│  │   薄弱点调整: 已解决的移除, 新增的加入                   │    │
│  │   偏好微调: resource_quality反馈 → 调整资源偏好权重     │    │
│  │   画像记录: 写入演化时间线 (ProfileMemory)             │    │
│  │                                                      │    │
│  │ Step 2: 路径调整                                      │    │
│  │   已掌握节点 → 标记completed, 后续路径跳过              │    │
│  │   薄弱节点 → 增加练习节点或深度                         │    │
│  │   节奏调整: 如果engagement低 → 降低密度                │    │
│  │                                                      │    │
│  │ Step 3: 策略优化                                      │    │
│  │   失败模式分析: 哪类题目错误率高 → 诊断原因             │    │
│  │   经验积累: 成功/失败模式 → ExperienceMemory           │    │
│  │   策略建议: 后续节点采用什么教学策略更有效               │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  输出: ReflectionResult                                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ {                                                     │    │
│  │   profile_changes: {                                 │    │
│  │     mastery_updates: {async_io: 0.6, ...},          │    │
│  │     weak_points_added: ["message_queue"],            │    │
│  │     weak_points_removed: ["decorators"],             │    │
│  │     preference_shift: {resource: +diagram}           │    │
│  │   },                                                 │    │
│  │   path_adjustments: {                                │    │
│  │     completed_nodes: ["node_3_rag"],                 │    │
│  │     accelerated_nodes: ["node_4_intro"],             │    │
│  │     reinforced_nodes: ["node_5_message"],            │    │
│  │     added_exercises: [                               │    │
│  │       {concept: "agent_patterns", count: 3}          │    │
│  │     ]                                                │    │
│  │   },                                                 │    │
│  │   next_recommendation: "继续Node 4: Agent通信机制",   │    │
│  │   experience_recorded: [{problem: ..., solution: ...}]│    │
│  │ }                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  副作用 (写入):                                               │
│    ProfileMemory.update()                                     │
│    HistoryMemory.append()                                     │
│    EventBus.emit()                                            │
│                                                              │
│  A3继承: src/core/meta_reflector.py (245行) +                │
│         src/core/improvement_loop.py (195行)                  │
│    保留: 尝试次数诊断, ExperienceMemory存储                    │
│    新增: 画像更新逻辑, 路径自适应调整, LLM深度语义分析          │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、Agent 协作时序

```
  学生输入
     │
     ▼
  Orchestrator.start_session()
     │
     ├─→ [1] ProfileAgent.extract()
     │       读取: ProfileMemory (合并历史画像)
     │       写入: ProfileMemory
     │       Event: emit("ProfileAgent", "extract", ...)
     │       返回: DynamicProfile
     │
     ├─→ [2] KnowledgeAgent.diagnose(profile)
     │       读取: RAG Engine (课程知识结构)
     │       Event: emit("KnowledgeAgent", "diagnose", ...)
     │       返回: KnowledgeGap
     │
     ├─→ [3] PlannerAgent.plan(profile, gap)
     │       读取: HistoryMemory (历史数据自适应)
     │       Event: emit("PlannerAgent", "plan", ...)
     │       返回: LearningPlan
     │
     ├─→ [4] ResourceAgent.generate(plan_node, profile, knowledge)
     │       ┌ 对每个PlanNode循环 ──────────────┐
     │       │ 4a. KnowledgeAgent.retrieve()     │
     │       │     返回: KnowledgeContext         │
     │       │ 4b. LLM生成5种资源                 │
     │       │ 4c. Trust Layer质量检查            │
     │       │ Event: emit("ResourceAgent", ...)  │
     │       └──────────────────────────────────┘
     │       返回: Resources[]
     │
     ├─→ [5] EvaluationAgent.evaluate(responses, behavior, feedback)
     │       读取: 答题结果 + 学习行为 + 资源反馈
     │       写入: HistoryMemory (评估记录)
     │       Event: emit("EvaluationAgent", "evaluate", ...)
     │       返回: EvaluationResult
     │
     └─→ [6] ReflectionAgent.reflect(evaluation, profile, plan)
             读取: EvaluationResult + Profile + Plan + History
             写入: ProfileMemory (画像更新)
             写入: HistoryMemory (经验记录)
             Event: emit("ReflectionAgent", "reflect", ...)
             返回: ReflectionResult (含下一轮建议)

  循环: 如果有新学习节点 → 回到 [3] PlannerAgent.plan() 或 [4] ResourceAgent.generate()
```

---

## 四、Agent 基类设计

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class AgentContext:
    """Agent执行上下文 — 由Orchestrator注入"""
    session_id: str
    student_id: str
    trace_id: str
    memory: "MemoryManager"          # 统一记忆入口
    event_bus: "AgentEventBus"       # 事件总线
    llm_provider: "BaseLLMProvider"  # LLM抽象
    rag_retriever: Optional["BaseRetriever"] = None

class BaseAgent(ABC):
    """Agent基类 — 所有6个Agent继承此类"""

    agent_name: str
    ctx: AgentContext

    @abstractmethod
    def execute(self, input_data: Any) -> Any:
        """Agent主执行入口 — 子类实现"""
        ...

    def record_event(self, action: str, input_summary: str,
                     output_summary: str, status: str = "success",
                     duration_ms: float = 0.0, metadata: Dict = None):
        """通过EventBus记录事件 — 基类提供的通用方法"""
        self.ctx.event_bus.emit(
            agent=self.agent_name,
            action=action,
            input_summary=input_summary,
            output_summary=output_summary,
            status=status,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
```

---

## 五、Agent + Tool 架构原则

> **核心区分：Agent 代表决策能力，Tool 代表执行能力。**

```
6 Cognitive Agents (决策层)
    │
    │ "我需要生成讲义、PPT、习题"
    │
    ▼
Skill Router (调度层)
    │
    │ 匹配 + 加载 + 权限检查
    │
    ▼
Generator Tools (执行层)
    ├── DocumentGenerator
    ├── PPTGenerator
    ├── QuizGenerator
    ├── CodeLabGenerator
    └── MindMapGenerator
```

**为什么不用多个Agent：**
- ResourceGenerationAgent 不拆成 DocumentAgent + PPTAgent + QuizAgent
- 决策是统一的："这个学生需要什么资源？" → 一个 Agent 决策
- 执行是多样的："怎么生成这些资源？" → 多个 Tool 执行
- Agent = 决策者，Tool = 工匠

**ResourceAgent 的 Agent+Tool 模式：**
```
ResourceAgent (一个Agent, 统一决策)
    │
    │ 决策: "该学生是视觉型学习者，需要增强图表；PPT用Vercel风格"
    │
    ▼
SkillRouter.resolve()
    │
    ├── DocumentGenerator.generate(profile=..., knowledge=...)
    ├── PPTGenerator.generate(profile=..., knowledge=..., style="vercel")
    └── QuizGenerator.generate(profile=..., weak_points=[...])
```

---

## 六、为什么6个Agent是正确数量

| 反驳常见误解 | 实际理由 |
|:-----------|:--------|
| "Agent越多越强大" | 教育场景的环节是确定的。6个环节对应6个Agent。执行细节用Tool而非Agent |
| "每个功能都需要Agent" | Agent是有状态的决策单元，不是函数。PPT生成是Tool，不是Agent |
| "12个Agent展示技术能力" | 评审看的是**Agent+Tool架构设计**和**Agent间如何协作**，不是数量 |
| "Agent需要互相协商" | 学习路径是教学逻辑决定的，确定性DAG > 开放协商 |

---

## 七、Generator Tools 清单

| Tool | 输出 | 个性化参数 | 需要RAG |
|:-----|:-----|:-----------|:--------|
| **DocumentGenerator** | Markdown讲义 | knowledge_base → 难度; cognitive_style → 结构 | ✅ |
| **PPTGenerator** | .pptx演示文稿 | cognitive_style → 图表比例; 模板风格 | ✅ |
| **MindMapGenerator** | Mermaid思维导图 | 展开深度 → 画像掌握度 | ✅ |
| **QuizGenerator** | 3级难度习题 | weak_points → 重点题型; 学习节奏 → 题量 | ✅ |
| **CodeLabGenerator** | Python + tests | learning_habit → 实验扩展度 | ✅ |
| **VideoScriptGenerator** | 场景描述文本 | (Phase 2) | ✅ |
| **AnimationDescGenerator** | 动画描述 | (Phase 2) | ✅ |
