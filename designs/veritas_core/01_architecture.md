# Veritas_Core 总体架构设计

> **定位:** 基于大语言模型的可信个性化学习多智能体系统  
> **核心闭环:** 学生输入 → 画像构建 → 知识诊断 → 学习路径规划 → 资源生成 → 学习评估 → 画像更新  

---

## 一、系统架构总图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           USER LAYER                                      │
│                                                                           │
│   学生 (自然语言输入)                     教师/管理者 (Web Dashboard)       │
│   "我是网络工程大三学生，有Python基础，      学习分析 · 画像查看 · 系统监控   │
│    想系统学习多智能体系统..."                                              │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         API LAYER (FastAPI)                                │
│                                                                           │
│  POST /api/session/start    开始学习会话, 获取session_id                  │
│  POST /api/profile/extract  学生画像提取 (自然语言 → 结构化画像)          │
│  POST /api/learn/plan       生成个性化学习路径                              │
│  POST /api/learn/generate   生成学习资源 (讲义/PPT/思维导图/习题/代码)      │
│  POST /api/learn/evaluate   提交学习评估结果                                │
│  POST /api/learn/feedback   提交学习反馈/错题                                │
│  GET  /api/student/{id}     查询学生画像+学习记录                           │
│  GET  /api/dashboard        系统可观测数据                                  │
│  POST /api/knowledge/upload 上传课程资料 (PDF/MD/PPT)                      │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │ 同步REST + 异步任务队列
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    LEARNING ORCHESTRATOR                                    │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Learning Pipeline Engine                       │    │
│  │                                                                   │    │
│  │  UserInput → ProfileExtract → KnowledgeDiagnose → PlanPath      │    │
│  │                                    │                              │    │
│  │                                    ▼                              │    │
│  │           ResourceGenerate → Evaluate → Reflect → ProfileUpdate  │    │
│  │                                    │                              │    │
│  │                                    └──────── 反馈闭环 ──────────► │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                           │
│  ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────────┐           │
│  │ Profile  │ │  Knowledge   │ │ Planner  │ │  Resource    │           │
│  │ Agent    │ │  Agent       │ │ Agent    │ │  Agent       │           │
│  │          │ │  (RAG)       │ │          │ │              │           │
│  │画像构建   │ │ 知识检索      │ │路径规划   │ │资源生成       │           │
│  └──────────┘ └──────────────┘ └──────────┘ └──────────────┘           │
│                                                                           │
│  ┌──────────────────┐         ┌──────────────────┐                       │
│  │ Evaluation Agent │ ──────→ │ Reflection Agent │                       │
│  │ 学习效果评估       │         │ 画像/路径调整      │                       │
│  └──────────────────┘         └──────────────────┘                       │
│                                                                           │
│  通信: AgentEventBus (Singleton, 事件驱动)                                │
└──────────────┬───────────────────────────────────────────────────────────┘
               │
     ┌─────────┼───────────┬──────────────┐
     ▼         ▼           ▼              ▼
┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐
│  RAG    │ │  MEMORY  │ │  TRUST   │ │ OBSERVABILITY  │
│  ENGINE │ │  LAYER   │ │  LAYER   │ │                │
│         │ │          │ │          │ │                │
│ Parser  │ │Conv Mem  │ │知识引用   │ │ TraceCollector │
│ Chunker │ │(Redis)   │ │  验证     │ │ (升级版)       │
│ Embedder│ │          │ │          │ │                │
│ Vec DB  │ │Profile   │ │幻觉检测   │ │ Prompt Log     │
│(Chroma) │ │Mem(PG)   │ │          │ │ Token Track    │
│Retriever│ │          │ │内容审核   │ │ Decision Log   │
│         │ │History   │ │          │ │ Learn Analytics│
│ Context │ │Mem(PG+VD)│ │安全过滤   │ │                │
└────┬────┘ └────┬─────┘ └────┬─────┘ └───────┬────────┘
     │           │             │               │
     └───────────┼─────────────┼───────────────┘
                 │             │
                 ▼             ▼
         ┌────────────┐  ┌──────────┐
         │  Vector DB │  │PostgreSQL│
         │ (ChromaDB) │  │ + Redis  │
         └────────────┘  └──────────┘
                 │
                 ▼
         ┌────────────────┐
         │  LLM PROVIDER  │
         │ (DeepSeek/     │
         │  Spark/OpenAI) │
         └────────────────┘
