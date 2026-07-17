# Phase 9.3.2 — A3 Product Experience Specification

> **Version:** 1.0 | **Date:** 2026-07-17 | **Type:** Product Specification (no code)  
> **Foundation:** 9 Agents | 1064 Tests | Veritas-Core V7 | Streamlit + FastAPI  
> **Goal:** Research Prototype → AI Learning Software Product

---

## 1. Target Users

### 1.1 Persona Map

```
┌─────────────────────────────────────────────────────────────┐
│                     A3 User Personas                        │
│                                                             │
│  👨‍🎓 Xiao Lin (在校生)         👩‍💻 Mei (职场转型)              │
│  ─────────────────────        ─────────────────────         │
│  年龄: 20                     年龄: 28                       │
│  身份: 计算机大三              身份: 产品经理 → 数据分析        │
│  目标: 补齐 AI 基础            目标: 转行 Data Science         │
│  风格: 视觉 + 代码实验          风格: 阅读 + 案例               │
│  痛点: 找不到系统化教程          痛点: 时间碎片化，自学效率低     │
│  每天: 1-2 小时                 每天: 30 分钟碎片               │
│                                                             │
│  👨‍🏫 Prof. Chen (教师)         🌏 Alex (海外自学)              │
│  ─────────────────────        ─────────────────────         │
│  年龄: 42                     年龄: 24                       │
│  身份: 大学讲师                身份: 全栈开发者                  │
│  目标: 辅助教学 + 出题          目标: 进阶 AI/ML 技能            │
│  风格: 结构化 + 深度            风格: 代码 + 项目驱动             │
│  痛点: 批改作业耗时              痛点: 中文学习资源少              │
│  每天: 课程时间                 每天: 晚上 2 小时                │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 User Needs Matrix

| Need | Xiao Lin | Mei | Prof. Chen | Alex | Priority |
|:-----|:--------:|:---:|:----------:|:----:|:--------:|
| 系统化学习路径 | 🔴 | 🔴 | 🟡 | 🔴 | P0 |
| 个性化难度适配 | 🟡 | 🔴 | 🟡 | 🔴 | P0 |
| 练习题 + 自动批改 | 🔴 | 🟡 | 🔴 | 🟡 | P0 |
| 对话式答疑 | 🔴 | 🔴 | 🟢 | 🔴 | P1 |
| 代码实验环境 | 🔴 | 🟢 | 🟢 | 🔴 | P1 |
| 学习进度追踪 | 🟡 | 🔴 | 🔴 | 🟡 | P1 |
| 视频/图文混合资源 | 🔴 | 🔴 | 🟡 | 🟡 | P1 |
| 课件生成 (教师) | 🟢 | 🟢 | 🔴 | 🟢 | P2 |
| 离线学习 | 🟡 | 🔴 | 🟢 | 🟡 | P2 |

---

## 2. Complete User Journey

### 2.1 Onboarding → Mastery (6 Stages)

```
Stage 1: DISCOVERY (30 seconds)
  User lands on A3 → Sees value proposition → Starts free trial
  Goal: Convert visitor → user in <30s
  Key metric: Signup conversion rate

Stage 2: PROFILE CREATION (2 minutes)
  User describes themselves → ProfileAgent builds 6-dimension profile
  Goal: Capture enough data for personalization
  Key metric: Profile completion rate

Stage 3: GOAL SETTING (1 minute)
  User states learning goal → PlannerAgent generates personalized path
  Goal: User sees a clear, structured plan
  Key metric: Plan acceptance rate

Stage 4: ACTIVE LEARNING (30+ minutes)
  User engages with resources, tutor, exercises
  Goal: Learning happens — comprehension improves
  Key metric: Session duration, resource completion rate

Stage 5: EVALUATION (5 minutes)
  User takes quiz → EvaluationAgent scores + finds gaps
  Goal: Measure learning, identify weak areas
  Key metric: Quiz score, gap detection accuracy

Stage 6: REFLECTION & GROWTH (ongoing)
  ReflectionAgent summarizes → Memory updated → Next plan adapts
  Goal: Continuous improvement loop
  Key metric: Score improvement over time, retention rate
```

### 2.2 First-Time User Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  LANDING  │───▶│  PROFILE │───▶│   PLAN   │───▶│  LEARN   │───▶│  REFLECT │
│  PAGE     │    │  BUILD   │    │  CREATE  │    │  + CHAT  │    │  + NEXT  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
     │               │               │               │               │
     ▼               ▼               ▼               ▼               ▼
  "AI 学习伙伴"   "告诉我你现在的     "你的学习路径    对话式学习 +     "你掌握了 X，
   价值主张 +     水平和目标"        已生成"          资源 + 练习     下一步学 Y"
   开始按钮       ProfileAgent      PlannerAgent     TutorAgent      Reflection
                  6维画像           3层学习路径       + 8种资源       + Evaluation
```

