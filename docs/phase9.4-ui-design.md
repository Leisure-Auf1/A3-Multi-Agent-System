# Phase 9.4 — Web Frontend Architecture

> **Version:** 1.0 | **Date:** 2026-07-17 | **Type:** UI Design  
> **Backend:** FastAPI v2 (chat, profile, learning, resources, evaluation)  
> **Frontend:** Streamlit (`web/app_v4.py`)  
> **Tests:** 1089

---

## 1. Frontend Architecture

### 1.1 File Layout

```
web/
├── app.py                    # HF Spaces launcher (delegates to app_v4)
├── app_v4.py                 # Main application entry (NEW)
├── app_legacy.py             # Old app_v3.py (preserved backward compat)
├── components/
│   ├── __init__.py
│   ├── auth.py               # Login/Register/Profile forms
│   ├── chat.py               # ChatGPT-style chat with streaming
│   ├── cards.py              # Resource card components
│   ├── sidebar.py            # Navigation sidebar + thread list
│   ├── progress.py           # Progress charts and stats
│   └── quiz.py               # Quiz interface
├── utils/
│   ├── api.py                # API client (httpx wrapper)
│   └── renderer.py           # Markdown + code highlighting
├── streaming.py              # SSE stream consumer
└── assets/
    └── style.css             # Custom styles
```

### 1.2 Component Tree

```
App (app_v4.py)
├── Sidebar
│   ├── UserInfo (avatar, name, tier)
│   ├── Navigation (Dashboard | Chat | Resources | Progress | Profile)
│   └── ThreadList (chat history)
├── Main Content (routed)
│   ├── DashboardView          # /dashboard
│   │   ├── WelcomeBanner
│   │   ├── ContinueLearning   # Resume last session
│   │   ├── ProgressOverview   # Charts
│   │   └── QuickActions       # New chat, new quiz
│   ├── ChatView               # /chat
│   │   ├── ChatMessages       # Scrollable message list
│   │   ├── MessageBubble      # Single message (user/assistant)
│   │   ├── ResourceCard       # In-chat resource cards
│   │   └── ChatInput          # Text input + send button
│   ├── ResourceView           # /resources
│   │   ├── ResourceTabs       # Tab selector by type
│   │   ├── ResourceCardGrid   # Card grid layout
│   │   └── CourseSelector     # Course picker dropdown
│   ├── QuizView               # /quiz
│   │   ├── QuizSetup          # Topic + difficulty selector
│   │   ├── QuizQuestion       # Single question + options
│   │   └── QuizResults        # Score + weak areas + recommendations
│   ├── ProgressView           # /progress
│   │   ├── ProgressCharts     # Learning charts
│   │   ├── WeakAreasList      # Areas needing work
│   │   └── LearningTimeline   # Session history
│   └── ProfileView            # /profile
│       ├── ProfileEdit        # Edit student profile
│       └── AccountSettings    # Email, password, tier
└── AuthGate (login/register modal)
    ├── LoginForm
    ├── RegisterForm
    └── GuestButton
```

---

## 2. Page Designs

### 2.1 Auth (Login / Register)

