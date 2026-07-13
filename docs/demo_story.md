# Demo Story — Xiao Lin: Multi-Agent AI Learning Journey

> 5-minute competition demo flow
> Student: Xiao Lin | Background: Network Engineering | Goal: Multi-Agent AI System Development

---

## Story Arc

```
Xiao Lin enters → System understands → Plans a path → Recommends resources
→ Evaluates quality → Reflects & improves → Dashboard reveals everything
```

---

## Scene 1: Student Onboarding (0:30)

**What the judge sees:**
Student types their background in natural language:

> "I am Xiao Lin, a network engineering student. I have intermediate Python skills
> and want to learn Multi-Agent AI system development. My weak points are
> architecture design and project planning. I prefer code practice and visual explanations."

**What happens:**
`ConversationProfileAgent` + `ProfileAgent` extract a six-dimensional profile:

| Dimension | Value | How It Was Inferred |
|:----------|:------|:--------------------|
| Knowledge Base | `junior_dev` | "intermediate Python" → matched junior keyword table |
| Cognitive Style | `visual_dominant` | "visual explanations" |
| Error Bias | `type_mismatch` | Python typing patterns detected |
| Learning Pace | `normal` | No urgency/fast/deep keywords |
| Interaction Pref | `code_sandbox` | "code practice" |
| Frustration | `medium` | Default (no explicit frustration signal) |

**Talking point:** "The system understands students through natural language, not rigid forms."

---

## Scene 2: Learning Path Generation (0:45)

**What happens:**
`PlannerAgent` auto-detects "Multi-Agent AI" keywords and generates a personalized 5-level learning path:

```
Level 1 — LLM Fundamentals (3 nodes, 65 min)
  LLM 基础原理 → Prompt 工程 → 模型交互与 API

Level 2 — Agent Fundamentals (3 nodes, 85 min)
  Agent 主循环 → Tool Calling → Agent 规划与推理

Level 3 — Multi-Agent Architecture (3 nodes, 85 min)
  Agent 角色分工 → Agent 通信模式 → 任务分解与协作

Level 4 — Runtime Engineering (4 nodes, 115 min)
  EventBus 架构 → Memory 管理 → 状态持久化 → Trace 可观测性

Level 5 — Production Optimization (3 nodes, 85 min)
  Agent 评估体系 → 反思与改进循环 → 系统优化
```

**Personalization applied:**
- `junior_dev` → starts from Level 1 (no skip)
- `visual_dominant` → visual teaching strategy for all nodes
- `code_sandbox` → exercise count boosted by 2
- Weak points (`architecture=0.2`, `planning=0.25`) → depth +1, time +5min

**Talking point:** "Same goal, different student → completely different path. Here's how."

---

## Scene 3: Resource Recommendation (0:45)

**What happens:**
`ResourceRecommendationAgent` reads StudentMemory mastery map and recommends 6 targeted resources:

| Type | Resource | Priority | Reason |
|:-----|:---------|:---------|:-------|
| 🏋️ exercise | architecture_design 专项训练 | 9 | Historical weakness, 2 errors |
| 👁️ visual | 知识点图解总览 | 8 | `visual_dominant` learning style |
| 💻 code_lab | python_basics 实战 | 7 | Mastery=0.7, reinforcement mode |
| 💻 code_lab | api_design 实战 | 7 | Mastery=0.3, deep dive mode |
| 💻 code_lab | architecture 实战 | 7 | Mastery=0.2, boosted exercises |
| 💻 code_lab | project_planning 实战 | 7 | Mastery=0.25, boosted exercises |

**Talking point:** "Every recommendation has a reason. The system doesn't just push content — it explains why."

---

## Scene 4: Quality Evaluation (0:45)

**What happens:**
`AgentEvaluator` scores three agents across 4 dimensions:

| Agent | Correctness | Personalization | Explainability | Efficiency | Overall |
|:------|:-----------:|:---------------:|:--------------:|:----------:|:-------:|
| ProfileAgent | 1.00 | 0.30 | 0.30 | 0.80 | **0.60** |
| PlannerAgent | 0.50 | 0.30 | 0.30 | 0.60 | **0.43** |
| ResourceRec | 0.50 | 0.30 | 0.30 | 0.60 | **0.43** |

**Insight:** PlannerAgent and ResourceRecommendationAgent score below threshold (0.50). This triggers the improvement loop.

**Talking point:** "The system doesn't just run — it grades itself. Low scores trigger self-improvement."

---

## Scene 5: Self-Improvement (0:45)

**What happens:**
Low-score detection → `MetaReflector` analysis → `ImprovementLoop` generates suggestions:

```
❌ FAILURE: ResourceRecommendationAgent score 43% (below 50% threshold)
   ↓
📊 EVALUATION: personalization=0.30 (below 0.40 threshold)
   ↓
🔍 REFLECTION: "Difficulty mismatch — recommended advanced architecture
                resources to intermediate student with weak foundation"
   ↓
💾 EXPERIENCE: Stored in ExperienceMemory (12 lessons accumulated)
   ↓
🚀 STRATEGY: Check mastery map before recommending;
             degrade complexity for low-mastery concepts
```

**Talking point:** "The system learns from its mistakes. Every failure becomes a lesson."

---

## Scene 6: Dashboard Reveal (1:00)

**What the judge sees:**
`streamlit run web/app_v2.py` — 6-panel Intelligence Observatory:

| Panel | Content |
|:------|:--------|
| 🏗️ System Overview | 9 agents, 42 traces, 12 experience lessons |
| 🎯 Student Intelligence | 6-dim profile, mastery heatmap, weak points |
| 📜 Execution Timeline | 12 events with reasoning_type + latency |
| 🔮 Decision Explainability | 8 decisions with evidence + confidence |
| 📊 Agent Evaluation | 4 agents, 4 dimensions each |
| 🔄 Self Improvement | Failure → Eval → Reflection → Strategy chain |

**Talking point:** "Everything the system does is visible, explainable, and evaluable."

---

## Demo Flow Summary

| Time | Scene | Speaker Focus |
|:-----|:------|:--------------|
| 0:00-0:30 | Student Onboarding | Natural language understanding |
| 0:30-1:15 | Learning Path | Personalization + curriculum intelligence |
| 1:15-2:00 | Resource Recommendation | Explainable recommendations |
| 2:00-2:45 | Quality Evaluation | Self-grading mechanism |
| 2:45-3:30 | Self-Improvement | Closed-loop learning |
| 3:30-4:30 | Dashboard Reveal | Full observability |
| 4:30-5:00 | Q&A buffer | — |