### 2.3 Returning User Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│  DASH-   │───▶│ CONTINUE │───▶│  LEARN   │
│  BOARD    │    │  WHERE   │    │  + EVAL │
└──────────┘    │  LEFT OFF│    └──────────┘
     │          └──────────┘
     ▼
  "欢迎回来!     上次学到: Python OOP
  本周学了 5h    继续 Chapter 4 →
  掌握 12 概念   或者开始测验"
```

---

## 3. AI Learning Workflow

### 3.1 The A3 Pedagogy Model

```
┌──────────────────────────────────────────────────────────────┐
│                   A3 Learning Loop                           │
│                                                              │
│                    ┌──────────┐                              │
│                    │  PROFILE │ ← 你是谁？怎么学最好？        │
│                    │  (6 维度) │                              │
│                    └────┬─────┘                              │
│                         │                                    │
│         ┌───────────────┼───────────────┐                    │
│         ▼               ▼               ▼                    │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│   │   PLAN   │   │ RESOURCE │   │  TUTOR   │               │
│   │  学什么   │←──│  怎么学   │──▶│  答疑解惑 │               │
│   └────┬─────┘   └────┬─────┘   └────┬─────┘               │
│        │              │              │                       │
│        └──────────────┼──────────────┘                       │
│                       ▼                                      │
│                ┌──────────┐                                  │
│                │ EVALUATE │ ← 学到了吗？哪里薄弱？           │
│                └────┬─────┘                                  │
│                     │                                        │
│                     ▼                                        │
│                ┌──────────┐                                  │
│                │ REFLECT  │ ← 总结经验 → 更新画像 → 下一轮   │
│                └──────────┘                                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Learning Session Anatomy (30 min)

```
Timeline:
  0:00  ─ 学生打开 A3，看到上次进度
  0:30  ─ 点击 "继续学习" 或 "开始新课"
  1:00  ─ PlannerAgent 展示今日学习内容预览
  2:00  ─ 学生开始阅读 CourseNotes (Markdown, 10 min)
  12:00 ─ TutorAgent 弹出互动问题: "你现在能用自己的话解释 X 吗？"
  14:00 ─ 学生回答，TutorAgent 反馈 + 补充
  16:00 ─ 学生打开 CodeLab（代码实验，10 min）
  26:00 ─ EvaluationAgent 推送 5 道测验题
  29:00 ─ 评分 + 弱项分析 + 下节课推荐
  30:00 ─ 结束。ReflectionAgent 保存学习记录
```

---

## 4. Student Profile Creation Flow

### 4.1 6维画像模型

```
┌─────────────────────────────────────────────────────┐
│               Student Dynamic Profile                │
│                                                     │
│  ┌─────────────────┐  ┌─────────────────┐          │
│  │ knowledge_base  │  │ cognitive_style │          │
│  │ 知识基础         │  │ 认知风格          │          │
│  │                 │  │                 │          │
│  │ junior_dev      │  │ visual_dominant │          │
│  │ mid_level       │  │ auditory        │          │
│  │ senior          │  │ reading_writing │          │
│  │ beginner        │  │ code_sandbox    │          │
│  └─────────────────┘  └─────────────────┘          │
│                                                     │
│  ┌─────────────────┐  ┌─────────────────┐          │
│  │ error_prone_bias│  │ learning_pace   │          │
│  │ 常见错误倾向      │  │ 学习节奏          │          │
│  │                 │  │                 │          │
│  │ magic_syntax    │  │ slow (slow)     │          │
│  │ blind           │  │ normal          │          │
│  │ over_abstract   │  │ fast            │          │
│  │ copy_paste      │  │ accelerated     │          │
│  └─────────────────┘  └─────────────────┘          │
│                                                     │
│  ┌─────────────────────────┐  ┌──────────────────┐ │
│  │ interaction_preference  │  │ frustration_     │ │
│  │ 交互偏好                  │  │ threshold        │ │
│  │                         │  │ 受挫阈值           │ │
│  │ code_sandbox            │  │                  │ │
│  │ video_first             │  │ low / medium     │ │
│  │ document_first          │  │ high             │ │
│  │ quiz_first              │  │                  │ │
│  └─────────────────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### 4.2 Profile Creation Methods

```
Method A: 自然语言描述 (30s)
  "我大三，学过 Python 基础，想学机器学习。
   喜欢看视频 + 写代码。数学一般。"
  → ProfileAgent 分析 → 6维画像