```
┌──────────────────────────────────────────────────────┐
│                   🦊 A3 学习伙伴                       │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │                                              │   │
│  │           [登录]  [注册]                       │   │
│  │  ──────────────────────────────               │   │
│  │                                              │   │
│  │  📧 邮箱                                     │   │
│  │  ┌──────────────────────────────────────┐    │   │
│  │  │ user@example.com                     │    │   │
│  │  └──────────────────────────────────────┘    │   │
│  │                                              │   │
│  │  🔒 密码                                     │   │
│  │  ┌──────────────────────────────────────┐    │   │
│  │  │ ●●●●●●●●                             │    │   │
│  │  └──────────────────────────────────────┘    │   │
│  │                                              │   │
│  │  ┌──────────────────────────────────────┐    │   │
│  │  │          登  录                       │    │   │
│  │  └──────────────────────────────────────┘    │   │
│  │                                              │   │
│  │  或以游客身份 [快速体验 →]                     │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

### 2.2 Dashboard

```
┌──────────────────────────────────────────────────────┐
│  A3 │ 📊 仪表盘  💬 对话  📚 资源  ✏️ 测验  📈 进度 │
├────────────┬─────────────────────────────────────────┤
│            │  👋 欢迎回来，Xiao Lin！                  │
│  📁 Python │                                         │
│  📁 ML     │  ┌──────────────────────────────────┐   │
│  📁 Algo   │  │ 🔥 连续学习 5 天                   │   │
│            │  │ 本周: 8.5h · 23 题 · 12 概念       │   │
│  ──────    │  └──────────────────────────────────┘   │
│  ⚙️ 设置   │                                         │
│            │  📍 继续学习                              │
│            │  ┌──────────────────────────────────┐   │
│            │  │ 📄 Python OOP — Chapter 4         │   │
│            │  │ 上次学到: 继承与多态 · 80% 完成     │   │
│            │  │ [继续学习 →]  [重新测验 →]         │   │
│            │  └──────────────────────────────────┘   │
│            │                                         │
│            │  📊 课程进度                              │
│            │  ┌──────────────────────────────────┐   │
│            │  │ Python      ████████████░░░  80% │   │
│            │  │ ML Basics   ████████░░░░░░░  50% │   │
│            │  │ Algorithms  ██░░░░░░░░░░░░░  10% │   │
│            │  └──────────────────────────────────┘   │
└────────────┴─────────────────────────────────────────┘
```

### 2.3 Chat Interface (Streaming)

```
┌──────────────────────────────────────────────────────┐
│  💬 AI 导师对话                    📁 Python OOP     │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │ 🤖 Tutor                                    │   │
│  │                                              │   │
│  │ 上次我们学了继承的概念。现在让我们看一个实际     │   │
│  │ 的例子——多态在 Python 中的应用：                │   │
│  │                                              │   │
│  │ ```python                                     │   │
│  │ class Shape:                                  │   │
│  │     def area(self):                           │   │
│  │         raise NotImplementedError              │   │
│  │                                              │   │
│  │ class Circle(Shape):                          │   │
│  │     def __init__(self, radius):               │   │
│  │         self.radius = radius                  │   │
│  │     def area(self):                           │   │
│  │         return 3.14 * self.radius ** 2        │   │
│  │ ```                                           │   │
│  │                                              │   │
│  │ 你能看出 `area()` 方法的多态特性吗？            │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │ 👤 You                                       │   │
│  │ 同一个方法名，不同类有不同实现！                  │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │ 🤖 Tutor ████░░░░ (streaming...)             │   │
│  │ 完全正确！🎉 多态让代码更加灵活...               │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │ [输入你的问题...]                        [发送] │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ 📄 讲义   │ │ ✏️ 练习   │ │ 💻 实验   │            │
│  └──────────┘ └──────────┘ └──────────┘            │
└──────────────────────────────────────────────────────┘
```

### 2.4 Quiz Interface

```
┌──────────────────────────────────────────────────────┐
│  ✏️ Python OOP 测验               ⏱️ 02:35  📊 3/5  │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │                                              │   │
│  │  第 3 题                                     │   │
│  │                                              │   │
│  │  在 Python 中，以下哪个是正确的继承写法？       │   │
│  │                                              │   │
│  │  ┌──────────────────────────────────────┐    │   │
│  │  │ ○  class Dog(Animal)                 │    │   │
│  │  └──────────────────────────────────────┘    │   │
│  │  ┌──────────────────────────────────────┐    │   │
│  │  │ ○  class Dog extends Animal          │    │   │
│  │  └──────────────────────────────────────┘    │   │
│  │  ┌──────────────────────────────────────┐    │   │
│  │  │ ●  class Dog inherits Animal         │    │   │
│  │  └──────────────────────────────────────┘    │   │
│  │  ┌──────────────────────────────────────┐    │   │
│  │  │ ○  Dog = inherit(Animal)             │    │   │
│  │  └──────────────────────────────────────┘    │   │
│  │                                              │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│                    [上一题]  [下一题 →]                │
│                                                      │
│  ─────────────────────────────────────────────       │
│  进度: ●●●○○                                        │
└──────────────────────────────────────────────────────┘
```

### 2.5 Quiz Results

```
┌──────────────────────────────────────────────────────┐
│  ✏️ 测验结果 — Python OOP                             │
├──────────────────────────────────────────────────────┤
│                                                      │
│          ┌────────────────────────┐                  │
│          │                        │                  │
│          │       🎉  80%          │                  │
│          │      4 / 5 正确        │                  │
│          │                        │                  │
│          └────────────────────────┘                  │
│                                                      │
│  🟢 已掌握:                                           │
│  • 类与对象 (2/2)                                     │
│  • 继承语法 (2/2)                                     │
│                                                      │
│  🟡 需要复习:                                          │
│  • 多态的应用场景 (0/1)                                │
│                                                      │
│  📝 学习建议:                                          │
│  • 完成 "多态实战" CodeLab                             │
│  • 复习 Chapter 4.3                                   │
│                                                      │
│  [返回仪表盘]  [重新测验]  [查看详解]                   │
└──────────────────────────────────────────────────────┘
```

### 2.6 Progress Dashboard

```
┌──────────────────────────────────────────────────────┐
│  📈 学习进度                                          │
├──────────────────────────────────────────────────────┤
│                                                      │
│  📅 学习日历                                          │
│  ┌──────────────────────────────────────────────┐   │
│  │ 一   二   三   四   五   六   日               │   │
│  │ 🟢  🟢  🟢  ⚪  🟢  🟢  ⚪                  │   │
│  │ 2h  1h  3h  0   1h  1h  0                   │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  📊 课程进度                    🎯 掌握度趋势           │
│  ┌────────────────────┐    ┌────────────────────┐   │
│  │ Python ████████ 80%│    │ 100%      ╭──╮     │   │
│  │ ML     ████░░ 50% │    │  80%    ╭─╯  ╰─╮  │   │
│  │ Algo   ██░░░░ 20% │    │  60%  ╭─╯      ╰─ │   │
│  └────────────────────┘    │      └──────────── │   │
│                            └────────────────────┘   │
│                                                      │
│  📝 学习统计                                          │
│  ┌──────────────────────────────────────────────┐   │
│  │ 总学习时长: 32.5h  │  完成练习: 87 题          │   │
│  │ 掌握概念: 45 个     │  平均正确率: 78%           │   │
│  │ 连续学习: 5 天      │  活跃课程: 3 门            │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  🎯 推荐下一步                                         │
│  • ML: Chapter 3 — 监督学习 (建议今天完成)             │
│  • Python: 复习多态 (上次错误 1 题)                    │
└──────────────────────────────────────────────────────┘
```

---

## 3. API Integration

### 3.1 API Client (`web/utils/api.py`)

```python
class A3Client:
    """HTTP client for A3 v2 API."""
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base = base_url
        self.token: Optional[str] = None

    def set_token(self, token: str): ...
    def register(self, email, password, name) -> dict: ...
    def login(self, email, password) -> dict: ...
    def guest(self, name="Guest") -> dict: ...
    def chat_message(self, msg, thread_id=None, topic="") -> dict: ...
    def chat_stream(self, msg, thread_id=None) -> Iterator[str]: ...
    def get_threads(self) -> list: ...
    def get_profile(self) -> dict: ...
    def update_profile(self, profile: dict) -> dict: ...
    def assess_profile(self, text: str) -> dict: ...
    def generate_plan(self, goal: str) -> dict: ...
    def get_learning_history(self) -> list: ...
    def get_learning_stats(self) -> dict: ...
    def generate_resources(self, topic, concepts, types) -> list: ...
    def generate_quiz(self, topic, num=5) -> dict: ...
    def score_quiz(self, answers, topic) -> dict: ...
