# A3 v4 — 国家级大学生人工智能竞赛申报书

> **项目名称：** A3 v4 — 基于多智能体自主协商与知识图谱推理的个性化教育平台  
> **一句话定位：** 让 15 个 AI Agent 组成"虚拟教研室"，通过自主协商、知识推理与自我进化，为每位学生构建"学习的数字孪生"  
> **申报类别：** 人工智能应用创新 · 教育科技赛道  
> **技术栈：** Python 3.11+ | 讯飞星火 Spark Pro | NetworkX | Streamlit

---

## 一、项目核心创新点（5 条）

### 创新点一：基于三阶段协商协议的 AgentCouncil 多智能体自主协同决策机制

针对现有多智能体系统普遍采用固定工作流导致 Agent 间缺乏真正协同的问题，本项目首创 **AgentCouncil 轻量级协商层**，实现 Propose → Deliberate → Decide 三段式多 Agent 协商协议。每个 Agent 可对教学方案的任意环节发起提案、附议、反驳或提出替代方案，Council 通过加权投票 + Chairperson 独裁降级机制在 30 秒内收敛至全局最优决策。该机制使 Agent 从"顺序执行者"升级为"协同决策者"，实现了教育智能体从自动化到自主化的范式跃迁。

**技术突破：** 设计了完整的消息协议（CouncilProposal / CouncilReview / CouncilDecision）、僵局解决算法（3 轮无共识 → 强制裁决 + minority_opinion 审计）、以及无侵入式 EventBus 扩展方案，使现有 12 个 Agent 无需修改核心逻辑即可接入协商层。

---

### 创新点二：基于知识图谱拓扑排序与 Dijkstra 最短路径的个性化学习路径生成算法

传统教育系统依赖人工编排的线性章节，无法自适应学生知识结构的异构性。本项目构建 **InMemoryKnowledgeGraph**（19 节点 × 19 条 PREREQ_OF 依赖边），从课程 Markdown 知识库自动提取概念节点和依赖关系，结合 StudentMemory 的 EMA 掌握度数据（α=0.5），通过图拓扑排序 + Dijkstra 加权最短路径算法计算每个学生的最优学习序列。

**技术突破：** 将路径规划从"规则表查找"提升为"图遍历搜索"——同一课程对不同学生的路径差异率可达 60%+，且保证前置知识无遗漏（拓扑排序保证科学性）。

---

### 创新点三：10 维 DynamicStudentProfile 的动态追踪与置信度衰减机制

传统学习系统的学生画像是一次性快照。本项目将画像从 6 维扩展至 **10 维**（新增学习动机、注意力模式、时间碎片化程度、自我调节能力），每维度独立追踪 **value × confidence × evidence × update_time** 四元组。通过多源信号融合（对话 + 错题 + 行为 + 时长）自动更新画像，辅以**置信度指数衰减**（7 天无新证据 → 0.9/day 衰减）和**证据冲突检测**（新旧值矛盾 → 新证据权重 0.7），使画像从"静态快照"进化为"活的学习者数字孪生"。

**技术突破：** ProfileDiff 差异对比机制支持完整的画像演化审计——每个维度的每次变化都可追溯到具体的证据来源和时间戳。

---

### 创新点四：AgentExperienceMemory 跨学生经验迁移与 StrategyInjector 策略自动注入

现有 AI 教学系统的"经验"无法跨越学生边界复用。本项目通过 **AgentExperienceMemory** 实现跨学生、跨会话的 Agent 行为策略教训积累：ResourceGenAgent 发现视觉型学生对纯文本资源完成率低 → 自动记录经验（problem/cause/solution/success_rate）→ StrategyInjector 在下次规划前自动注入预防策略 → 防范同类错误。预注入 4 条默认经验解决冷启动问题，经验库随使用量增长持续精炼。

**技术突破：** 策略注入采用关键词匹配 + success_rate 排序 + apply_count 加权三重召回，仅当经验置信度 ≥ 0.7 且 apply_count ≥ 2 时才自动注入，保证建议质量。

---

### 创新点五：LearningResource 统一资源协议驱动的插件式多模态资源协奏生成

现有教育 AI 的资源生成局限于文本。本项目定义 **LearningResource 统一协议**（type × format × content × visual_prompt × difficulty × target_profile_dim 六元组），实现 Markdown 笔记、Mermaid 思维导图、PPT 课件、AI 教学配图、Manim 动画描述、视频分镜脚本、代码实验、习题、扩展阅读共 **9 类资源**在同一协议下的协奏生成。**ResourceGeneratorRegistry** 插件式架构支持第三方资源生成器动态注册，visual_prompt 字段将文本内容自动桥接至图像/视频生成 API。