Method B: 对话式采集 (2min)
  Agent: "你之前写过代码吗？"
  User:  "写过一些 Python"
  Agent: "你更喜欢看书还是看视频？"
  User:  "视频"
  Agent: "遇到困难时你会...?"
  User:  "先自己搜，不行再问人"
  → ConversationProfileAgent → 6维画像

Method C: 快速选择题 (1min)
  Q1: 你的编程经验？ [无/基础/中级/高级]
  Q2: 学习偏好？ [看书/看视频/做实验/做题]
  ... 6 questions
  → Rule-based → 6维画像

Dynamic Update:
  每次学习后，ReflectionAgent 微调画像:
    progress_score > 0.8 → 提升 knowledge_base
    反复错误某类题 → 更新 error_prone_bias
    完成速度快 → 提升 learning_pace
```

---

## 5. Multi-Agent Collaboration Flow

### 5.1 Agent Orchestration Map

```
                     Student Input
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌──────────────┐
    │ Profile  │   │Conversat.│   │  Resource    │
    │ Agent    │   │ Profile  │   │  Recommend.  │
    │          │   │ Agent    │   │  Agent       │
    │ 提取画像  │   │ 对话画像  │   │ 推荐资源      │
    └────┬─────┘   └────┬─────┘   └──────┬───────┘
         │              │               │
         └──────────────┼───────────────┘
                        │
                        ▼
                 ┌──────────┐
                 │ Planner  │  ← 核心：学习路径生成
                 │ Agent    │
                 └────┬─────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ Resource │ │Resource  │ │  Tutor   │
   │ Agent    │ │Gen Agent │ │  Agent   │
   │          │ │          │ │          │
   │ 资源规划  │ │ 资源生成  │ │ 对话教学  │
   └────┬─────┘ └────┬─────┘ └────┬─────┘
        │            │            │
        └────────────┼────────────┘
                     │
                     ▼
              ┌──────────┐
              │Evaluation│  ← 测验 + 评分
              │ Agent    │
              └────┬─────┘
                   │
                   ▼
              ┌──────────┐
              │Reflection│  ← 总结 + 更新记忆
              │ Agent    │
              └──────────┘
                   │
                   ▼
          Student Memory Updated
                   │
                   ▼
          Next Iteration (loop)
```

### 5.2 Agent Data Flow (Single Learning Cycle)

```
1. ProfileAgent:  text_input → ProfileExtractionResult
   Output: {knowledge_base, cognitive_style, error_prone_bias, 
            learning_pace, interaction_preference, frustration_threshold}

2. PlannerAgent:  profile + goal + knowledge_gaps → LearningPlan
   Output: {topic, nodes[{title, concepts, resources, order}], 
            estimated_hours, difficulty_level}

3. ResourceAgent:  profile + plan_node → ResourceRecommendation
   Output: {items[{type, title, url, priority, reason}]}

4. ResourceGenerationAgent:  plan_node + concepts → GeneratedResources
   Output: {course_notes, mind_map, exercises, code_lab, video_script, 
            extended_reading, slides, illustrations}

5. TutorAgent:  student_question + context → TutorResponse (streaming)
   Output: {content, follow_up_questions, suggested_resources, teaching_style}

6. EvaluationAgent:  topic + level → QuizQuestions → StudentAnswers → QuizResult
   Output: {score_percent, weak_areas, strong_areas, recommendations}

7. ReflectionAgent:  session_data → ReflectionResult → Updated StudentMemory
   Output: {insights, mastery_updates, next_recommendations}
```

### 5.3 Coordination via A3Workflow

```
A3Workflow.run(student_goal, student_profile)
  │
  ├─ Phase 1: PROFILE
  │   agent: ProfileAgent
  │   state: PROFILE → PLAN
  │
  ├─ Phase 2: PLAN
  │   agent: PlannerAgent
  │   state: PLAN → EXECUTE
  │
  ├─ Phase 3: EXECUTE (parallel)
  │   agents: ResourceAgent + ResourceGenerationAgent + TutorAgent
  │   state: EXECUTE → EVALUATE
  │
  ├─ Phase 4: EVALUATE
  │   agent: EvaluationAgent
  │   state: EVALUATE → REFLECT
  │
  └─ Phase 5: REFLECT
      agent: ReflectionAgent
      state: REFLECT → MEMORY_UPDATE → DONE