```

### 3.2 SSE Streaming Consumer

```python
# web/streaming.py
def consume_sse(url: str, token: str, on_token, on_done, on_error):
    """
    Consume SSE stream from /api/v2/chat/stream.
    Calls on_token(text) for each chunk, on_done() on [DONE].
    """
    headers = {"Authorization": f"Bearer {token}", "Accept": "text/event-stream"}
    with httpx.stream("POST", url, json=payload, headers=headers) as resp:
        for line in resp.iter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                if data == "[DONE]":
                    on_done()
                elif "token" in data:
                    on_token(data["token"])
```

### 3.3 Page → API Mapping

| UI Page | API Calls |
|:--------|:----------|
| Login | `POST /api/v2/auth/login` |
| Register | `POST /api/v2/auth/register` |
| Dashboard | `GET /api/v2/learning/stats` |
| Chat | `POST /api/v2/chat/stream`, `GET /api/v2/chat/threads` |
| Resources | `POST /api/v2/resources/generate`, `GET /api/v2/resources/courses` |
| Quiz | `POST /api/v2/evaluation/quiz/generate`, `POST /api/v2/evaluation/quiz/score` |
| Progress | `GET /api/v2/learning/history`, `GET /api/v2/learning/stats` |
| Profile | `GET /api/v2/profile`, `PUT /api/v2/profile`, `POST /api/v2/profile/assess` |

---

## 4. Key Design Decisions

### 4.1 Streamlit vs. React

```
Decision: Streamlit for Phase 9.4
Rationale:
  ✅ Zero frontend build tooling (no npm, webpack, etc.)
  ✅ Python-only stack → single developer can build full product
  ✅ Streamlit's native components cover 90% of UI needs
  ✅ Fast iteration (hot reload, no compile step)
  ⚠️ Limitation: Not suitable for production scale (use React/Svelte for v2)