```

---

## 二、各层职责

| 层 | 职责 | 核心组件 | 设计原则 |
|:---|:-----|:---------|:---------|
| **User Layer** | 学生自然语言输入 + 教师可观测 | Streamlit Dashboard (保留A3), 自然语言交互 | 降低使用门槛，支持非技术用户 |
| **API Layer** | REST接口、请求验证、会话管理 | FastAPI, async/await, JSON Schema 验证 | 同步REST为主，异步任务队列处理生成 |
| **Learning Orchestrator** | 6 Agent 工作流调度，学习管线管理 | Pipeline Engine (确定性DAG), EventBus, 状态机 | 学习场景步骤可预期，DAG比开放对话更可靠 |
| **RAG Engine** | 课程知识检索与上下文构建 | Parser → Chunker → Embedder → ChromaDB → Retriever → ContextBuilder | 知识准确性是教育的生命线，RAG锚定课程内容 |
| **Memory Layer** | 三层记忆管理：会话/画像/学习历史 | Redis (Conversation) + PostgreSQL (Profile + History) + ChromaDB (知识向量) | 短期/长期/知识三层分离，各自最优存储 |
| **Trust Layer** | 生成内容可信保障 | 知识来源检查 → RAG引用验证 → 质量评估 → 幻觉检测 → 安全过滤 | Veritas = 学习内容的可靠性是核心承诺 |
| **Observability** | 全链路学习过程追踪 | TraceCollector, PromptLog, TokenTracker, LearningAnalytics | 学习系统需要可审计、可优化、可解释 |
| **LLM Provider** | 多模型抽象接入 | LLMProvider Interface + Factory (A3保留) | 教育场景不同任务可能用不同模型 |

---

## 三、核心数据流

```
═══════════════════════════════════════════════════════════════════
                    完整学习闭环数据流
═══════════════════════════════════════════════════════════════════