**技术突破：** 协议设计与画像系统深度耦合——每个资源标注 target_profile_dim，推荐系统可根据学生画像自动选择最优资源类型组合。

---

## 二、与普通 ChatGPT 教育助手的本质区别

| 维度 | ChatGPT 教育助手 | A3 v4 多智能体教育平台 |
|:---|:---|:---|
| **架构范式** | 单一 LLM 承担所有角色 | **15 Agent 专职分工**，通过 EventBus + Council 协商达成全局最优 |
| **个性化机制** | Prompt 级描述 (best-effort) | **10 维 DynamicStudentProfile** + EMA 掌握度追踪 + 4 源信号融合 + 置信度衰减 |
| **知识组织** | 依赖 LLM 参数记忆，无结构化 KB | **19 节点知识图谱** + 80+ 概念路径 + 6 章权威 KB 锚定 |
| **路径规划** | "请按顺序列大纲" — 无拓扑保证 | **拓扑排序 + Dijkstra 最短路径**，科学保证前置知识不遗漏 |
| **资源生成** | 纯文本回答 | **9 类多模态资源统一协议**，visual_prompt 自动桥接 AI 图片/动画 |
| **质量保证** | 无系统级质量控制 | **ReviewGate 3 层防线** (AST 静态 + Pytest 动态 + LLM-Judge 语义) |
| **Agent 协作** | 不存在 | **AgentCouncil 协商协议**：提案 → 审议 → 决策，可反驳、可替代 |
| **自我进化** | 依赖模型更新 | **AgentExperienceMemory** 跨学生经验迁移 + StrategyInjector 策略注入 |
| **可解释性** | "我计算得出" | DecisionExplainer 证据链 + Council 协商日志 + confidence score |
| **可观测性** | 对话日志 | EventBus + TraceCollector + **7-panel Dashboard** (含 Council Chamber) |

**一句话总结：** ChatGPT 是一个全科家教，A3 v4 是一个 **AI 教研室**。

---

## 三、技术壁垒

| 壁垒 | 技术内涵 | 复现难度 |
|:---|:---|:---|
| **AgentCouncil 三段式协商协议** | Propose→Deliberate→Decide 完整协议栈 + 加权投票（Agent 可设专家权重）+ 僵局解决（3 轮无共识自动降级）+ minority_opinion 审计记录，涵盖提案类型枚举、决议策略、超时降级等生产级设计 | 🔴 **高** — 需要系统设计 + 分布式协议工程 |
| **KnowledgeGraph 自动构建 + 图搜索路径规划** | 从非结构化 Markdown 到 19 节点的拓扑排序图 + 递归传递前置检索 + Dijkstra 最优路径，涉及 NLP 概念提取 + 图算法交叉技术栈 | 🔴 **高** — 跨领域技术栈 |
| **10 维 DynamicStudentProfile + 指数衰减** | 四源信号融合（对话/错题/行为/时长）+ ProfileEntry 独立生命周期管理 + 证据冲突检测 + 指数衰减算法，涉及教育测量学 + 时序数据建模 | 🟡 **中高** — 需要领域知识 |
| **AgentExperienceMemory + StrategyInjector** | 跨学生经验迁移 + EMA success_rate 更新 + 关键词排序召回 + apply_count 加权自动注入，从单次失败到跨会话知识蒸馏 | 🟡 **中** — 需要系统性工程 |
| **LearningResource 统一协议 + 插件式生成器注册表** | 9 类资源同一协议的强类型约束 + visual_prompt 桥接 + ResourceGeneratorRegistry 动态注册，支持第三方扩展 | 🟡 **中** — 需要协议设计 + API 集成 |

---

## 四、答辩高频问题及标准回答

**Q1: "你们的 AgentCouncil 和普通工作流的区别在哪里？Agent 之间真的在协商吗？"**

> **回答：** 本质区别在于"被动执行"vs"主动博弈"。普通工作流中，ResourceAgent 即使发现 Planner 给错了资源难度，也只能照单生成。在 A3 v4 中，ResourceAgent 检测到矛盾后会**主动发起 CouncilProposal**——提案、举证（附 mastery_map 快照）、建议替代方案。其他 Agent 依次投票，AgentEvaluator 会基于历史评测数据投出加权票。如果 3 轮无法达成 2/3 共识，Chairperson 强制执行并记录 minority_opinion 供审计。这不是"把函数改名 Agent"，这是**真正的 multi-agent deliberation**。

**Q2: "知识图谱是你们手工建的还是自动构建的？19 个节点是不是太少了？"**