```

---

## 6. Multimodal Resource Interaction Flow

### 6.1 Resource Type Map

```
Student: "我想学 Python OOP"
          │
          ▼
   ResourceGenerationAgent
          │
          ├─ 📄 CourseNotes:   结构化讲义 (Markdown)
          │   交互: 阅读 → 划重点 → 做笔记 → 提问
          │
          ├─ 🧠 MindMap:       知识图谱 (Mermaid)
          │   交互: 展开/折叠节点 → 点击跳转 → 导出图片
          │
          ├─ ✏️ Exercises:     练习题 (单选/填空/代码)
          │   交互: 作答 → 即时批改 → 查看解析 → 重做
          │
          ├─ 💻 CodeLab:       代码实验 (浏览器内运行)
          │   交互: 阅读指导 → 写代码 → 运行 → 对比输出
          │
          ├─ 📊 Slides:        PPT 课件 (分页浏览)
          │   交互: 翻页 → 全屏 → 导出 → 语音讲解
          │
          ├─ 🎬 VideoScript:   视频脚本 (场景 + 画外音)
          │   交互: 阅读脚本 → 生成配音(EdgeTTS) → 播放
          │
          ├─ 📖 ExtendedReading: 拓展阅读 (论文/文章)
          │   交互: 浏览列表 → 打开链接 → 收藏
          │
          └─ 🖼️ Illustration:  概念插图 (AI生成)
              交互: 查看 → 放大 → 下载 → 分享
```

### 6.2 Resource Card UI Pattern

```
┌─────────────────────────────────────────────────────────┐
│  📄 Python OOP 基础讲义                                  │
│  ─────────────────────────────────────────────────────  │
│  Python OOP 入门                   ⏱️ 15 min read       │
│                                                         │
│  [阅读讲义]  [导出 Markdown]  [生成配音]                 │
└─────────────────────────────────────────────────────────┘

┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐
│ 🧠 OOP 知识图谱   │  │ ✏️ OOP 练习题     │  │ 💻 代码实验   │
│                  │  │                  │  │              │
│ [查看] [展开全部] │  │ 5 题 · 中等难度   │  │ Python 3.10  │
│                  │  │ [开始答题]        │  │ [开始实验]    │
└──────────────────┘  └──────────────────┘  └──────────────┘
```

### 6.3 Resource Generation Trigger Flow

```
User Action                    →  Agent Trigger         →  Resource Generated
─────────────────────────────────────────────────────────────────────────────
点击 "开始学习 Chapter 2"       →  ResourceAgent         →  推荐资源列表
点击 "生成讲义"                 →  ResourceGeneration    →  CourseNotes (MD)
点击 "查看思维导图"              →  ResourceGeneration    →  MindMap (JSON→Mermaid)
点击 "生成练习题"                →  ResourceGeneration    →  Exercises (MCQ)
点击 "开始代码实验"              →  ResourceGeneration    →  CodeLab (可运行)
教师点击 "生成课件"              →  ResourceGeneration    →  Slides (分页)
点击 "AI 配图"                  →  ImageGateway          →  Illustration (AI生成)
点击 "播放讲解"                  →  AudioGateway          →  Narration (TTS)
```

---

## 7. Evaluation Feedback Loop

### 7.1 Assessment Cycle

```
┌─────────────────────────────────────────────────────────────┐
│                   Evaluation Feedback Loop                   │
│                                                             │
│   ┌─────────┐      ┌─────────┐      ┌─────────┐           │
│   │  LEARN  │─────▶│  QUIZ   │─────▶│  SCORE  │           │
│   │  (学习)  │      │  (测验)  │      │  (评分)  │           │
│   └─────────┘      └─────────┘      └────┬────┘           │
│                                          │                 │
│                    ┌─────────────────────┼──────────┐      │
│                    ▼                     ▼          ▼      │
│              ┌─────────┐          ┌─────────┐ ┌────────┐  │
│              │  STRONG │          │  WEAK   │ │  NEXT  │  │
│              │  AREAS  │          │  AREAS  │ │  STEPS │  │
│              │  掌握    │          │  薄弱    │ │  建议   │  │
│              └────┬────┘          └────┬────┘ └────┬───┘  │
│                   │                   │           │       │
│                   └───────────────────┼───────────┘       │
│                                       ▼                    │
│                               ┌─────────────┐             │
│                               │  UPDATE     │             │
│                               │  PROFILE +  │             │
│                               │  MEMORY     │             │
│                               └──────┬──────┘             │
│                                      │                    │
│                                      ▼                    │
│                               ┌─────────────┐             │
│                               │  NEXT PLAN  │  ← 循环    │
│                               │  ADAPTED    │             │
│                               └─────────────┘             │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Score Bands & Responses

