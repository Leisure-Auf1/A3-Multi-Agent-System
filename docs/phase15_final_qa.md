# Phase 15 — Final Q&A Preparation

> 评委可能提出的 8 个关键问题 + 标准回答
> Date: 2026-07-13 | A3 v2.9

---

## Q1: "你们和普通的 RAG 系统有什么区别？"

**标准回答:**
> "普通 RAG 是单 Agent 模式——检索文档片段 → 喂给一个 LLM → 生成回答。我们的系统是 12 个专用 Agent 的协同团队。ProfileAgent 理解学习者，PlannerAgent 设计课程路径，ResourceGenerationAgent 生成 6 类多模态资源，AgentEvaluator 给每个 Agent 打分，MetaReflector 分析失败原因，ImprovementLoop 自动改进。这不是'检索+生成'——这是'理解+规划+生成+评估+反思+改进'的完整闭环。"

**关键点:** 不是 RAG vs 非 RAG，而是 1 个 Agent vs 12 个 Agent。

---

## Q2: "为什么需要这么多 Agent？一个 LLM 不够吗？"

**标准回答:**
> "因为教育不是一个'问答'问题。教育需要理解学生（ProfileAgent），需要规划课程（PlannerAgent），需要生成多模态资源（ResourceGenerationAgent），需要评估质量（AgentEvaluator），需要从错误中学习（MetaReflector + ImprovementLoop）。一个 LLM 做所有这些会面临注意力稀释——一条 System Prompt 里塞几千字指令，不同任务互相干扰。12 个 Agent 各司其职，通过 EventBus 和 Memory 协同，每个 Agent 只做一件事，做到最好。"

**关键点:** 单一 LLM = 注意力稀释；Multi-Agent = 专业化分工。

---

## Q3: "如何防止 AI 教错东西（幻觉）？"

**标准回答:**
> "三层防御。第一层：知识根基——所有生成的内容都要对照我们的课程知识库（6 章 curated 内容）进行验证。第二层：ReviewGate 三道门禁——语法检查、代码执行测试、语义质量判断，任何一道不通过都不会发布。第三层：置信度评分——每一份输出都有置信度分数，低置信度的内容会被标记，不会直接推送给学生。我们的 Trust & Safety 面板实时展示这些指标。"

**关键点:** 不是"我们觉得可靠"——有具体指标和验证流程。

---

## Q4: "怎么证明你们的个性化是真实的，不是硬编码的？"

**标准回答:**
> "我们可以现场演示。同一个课程'Multi-Agent AI'，两个不同的学生输入会产生完全不同的学习路径和资源。visual_dominant 学生得到思维导图和 ASCII 图解，text_linear 学生得到分步文字拆解。fast_track 学生跳过基础章节，deep_dive 学生每个概念深挖底层。这一切都是 ProfileAgent 从自然语言中自动提取画像后，PlannerAgent 动态计算的——没有任何 if-else 硬编码分支。"

**操作:** 切换两个不同的学生输入，展示不同路径。

---

## Q5: "为什么选择使用讯飞星火大模型？"

**标准回答:**
> "讯飞星火在教育场景有深厚积累——中文理解能力强，多模态能力完善，Spark 4.0 系列在推理任务上表现优异。我们的系统通过 OpenAI 兼容接口对接 Spark，通过 LLMProvider 抽象层实现 — 未来可以扩展到更多模型。比赛环境的核心推理引擎是讯飞星火 spark-pro。"

**关键点:** Spark 在教育场景的优势 + 技术架构的扩展性。

---

## Q6: "多模态具体体现在哪里？"

**标准回答:**
> "我们的 ResourceGenerationAgent 生成 6 类资源：课程讲义（文档）、思维导图（Mermaid 可视化）、练习题（带评分标准）、代码实验（可执行的脚手架代码）、视频脚本（分镜旁白）、拓展阅读（curated 参考文献）。Dashboard 用彩色卡片展示每类资源，visual_dominant 的学生会看到更多图表，code_sandbox 的学生会得到更多代码实验。多模态不是'我们有图片'——是'资源类型适配学习风格'。"

**关键点:** 6 类资源 × 学习风格匹配 = 真正的多模态。

---

## Q7: "如果大模型 API 出问题了怎么办？"

**标准回答:**
> "我们的系统有三级 fallback。第一级：尝试 Spark API。第二级：如果 API 不可用（网络、配额、超时），LLMAgentAdapter 自动切换到规则引擎——ProfileAgent 用关键词匹配，PlannerAgent 用硬编码知识图谱——同样的输出质量，只是生成路径不同。第三级：ProviderFactory 可以配置 MockProvider，完全离线运行。任何情况下，学生看到的都是完整的个性化方案——只是背后的引擎不同。"

**操作:** Chat Demo 切换 LLM Provider 到 "Rule Only" → 演示相同流程。

---

## Q8: "这个系统的最大创新是什么？"

**标准回答:**
> "两个层面。架构层面：不是 1 个 AI 做所有事，而是 12 个专用 Agent 的协同团队——每个 Agent 有单一职责，通过 EventBus 和 Memory 通信。机制层面：系统不仅是'生成内容'，而是完整的'生成 → 评估 → 反思 → 记忆 → 改进'闭环。如果 AgentEvaluator 发现 PlannerAgent 的个性化不足，MetaReflector 会分析原因，ExperienceMemory 会记录教训，ImprovementLoop 会在下次运行时自动改进。这个自改进闭环是传统教育 AI 没有的。"

**关键点:** Multi-Agent 架构 + Self-Improvement 闭环 = 核心创新。

---

## 应急 Q&A

| 情况 | 应对 |
|:-----|:-----|
| Demo 卡顿 | "系统在实时分析——这是 EventBus 在追踪每个 Agent 的执行状态" |
| Spark 无响应 | 切换到 Mock 模式："我们的 LLMProvider 抽象层支持多模型切换" |
| 时间不够 | 跳过 Scene 5/6，直接总结："核心是 Multi-Agent 协同 + 自改进闭环" |
| 评委质疑复杂度 | "教育问题本身就复杂——12 个 Agent 是问题驱动的设计，不是技术堆砌" |