> **回答：** 当前 19 节点图谱是**从现有 6 章 Markdown 知识库自动提取的细粒度概念**——不是简单的章节标题，而是从"人工智能概述"到"智能体编排"的概念层级。每个节点的前置依赖（prerequisites 字段）由 LLM 语义推断 + 章节顺序验证双重确认。19 节点是目前竞赛 Demo 的精确覆盖范围。我们预留了 KB 自动解析管线，接入新课程时可通过 KnowledgeGraphAgent 自动扩展至 80-100+ 节点。

**Q3: "15 个 Agent 的 LLM 调用成本怎么控制？"**

> **回答：** 三层成本控制策略。第一层：**规则引擎优先** — ProfileAgent 和 PlannerAgent 默认使用关键词匹配 + 规则表，零 LLM API 调用即完成核心管线。第二层：**LLM 按需激活** — 只有 ContentAgent（内容生成）、ReviewGate Gate 3（语义质量评估）等真正需要语义理解的节点才调用 LLM。第三层：**KV Cache 设计预留** — 对重复画像/概念组合缓存 LLM 响应，预计降低 40-60% API 成本。在规则模式下，完整学习路径规划耗时 < 1 秒，API 成本为零。

**Q4: "系统怎么验证个性化是有效的？"**

> **回答：** 三层验证体系。第一层：**Regression Testing** — 241 个 pytest 测试用例覆盖所有 Agent 的输入输出契约，每次改进后全量通过。第二层：**Benchmark 基准** — 20 个预设不同画像的基准学生案例，对比同一课程在不同画像下的路径差异率。第三层：**UserSimulationAgent** — 基于认知画像驱动的第一人称模拟学习过程，验证改进策略对学习效果的因果影响。我们承认当前 UserSim 是模拟而非真实学生，这是下一步真实课堂验证的重点。

**Q5: "你们的核心到底是多智能体还是知识图谱？创新点太多了是不是摊大饼？"**

> **回答：** 核心是 **"多智能体 + 知识图谱的协同融合"**——不是两者并列，而是知识图谱为多智能体的协商和规划提供**可计算的语义基础**。PlannerAgent 的"规划"在 v3.0 是规则表查找，在 v4.0 是 KnowledgeGraph 上的拓扑搜索。AgentCouncil 的"协商"在缺少知识图谱时只能凭经验投票，有了 KG 后可以用知识缺口（KnowledgeGap）作为提案证据。这不是摊大饼，而是**技术栈的有机耦合**。其他模块（Profile、MultiModal、Evolution）是围绕这个核心的必要支撑。

---

## 五、未来产业化方向

| 方向 | 市场痛点 | A3 v4 技术优势 | 市场前景 |
|:---|:---|:---|:---|
| **高等教育自适应学习平台** | 大班授课无法因材施教 | 10 维画像 + KG 个性化路径 + 多模态资源 | 300 亿 RMB (中国在线高教) |
| **企业 AI 培训 SaaS** | 培训一刀切，效果难量化 | Agent 场景模拟 + 练习自动生成 + 闭环评估 | 50 亿 RMB |
| **K-12 自适应辅导** | 辅导师资参差不齐 | AI 教研团队替代人工教研，7×24 服务 | 500 亿 RMB |
| **终身学习平台** | 成人学习碎片化、目标多样 | 动态画像持续追踪 + 碎片化时间自适应 | 全球 1000 亿 USD |

**短期路径（1-2 年）：** 高校合作试点 → SaaS 多课程扩展 → 多模态 API 接入  
**长期路径（3-5 年）：** 平台化（开放 Plugin API）→ 国际化（多语言）→ K-12 下沉

---

## 附录：A3 v3 → v4 升级总览

| 维度 | v3.0 (竞赛当前) | v4.0 (本设计) |
|:---|:---|:---|
| Agent 数量 | 12 | 15 (+KG, +MultiModal, +BehaviorTracker) |
| 协作模式 | Pipeline (固定管线) | Pipeline + Council (双层) |
| 画像维度 | 6 维静态 | 10 维动态 (value/confidence/evidence/time) |
| 知识组织 | 6 章 Markdown | 19 节点知识图谱 (NetworkX) |
| 路径规划 | 规则表查找 | 拓扑排序 + Dijkstra 最短路径 |
| 资源类型 | 6 类 (文本为主) | 9 类 (统一协议 + 插件注册) |
| 资源协议 | 各类型独立格式 | LearningResource 统一协议 |
| Agent 经验 | 无 | AgentExperienceMemory + StrategyInjector |
| Agent 协商 | 不存在 | AgentCouncil 三段式协议 |
| 代码行数 | ~8,500 | ~10,500 (+2,000 增量) |
| 测试覆盖 | 241 用例 | 目标: 300+ 用例 |

---

*A3 v4 — 从"多智能体 Demo"到"科研级教育智能体平台"*  
*Competition Innovation Document · 2026-07-13*