Phase 1: 学生输入 ─────────────────────────────────────────────────
│
│  Input:  学生自然语言描述
│          "我是网络工程大三学生,有Python基础,
│           视觉型学习,想系统学习多智能体系统"
│  Module: API Layer → POST /api/session/start
│  Output: session_id, StudentInput 结构化
│
▼
Phase 2: 画像构建 ─────────────────────────────────────────────────
│
│  Module: ProfileAgent.extract(student_input)
│  Process:
│    规则引擎 (关键词+优先级表) → 6维初始画像
│    LLM增强 (深度理解) → 细化画像维度
│    ProfileMemory查询 → 合并历史画像 (EMA)
│  Data:
│    StudentInput → DynamicProfile
│    {
│      knowledge_base: "mid_level",
│      learning_goal: "Multi-Agent Systems",
│      cognitive_style: "visual_dominant",
│      weak_points: ["decorators", "async"],
│      learning_habit: "code_sandbox",
│      resource_preference: "diagram+code",
│      learning_motivation: "career_advancement",
│      time_budget: "10h/week"
│    }
│  Output: DynamicProfile (8维), confidence: 0.85
│  EventBus: emit("ProfileAgent", "extract", ...)
│  Memory:  ProfileMemory.save(profile)
│
▼
Phase 3: 知识诊断 ─────────────────────────────────────────────────
│
│  Module: KnowledgeAgent.diagnose(profile, course_context)
│  Process:
│    RAG检索: 学生目标课程的知识结构
│    画像映射: 学生当前水平 → 知识图谱位置
│    缺口识别: 目标水平 - 当前掌握度 = 学习缺口
│  Data:
│    DynamicProfile + CourseKnowledge → KnowledgeGap
│    {
│      target_course: "multi_agent_systems",
│      known_concepts: ["python_basics", "functions"],
│      gap_concepts: ["async_io", "message_passing", "agent_patterns"],
│      recommended_start: "chapter_02_llm",
│      difficulty_map: {async_io: 0.3, agent_patterns: 0.1, ...}
│    }
│  Output: KnowledgeGap, prerequisite_chain
│  EventBus: emit("KnowledgeAgent", "diagnose", ...)
│
▼
Phase 4: 学习路径规划 ─────────────────────────────────────────────
│
│  Module: PlannerAgent.plan(profile, knowledge_gap)
│  Process:
│    知识缺口 → 学习模块映射
│    画像约束: 认知风格 → 教学策略 (visual → diagram-rich)
│    时间约束: time_budget → 每日节点数
│    前置依赖: prerequisite_chain → 拓扑排序
│    自适应: 历史学习数据 → 节奏调整
│  Data:
│    DynamicProfile + KnowledgeGap → LearningPlan
│    PlanNode[]
│    ├─ Node 1: LLM基础回顾 (快进, depth=1)
│    ├─ Node 2: Prompt Engineering (标准, depth=2)
│    ├─ Node 3: RAG系统原理 (深度, depth=3, +diagram)
│    ├─ Node 4: Agent通信机制 (深度, depth=3, +code_lab)
│    ├─ Node 5: 多Agent架构设计 (深度, depth=3, +case_study)
│    └─ Node 6: 综合项目实践 (强化, depth=4, +project)
│  Output: LearningPlan (ordered nodes, resources, estimated_time)
│  EventBus: emit("PlannerAgent", "plan", ...)
│
▼
Phase 5: 资源生成 ─────────────────────────────────────────────────
│
│  Module: ResourceAgent.generate(plan_node, profile, knowledge_context)
│  Process (per node):
│    RAG检索 → 课程相关知识上下文
│    画像注入 → 适配学生水平/风格
│    LLM生成 → 5种资源类型
│    Trust Layer → 质量检查 → 安全过滤
│  Output per node:
│    ├─ CourseNotes:     结构化讲义 (Markdown)
│    ├─ PPT:            演示文稿 (python-pptx)
│    ├─ MindMap:         思维导图 (Mermaid)
│    ├─ Exercises:       练习题 (3难度级别)
│    └─ CodeLab:         代码实验 (runnable)
│  Extended:
│    ├─ VideoScript:     视频脚本 (scene-by-scene)
│    └─ AnimationDesc:   动画描述 (Manim/TouchDesigner)
│  EventBus: emit("ResourceAgent", "generate", ...)
│
▼
Phase 6: 学习评估 ─────────────────────────────────────────────────
│
│  Module: EvaluationAgent.evaluate(student_id, session_data)
│  Input:
│    - 答题结果 (exercises responses)
│    - 学习行为 (停留时间/是否跳过/重复次数)
│    - 资源反馈 (学生评分/难度自评)
│    - ReviewGate (内容质量校验结果)
│  Process:
│    RuleJudge: 客观题自动判分
│    KnowledgeGap更新: 答题结果 → 掌握度EMA更新
│    BehaviorAnalyzer: 学习行为模式分析
│    Trust Check: 生成内容可信度评分
│  Data:
│    SessionData → EvaluationResult
│    {
│      overall_score: 0.78,
│      correctness: 0.85,
│      knowledge_gain: 0.32,      # 掌握度提升量
│      engagement: 0.90,           # 学习投入度
│      resource_quality: 0.82,     # 资源质量反馈
│      weak_points_updated: [...],
│      suggestions: ["加强async_io练习"]
│    }
│  Output: EvaluationResult
│  EventBus: emit("EvaluationAgent", "evaluate", ...)
│
▼
Phase 7: 画像更新 (反馈闭环) ─────────────────────────────────────
│
│  Module: ReflectionAgent.reflect(evaluation, profile, history)
│  Process:
│    评估分析: 哪些维度需要更新
│    画像更新: mastery_map EMA调整, weak_points增删
│    路径调整: 根据掌握度重排后续节点
│    资源优化: 根据反馈调整资源类型偏好
│    经验存储: 失败模式 → ExperienceMemory
│  Data:
│    EvaluationResult + DynamicProfile → UpdatedProfile
│    {
│      profile_changes: {
│        mastery_map: {async_io: 0.3→0.6, agent_patterns: 0.1→0.35},
│        weak_points: [-"decorators", +"message_queue"],
│        cognitive_adjustment: null  # 认知风格稳定不变
│      },
│      path_adjustments: {
│        accelerate: ["prompt_engineering"],  # 已掌握,快进
│        reinforce: ["message_passing"],      # 需要加强
│        add_exercise: ["agent_patterns"]     # 增加练习
│      },
│      next_recommendation: "继续Node 4: Agent通信机制"
│    }
│  Output: UpdatedProfile, AdjustedPlan
│  EventBus: emit("ReflectionAgent", "reflect", ...)
│  Memory:  ProfileMemory.update() + HistoryMemory.append()
│
▼
循环: 回到 Phase 3 (知识诊断) → Phase 4 (路径调整) → Phase 5 (新一轮资源生成)
```

---

## 四、Agent 协作流程

```
                    ┌──────────────────────────────────────────┐
                    │         Learning Orchestrator             │
                    │          (Pipeline DAG Engine)            │
                    └──────────────────┬───────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         │                             │                             │
         ▼                             ▼                             ▼
┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
│   ProfileAgent  │          │  KnowledgeAgent │          │  PlannerAgent   │
│                 │          │                 │          │                 │
│ "理解学生是谁"    │─────────▶│ "学生缺什么知识"  │─────────▶│ "应该学什么"     │
│                 │ profile  │                 │ gap      │                 │
│ 读取:           │          │ 读取:           │          │ 读取:           │
│  ProfileMemory  │          │  RAG(Vector DB) │          │  ProfileMemory  │
│                 │          │  CourseKB       │          │  HistoryMemory  │
│ 写入:           │          │                 │          │                 │
│  ProfileMemory  │          │  (只读)          │          │  (只读)          │
└────────┬────────┘          └────────┬────────┘          └────────┬────────┘
         │                            │                            │
         │                            │                  LearningPlan
         │                            │                            │
         │                   ┌────────┴────────┐                   │
         │                   │                 │                   │
         │                   ▼                 ▼                   │
         │          ┌─────────────────┐ ┌─────────────────┐       │
         │          │  ResourceAgent  │ │ EvaluationAgent │       │
         │          │                 │ │                 │       │
         │          │ "生成学习资源"    │ │ "学得怎么样"     │       │
         │          │                 │ │                 │       │
         │          │ 读取:           │ │ 读取:           │       │
         │          │  RAG + Profile  │ │  答题结果        │       │
         │          │                 │ │  学习行为        │       │
         │          │ 写入:           │ │  资源反馈        │       │
         │          │  (EventBus)     │ │                 │       │
         │          └────────┬────────┘ │ 写入:           │       │
         │                   │          │  HistoryMemory   │       │
         │                   │          └────────┬────────┘       │
         │                   │                   │                │
         │                   │          EvaluationResult          │
         │                   │                   │                │
         │                   └─────────┬─────────┘                │
         │                             │                          │
         │                             ▼                          │
         │                    ┌─────────────────┐                │
         │                    │ ReflectionAgent │                │
         │                    │                 │                │
         │                    │ "如何改进"       │◄───────────────┘
         │                    │                 │   feedback
         │                    │ 读取:           │
         │                    │  Evaluation     │
         │                    │  Profile        │
         │                    │  History        │
         │                    │                 │
         │                    │ 写入:           │
         │◄───────────────────│  ProfileMemory  │
         │  updated_profile   │  HistoryMemory  │
         │                    │  (策略更新)      │
         └────────────────────┴─────────────────┘

═══════════════════════════════════════════════════════════════
通信机制: AgentEventBus (Singleton)
═══════════════════════════════════════════════════════════════

每个Agent执行完成后:
  → EventBus.emit(agent_name, action, input_summary, output_summary, status, duration_ms)
  → TraceCollector 自动订阅并持久化
  → Dashboard 通过 get_timeline() 读取实时事件
  → 下游Agent通过Orchestrator接收上游输出,非直接依赖
```

---

## 五、架构设计原则

| 原则 | 在Veritas_Core中的体现 |
|:-----|:----------------------|
| **教育场景为核心** | 每个Agent的输入输出都是教育领域概念：画像/知识缺口/学习路径/资源/评估/反思。不引入通用概念（如intent/execution/tool） |
| **Agent服务于学习流程** | 6个Agent映射到学习的6个关键环节。不需要更多Agent——一个环节一个Agent，职责明确 |
| **优先保证核心闭环完整** | 画像→诊断→规划→生成→评估→反思→画像更新，7步形成完整闭环。任一环节可独立运行 |
| **保留A3优秀资产** | EventBus, ReviewGate, LLMProvider, TraceCollector 直接复用。ProfileAgent/PlannerAgent 规则引擎保留 |
| **渐进式升级** | 不推倒重来。A3的JSON Memory → PostgreSQL；规则模板生成 → RAG增强LLM生成；管线式Agent → 可循环的DAG |
| **可信 = 知识锚定 + 质量评估** | Trust Layer 不评价模型，而是保证给学生的是可验证、可溯源的可靠内容 |