```

### 4.2 State Management

```
Streamlit session_state for:
  - auth_token
  - current_thread_id
  - current_user
  - cached profile
  - cached resources
  - quiz state (current question, answers, results)
```

### 4.3 Responsive Layout

```
Desktop (≥1024px):
  [Sidebar 280px] [Main Content flex]

Tablet (768-1023px):
  [Hamburger menu] [Main Content full]

Mobile (<768px):
  [Main Content full, bottom nav]
  Sidebar becomes overlay
```

---

## 5. Implementation Plan

### 5.1 File Creation Order

```
1. web/utils/api.py          # API client
2. web/utils/renderer.py     # Markdown + code renderer
3. web/streaming.py          # SSE consumer
4. web/components/auth.py    # Login/Register forms
5. web/components/sidebar.py # Navigation
6. web/components/chat.py    # Chat UI with streaming
7. web/components/cards.py   # Resource cards
8. web/components/quiz.py    # Quiz UI
9. web/components/progress.py# Progress charts
10. web/app_v4.py            # Main app (wires everything)
```

### 5.2 Test Plan (15+ tests)

```
tests/test_phase9_ui.py:
  - test_api_client_register_login
  - test_api_client_chat_message
  - test_api_client_stream_consumer
  - test_renderer_markdown_to_html
  - test_renderer_code_highlighting
  - test_renderer_math_rendering
  - test_chat_component_renders_messages
  - test_resource_card_renders_types
  - test_quiz_flow_complete
```

---

## 6. Summary

| Layer | Status | Files | Tests |
|:------|:------:|:------|:-----:|
| API v2 routes | ✅ Built | 6 files | 25 |
| UI components | 📋 Spec | 10 files planned | 15+ planned |
| Integration | ✅ API tested | Full user flow test | 1 e2e |

**Product API endpoints:** 20 endpoints across chat, profile, learning, resources, evaluation.
**UI pages:** 6 pages (Auth, Dashboard, Chat, Resources, Quiz, Progress).
