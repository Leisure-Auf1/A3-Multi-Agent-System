# Phase 15 — Final Competition Demo Script

> 5 分钟精准演示流程 — 按秒编排
> A3 Multi-Agent Learning System v2.9

---

## 演示前检查清单

- [ ] `streamlit run web/chat_demo.py` 启动正常
- [ ] LLM Provider 选择 "🤖 Mock (Demo)" — 确保稳定
- [ ] Use Knowledge Base ✅ 勾选
- [ ] 浏览器全屏，字体缩放 125%
- [ ] 网络连接测试（Spark 模式需 API key）

---

## Scene 0: 开场 (0:00-0:15)

**画面:** Chat Demo 首页，侧边栏可见

**旁白:**
> "这是 A3 —— 基于大模型的个性化资源生成与学习智能体系统。学生只需要用自然语言描述自己的需求，一个智能体团队就会自动为他生成个性化的学习方案。"

**操作:** 无（静态展示首页）

---

## Scene 1: 学生输入 (0:15-0:45)

**画面:** 在文本框输入学生描述

**预输入文本:**
```
我是网络工程专业的学生，有一些 Python 基础。我比较喜欢看图学习，
不太喜欢纯文字。想快速上手 Multi-Agent AI 系统开发。容易受挫，
希望讲解时多鼓励我。
```

**操作:** 粘贴文本 → 点击 "🚀 Run Pipeline"

**旁白:**
> "学生用自然语言描述自己——不需要填表格，不需要选下拉框。系统会自动理解他的背景、学习风格和目标。"

---

## Scene 2: 画像构建 (0:45-1:30)

**画面:** Pipeline 执行中，Step 1 展示

**预期输出:**
- Source: 🤖 LLM (或 📏 Rule，取决于模式)
- 6 维画像：
  - 📚 Knowledge: mid_level
  - 🧠 Style: visual_dominant
  - ⚠️ Error Bias: magic_syntax_blind
  - ⚡ Pace: fast_track
  - 🖐️ Interaction: code_sandbox
  - 🛡️ Frustration: medium

**旁白:**
> "系统从自然语言中提取了六个维度的学习画像。注意这里的 Confidence 84%——系统知道自己的推断有多可靠。"

**Talking point:** 自然语言 → 结构化画像，6 维，带置信度。

---

## Scene 3: 学习路径 (1:30-2:15)

**画面:** Step 2 展示

**预期输出:**
- 6 个节点（从 KB 章节生成）
- 总时长约 180 分钟
- Strategy: visual 教学策略

**旁白:**
> "PlannerAgent 根据学生的画像和知识库，生成了个性化的学习路径。注意：因为是 visual_dominant 学习者，所有节点都使用视觉教学策略。因为是 fast_track 节奏，跳过了基础章节。"

**Talking point:** 同一课程，不同画像 → 不同路径。路径由 KB 驱动，非硬编码。

---

## Scene 4: 资源生成 (2:15-3:00)

**画面:** Step 3 展示 — 6 张彩色卡片出现

**预期输出:**
- 📄 Course Notes
- 🧠 Mind Map
- ✏️ Exercises
- 💻 Code Lab
- 🎬 Video Script
- 📖 Extended Reading

**操作:** 展开 Mind Map 预览 → 展示 Mermaid 代码；展开 Extended Reading → 展示参考文献列表

**旁白:**
> "系统自动生成了 6 类学习资源——课程讲义、思维导图、练习题、代码实验、视频脚本和拓展阅读。所有资源都适配学生的 visual_dominant 风格。拓展阅读引用来自我们知识库的 curated 文献，不是 LLM 凭空生成。"

**Talking point:** 6 类多模态资源，知识根基可控，无幻觉风险。

---

## Scene 5: Trust & Safety (3:00-3:30)

**操作:** 滚动到 Trust & Safety Panel（或切换到 Dashboard V2）

**画面:** 展示：
- 📚 Knowledge Grounding: 46/46 concepts, 92% confidence
- 📊 Evaluation: Correctness 90%, Completeness 88%, Safety 95%
- 🚪 ReviewGate: AST ✅, Pytest ✅, Judge ✅
- 🔍 Hallucination: 8/8 claims grounded, 0 contradictions

**旁白:**
> "系统的可信度面板展示了知识根基、评估分数和幻觉控制状态。每一份生成的内容都经过三道门禁验证——语法检查、代码执行测试和语义质量判断。"

**Talking point:** 防幻觉不是一句口号——有具体指标和验证流程。

---

## Scene 6: 总结 (3:30-4:00)

**画面:** Pipeline Summary

**旁白:**
> "总结一下：学生用自然语言描述需求 → ProfileAgent 提取六维画像 → PlannerAgent 生成个性化路径 → ResourceGenerationAgent 创建 6 类多模态资源 → 可信度面板保证内容质量。这不是一个 AI 在做所有事——这是 12 个专用 Agent 的协同团队。"

---

## 剩余 1 分钟: Q&A 缓冲

**可选展示 (如果时间允许):**
1. 切换到 Dashboard V2 → 展示 6-panel 系统总览
2. 切换 LLM Provider 到 "📏 Rule Only" → 展示 fallback 机制
3. 展示 ImprovementLoop 面板 → 展示自改进闭环

---

## 演示关键信息总结

| 信息 | 如何传达 |
|:-----|:---------|
| 多智能体 | "12 个专用 Agent" + Dashboard 拓扑面板 |
| 个性化 | 6 维画像 → 不同路径 → 不同资源 |
| 多模态 | 6 类彩色卡片 |
| 可信/安全 | Trust Panel 展示具体指标 |
| 讯飞星火 | Spark 集成 + 切换演示 |
| 自改进 | ImprovementLoop 闭环 |