| Score | Label | Student Sees | System Action |
|:------|:------|:-------------|:--------------|
| 90-100% | 🏆 Excellent | "太棒了！你已完全掌握。准备好挑战进阶内容吗？" | 跳过当前 → 推荐下一个 topic |
| 75-89% | ✅ Good | "很好！有 1-2 个小问题要复习。" | 标记弱项 → 生成针对性练习 |
| 60-74% | 📖 Needs Review | "基础不错，但这几个概念需要再巩固。" | 重生成讲义 + 更多练习 |
| 40-59% | 🔄 Let's Retry | "别担心，我们换个方式再来一次。" | 切换到不同教学风格重讲 |
| <40% | 🆘 Start Over | "看来这个主题需要从头开始。我帮你调整了路径。" | 降级到 beginner → 重建学习计划 |

### 7.3 Progress Tracking

```
Student Dashboard — Progress Section:

┌─────────────────────────────────────────────────────────────┐
│  📊 学习进度                                                 │
│                                                             │
│  Python Basics        ████████████████░░░░  80%  ✅         │
│  OOP Concepts         ██████████░░░░░░░░░░  50%  🔄         │
│  Data Structures      ████████████████████  100% 🏆         │
│  Algorithms           ████░░░░░░░░░░░░░░░░  20%  🆕         │
│                                                             │
│  本周学习: 8.5h  │  完成练习: 23 题  │  掌握概念: 12 个      │
│  连续学习: 5 天 🔥                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Web/Desktop Product Architecture

### 8.1 Product Stack

```
┌──────────────────────────────────────────────────────────────┐
│                     Product Architecture                     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │              Presentation Layer                      │     │
│  │                                                     │     │
│  │  Web: Streamlit (localhost:8501 / Render cloud)     │     │
│  │  Desktop: Streamlit wrapped in PyWebView/Tauri      │     │
│  │  Mobile: PWA (responsive Streamlit)                 │     │
│  └──────────────────────┬─────────────────────────────┘     │
│                         │                                    │
│  ┌──────────────────────┼─────────────────────────────┐     │
│  │              API Layer (FastAPI :8000)              │     │
│  │                                                     │     │
│  │  /api/v1/learning     ← A3Workflow (legacy)        │     │
│  │  /api/v1/runtime      ← RuntimeBus (Veritas-Core)  │     │
│  │  /api/v2/auth/*       ← Auth (Phase 9.1)           │     │
│  │  /api/v2/resources/*  ← Resources (Phase 9.3)      │     │
│  │  /api/v2/chat/stream  ← SSE Streaming (Phase 9.4)  │     │
│  └──────────────────────┬─────────────────────────────┘     │
│                         │                                    │
│  ┌──────────────────────┼─────────────────────────────┐     │
│  │              Agent Layer (A3Workflow)               │     │
│  │                                                     │     │
│  │  9 Agents: Profile → Planner → Resource → ...       │     │
│  │  Orchestrated via Veritas-Core RuntimeEngine         │     │
│  └──────────────────────┬─────────────────────────────┘     │
│                         │                                    │
│  ┌──────────────────────┼─────────────────────────────┐     │
│  │              Data Layer                             │     │
│  │                                                     │     │
│  │  SQLite: users, resources, learning_records         │     │
│  │  Knowledge Base: course JSON files                  │     │
│  │  Veritas-Core: MemoryManager (student memory)       │     │
│  └────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

### 8.2 Client vs Server Split

```
LINUX SERVER (Render/VPS)              WINDOWS CLIENT (Desktop)
─────────────────────────────          ──────────────────────────
FastAPI :8000                          Streamlit :8501
Veritas-Core Runtime                   Local cache (SQLite)
All 9 agents                           UI rendering only
Resource generation                    Offline mode
LLM/Image/Audio API calls              No API keys needed
Master SQLite DB                       httpx → Server API
Knowledge Base
```

---

## 9. UI Page Specification

### 9.1 Page Map

```
A3 Product — Page Map
══════════════════════

/ (Landing)
├── /login
├── /register
├── /dashboard                    ← Main hub after login
│   ├── /learn?topic=python_oop   ← Active learning session
│   │   ├── Chat panel (left)
│   │   ├── Resource viewer (center)
│   │   └── Resource cards (right)
│   ├── /quiz?topic=python_oop     ← Quiz mode
│   ├── /progress                  ← Progress dashboard
│   └── /profile                   ← Profile settings
├── /chat                          ← Standalone tutor chat
├── /resources                     ← Resource library
└── /settings                      ← Account settings
```

### 9.2 Page Specifications

#### Page 1: Landing `/`

```
┌──────────────────────────────────────────────────────────────┐
│                       🦊 A3 智能学习伙伴                       │
│                                                              │
│           你的个人 AI 导师团队 — 随时随地，因材施教              │
│                                                              │
│   ┌─────────────────────┐  ┌─────────────────────┐          │
│   │  🎯 个性化学习路径    │  │  💬 AI 导师实时答疑  │          │
│   │  根据你的基础和目标   │  │  9 个 Agent 协同工作 │          │
│   └─────────────────────┘  └─────────────────────┘          │
│   ┌─────────────────────┐  ┌─────────────────────┐          │
│   │  📚 8 种学习资源     │  │  📊 智能评估反馈     │          │
│   │  讲义/导图/代码/视频 │  │  自动出题 + 弱项分析  │          │
│   └─────────────────────┘  └─────────────────────┘          │
│                                                              │
│              [🎓 免费开始]  [📧 注册账号]                     │
│                                                              │
│   已有账号？ [登录]  或以游客身份 [快速体验]                    │
└──────────────────────────────────────────────────────────────┘
```

#### Page 2: Dashboard `/dashboard`

```
┌──────────────────────────────────────────────────────────────┐
│  A3 学习仪表盘                            👤 Xiao Lin  ▼     │
├────────────┬─────────────────────────────────────────────────┤
│  📚 课程    │  👋 欢迎回来，Xiao Lin！                         │
│            │                                                 │
│  🐍 Python │  ┌─────────────────────────────────┐           │
│  Basics    │  │ 🔥 连续学习 5 天                 │           │
│    80% ██  │  │ 本周: 8.5h · 23 题 · 12 概念    │           │
│            │  └─────────────────────────────────┘           │
│  🏗️ OOP   │                                                 │
│    50% ██  │  📍 继续学习                                     │
│            │  ┌─────────────────────────────────┐           │
│  🔢 Algo   │  │ Python OOP — Chapter 4          │           │
│    20% ██  │  │ 上次学到: 继承与多态              │           │
│            │  │ [继续学习 →]  [重新测验]          │           │
│  ➕ 添加   │  └─────────────────────────────────┘           │
│            │                                                 │
│  ──────    │  📊 本周进度                                     │
│  📜 历史    │  Python Basics     ████████████████░░░  80%    │
│  📝 笔记    │  OOP Concepts      ██████████░░░░░░░░░░  50%    │
│  ⚙️ 设置   │  Data Structures   ████████████████████  100%   │
└────────────┴─────────────────────────────────────────────────┘
```

#### Page 3: Learning Session `/learn`

```
┌──────────────────────────────────────────────────────────────┐
│  🐍 Python OOP — Chapter 4: 继承与多态         📊 50%  ⚙️    │
├─────────────────────┬────────────────────┬───────────────────┤
│  💬 Tutor Chat      │  📄 Course Notes   │  📦 Resources     │
│                     │                    │                   │
│  ┌─────────────────┐│  # Python 继承     │  🧠 思维导图       │
│  │ Tutor: 上次我们  ││                    │  📝 练习题 (5)    │
│  │ 学了继承的概念。  ││  继承是 OOP 的     │  💻 代码实验       │
│  │ 现在试试这个例子: ││  核心概念之一...   │  🎬 视频脚本       │
│  │                 ││                    │  📖 拓展阅读       │
│  │ ```python       ││  ## 基本语法       │                   │
│  │ class Animal:   ││                    │  ─────────────    │
│  │   ...           ││  ```python         │  ⏱️ 学习时长      │
│  │ ```             ││  class Animal:     │  12 min / 30 min  │
│  │                 ││      def speak():  │                   │
│  │ 你能解释这段代码  ││      ...          │  📈 掌握度         │
│  │ 在做什么吗？     ││  ```              │  ████████░░  80%  │
│  └─────────────────┘│                    │                   │
│                     │  ## 多态           │                   │
│  ┌─────────────────┐│  ...               │                   │
│  │ [输入你的回答...]││                    │                   │
│  │            [发送]││                    │                   │
│  └─────────────────┘│                    │                   │
└─────────────────────┴────────────────────┴───────────────────┘
```

#### Page 4: Quiz `/quiz`

```
┌──────────────────────────────────────────────────────────────┐
│  ✏️ Python OOP 测验                          ⏱️ 05:00         │
│                                                              │
│  第 2 / 5 题                               📊 进度 ██░░░     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                                                      │   │
│  │  Q2: 以下哪个选项正确地描述了 Python 中的多态？        │   │
│  │                                                      │   │
│  │  ○ A) 一个类可以继承多个父类                           │   │
│  │  ● B) 不同类的对象可以通过相同的接口调用               │   │
│  │  ○ C) 父类的方法不能被重写                             │   │
│  │  ○ D) 所有对象都共享同一个方法                          │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ✅ 正确！                                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  多态的核心是 "同一个接口，不同实现"。                   │   │
│  │  例如: dog.speak() 和 cat.speak() 都调用 speak()，     │   │
│  │  但实际行为由各自的类决定。                              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│                              [上一题]  [下一题 →]             │
└──────────────────────────────────────────────────────────────┘
```

#### Page 5: Progress `/progress`

```
┌──────────────────────────────────────────────────────────────┐
│  📊 学习报告                            👤 Xiao Lin  ▼       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  📅 学习日历                                                  │
│  ┌──┬──┬──┬──┬──┬──┬──┐                                    │
│  │🟢│🟢│🟢│  │🟢│🟢│  │  ← 本周 5 天学习                   │
│  └──┴──┴──┴──┴──┴──┴──┘                                    │
│                                                              │
│  📈 掌握趋势                           📊 能力分布            │
│  ┌────────────────────┐              ┌──────────────────┐   │
│  │ 100%               │              │ 语法      ████ 90%│   │
│  │  80%    ╭──╮       │              │ 面向对象  ██░ 60%│   │
│  │  60%  ╭─╯  ╰─╮    │              │ 算法      █░░ 30%│   │
│  │  40% ╭╯      ╰──  │              │ 数据结构  ░░░ 10%│   │
│  │      └───────────  │              └──────────────────┘   │
│  └────────────────────┘                                     │
│                                                              │
│  🎯 薄弱环节 (需要加强)                                       │
│  • 多态的实际应用场景 (2 次错误)                               │
│  • 抽象类的使用时机 (1 次错误)                                 │
│                                                              │
│  📝 学习建议                                                  │
│  • 完成 "多态实战" CodeLab                                    │
│  • 复习 Chapter 4.3 抽象类部分                                │
└──────────────────────────────────────────────────────────────┘
```

---

## 10. Competition Demo Scenario

### 10.1 Demo Flow (5 minutes)

```
⏱️ 0:00 — LANDING PAGE
─────────────────────────
Presenter: "这是 A3——一个 AI 驱动的个性化学习系统。
不是录播课程，不是通用 AI 聊天，而是一个由 9 个
AI Agent 组成的教学团队。"

Screen: 展示 Landing page，点击 "免费开始"

⏱️ 0:30 — PROFILE CREATION
─────────────────────────
Presenter: "我扮演一个想学 Python OOP 的大三学生。"

输入: "我大三，学过 Python 基础，想深入学 OOP。
喜欢看代码例子 + 动手写，数学一般。"

Screen: ProfileAgent 实时分析 → 6 维画像生成
展示: 画像雷达图 + 各维度解释

⏱️ 1:15 — LEARNING PLAN
─────────────────────────
Presenter: "A3 的 PlannerAgent 根据我的画像，
自动生成了个性化学习路径。"

Screen: 3 层学习路径展开
- Chapter 1: OOP 基础回顾 (2h, 根据画像跳过基础)
- Chapter 2: 类与对象深入 (3h)
- Chapter 3: 继承与多态 (4h, 核心)

⏱️ 1:45 — RESOURCE GENERATION
─────────────────────────
Presenter: "点击开始学习，ResourceGenerationAgent
生成了 5 种学习资源。"

Screen: 资源卡片依次出现
📄 讲义 (15min read)
🧠 思维导图 (可交互)
✏️ 练习题 (自动生成)
💻 CodeLab (浏览器内写代码)
📖 拓展阅读 (推荐 3 篇论文)

点击 CodeLab → 展示代码编辑 + 运行

⏱️ 3:00 — TUTOR INTERACTION
─────────────────────────
Presenter: "学习过程中遇到问题？直接问 TutorAgent。
注意——它会用我的学习风格来回答。"

输入: "我不太理解多态的实际应用场景"

Screen: TutorAgent 流式回复 (token-by-token)
→ "想象你有个 Animal 基类..." (类比风格, 适配 visual_dominant)
→ 代码例子自动适配 beginner 难度
→ 追问: "你能用自己的话解释吗？"

⏱️ 4:00 — EVALUATION
─────────────────────────
Presenter: "学完一节课，EvaluationAgent 自动出题。"

Screen: 5 道 MCQ 测验
→ 答对 4 题 (80%)
→ 实时评分 + 弱项标注
→ "多态的实际应用" 标记为需要加强

⏱️ 4:30 — REFLECTION + CLOSE
─────────────────────────
Presenter: "ReflectionAgent 总结本次学习，更新画像。
下次学习时，路径会自动调整——多态部分增加练习，
跳过已掌握的继承基础。"

Screen: Progress Dashboard
→ Python OOP: 80% 完成
→ 下次推荐: Chapter 3 多态专项练习
→ 7 天学习趋势图

⏱️ 5:00 — END
```

### 10.2 Demo Technical Requirements

| Requirement | Solution | Status |
|:------------|:---------|:------:|
| 零外部 API 依赖演示 | 使用规则模式 (no LLM needed) | ✅ Rule-based fallback |
| 流式对话效果 | TutorAgent streaming | ✅ Phase 9.2 |
| 资源生成可视化 | 规则模式生成所有 6 种资源 | ✅ Phase 11 agent |
| 测验 + 评分 | EvaluationAgent | ✅ Phase 9.2 |
| 画像动态更新 | ReflectionAgent + StudentMemory | ✅ Phase 5 |
| Demo 数据预置 | demo_student.json 画像 + AI course KB | ✅ Exists |

### 10.3 Demo Talking Points

```
Technical Depth (评委技术视角):
  1. "9 个 Agent 通过 Veritas-Core RuntimeEngine 编排"
  2. "LLM 增强 + 规则降级，永不离线"
  3. "Streaming SSE 实现 token-by-token 教学"
  4. "SQLite WAL 模式支持并发学习会话"
  5. "Veritas-Core 独立 Framework，A3 是应用层"

Educational Innovation (评委教育视角):
  1. "6 维动态画像，比传统 LMS 更懂学生"
  2. "不是推荐系统，是多 Agent 协作教学"
  3. "自动出题 + 批改，教师效率提升 10x"
  4. "自适应难度：学生永远不会太难或太简单"
  5. "学习风格适配：视觉/代码/阅读 自动切换"

Product Vision (评委商业视角):
  1. "Free tier: 规则模式学习 Pro tier: LLM 增强"
  2. "教师端: 自动生成课件 + 题库"
  3. "企业端: 内部培训 AI 化"
  4. "Open Source: Veritas-Core (MIT) + A3 (AGPL)"
```

---

## 11. Summary

### 11.1 Product Specification Checklist

| Section | Content | Pages |
|:--------|:--------|:-----:|
| 1. Target Users | 4 personas + needs matrix | 1 |
| 2. User Journey | 6-stage lifecycle + first-time/returning flows | 2 |
| 3. AI Learning Workflow | Pedagogy model + session anatomy | 2 |
| 4. Student Profile | 6-dimension model + 3 creation methods | 1 |
| 5. Multi-Agent Flow | Orchestration map + data flow + A3Workflow | 2 |
| 6. Multimodal Resources | 8 resource types + card UI + trigger flow | 2 |
| 7. Evaluation Loop | Assessment cycle + score bands + progress tracking | 2 |
| 8. Product Architecture | Stack + client/server split | 2 |
| 9. UI Page Spec | 5 full-page wireframes (Landing/Dashboard/Learn/Quiz/Progress) | 5 |
| 10. Competition Demo | 5-min scenario + tech requirements + talking points | 3 |

### 11.2 Key Differentiators

| vs. Traditional LMS | vs. ChatGPT/Claude | vs. Other AI Tutors |
|:--------------------|:-------------------|:--------------------|
| 9 Agent 团队 vs 单一算法 | 结构化学习路径 vs 随意对话 | 资源自动生成 vs 手动创建 |
| 动态画像 vs 静态标签 | 6 维适配 vs 通用回答 | 开源可控 vs 黑盒 SaaS |
| 自动出题批改 vs 人工 | 离线可用 vs 必须联网 | 多模态 vs 纯文本 |
| 规则降级 vs 必须 API | 学生记忆 vs 无状态 | Veritas-Core 框架 vs 单体 |
