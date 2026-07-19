# A3-Agent v7.1.0 — Demo Recording Script

3-5 minute competition/portfolio demonstration video.

---

## Scene 1: Project Introduction (30s)

**Visual**: GitHub README or title card with A3 logo.

**Narration**:

> "A3 is a deployable offline multi-agent learning assistant. It combines 12 specialized AI agents that collaborate through an EventBus to deliver personalized education — from profile analysis to learning plan generation, resource creation, tutoring, and evaluation. All packaged as a double-click desktop application for Windows and Linux."

**Key Points**:
- 12 AI agents working collaboratively
- Multi-LLM provider support (DeepSeek, OpenAI, Spark)
- Cross-platform: Windows .exe, Linux, Docker, Streamlit Cloud
- 1154 tests, zero failures

---

## Scene 2: Input Learning Goal (30s)

**Visual**: Welcome page → main UI → type learning goal in Tab 1 (学习助手).

**Action**:
1. Launch A3-Agent (or open browser demo)
2. Click "🎭 Demo Mode" or configure provider
3. Enter learning goal: "帮我制定 Python 学习计划"
4. Click "🚀 开始分析"

**Narration**:
> "You describe what you want to learn in natural language. A3's agent pipeline takes over from there — no prompt engineering, no manual setup."

---

## Scene 3: Agent Pipeline Execution (60s)

**Visual**: Switch to "比赛演示" tab → click "运行完整 Pipeline" → show agent execution timeline.

**Action**:
1. Navigate to "比赛演示" tab
2. Click "运行完整 Pipeline"
3. Watch agents execute: ProfileAgent → PlannerAgent → ResourceAgent → EvaluationAgent → ReflectionAgent
4. Show the execution timeline with color-coded agent bars

**Narration**:
> "Behind the scenes, 5 core agents collaborate through an EventBus. ProfileAgent extracts a 6-dimension cognitive profile. PlannerAgent generates a structured learning path. ResourceAgent creates 7 types of multimodal resources. EvaluationAgent scores understanding. ReflectionAgent proposes improvements. Every step is traced and explainable."

**Key Screens to Capture**:
- Agent execution timeline
- Individual agent outputs
- Resource cards (documents, exercises, mindmaps)

---

## Scene 4: Evaluation & Explainability (45s)

**Visual**: Dashboard tab (仪表盘) — KPI cards + trust metrics.

**Action**:
1. Navigate to "仪表盘" tab
2. Show KPI cards: Correctness, Personalization, Coverage
3. Show explainability chain: "Why this plan was chosen"
4. Show trust metrics: ReviewGate confidence scores

**Narration**:
> "Every decision is transparent. The Dashboard shows real-time KPIs — correctness, personalization, coverage. Click any decision to see the explainability chain: which agents contributed, what data they used, and why they made that choice. ReviewGate provides confidence scoring for every output."

---

## Scene 5: Architecture Overview (30s)

**Visual**: Architecture tab (架构概览) — 5-layer diagram.

**Action**:
1. Navigate to "架构概览" tab
2. Scroll through the 5-layer architecture diagram
3. Highlight: Presentation → Agent Pipeline → Intelligence → Trust → Data

**Narration**:
> "A3 is built on a 5-layer architecture. The Presentation layer handles browser and desktop UI. The Agent Pipeline orchestrates 12 specialized agents. The Intelligence layer connects to any LLM provider via a factory pattern. Trust & Security includes ReviewGate quality gates and OS-level keyring encryption. Data is stored in SQLite with automatic schema migration."

---

## Scene 6: Cross-Platform Distribution (30s)

**Visual**: GitHub Release page → download Windows .exe → show Linux tar.gz.

**Action**:
1. Show GitHub Release page with 4 assets
2. Highlight: Windows .exe (54 MB, double-click, zero dependencies)
3. Highlight: Linux tar.gz (76 MB)
4. Show Docker pull command

**Narration**:
> "A3 ships as a double-click Windows executable with zero dependencies. Just download, extract, and run — no Python, no Docker, no configuration required. Linux, Docker, and Streamlit Cloud deployments are also available. All open source under MIT license."

---

## Recording Checklist

| # | Scene | Duration | Captured |
|:--|:------|:---------|:---------|
| 1 | Project Introduction | 30s | ⬜ |
| 2 | Input Learning Goal | 30s | ⬜ |
| 3 | Agent Pipeline Execution | 60s | ⬜ |
| 4 | Evaluation & Explainability | 45s | ⬜ |
| 5 | Architecture Overview | 30s | ⬜ |
| 6 | Cross-Platform Distribution | 30s | ⬜ |
| **Total** | | **~3.5 min** | |

---

## Technical Setup

### Screen Recording
- **Windows**: OBS Studio or Xbox Game Bar (Win+G)
- **Linux**: OBS Studio or SimpleScreenRecorder
- Resolution: 1920×1080 (or 2560×1600 if available)

### Audio
- Use external microphone (not laptop built-in)
- Record in quiet environment
- Speak at moderate pace (~150 words/min)

### Post-Production
- Add title cards between scenes
- Add subtitles (Chinese + English)
- Trim dead air / loading screens
- Background music: instrumental, low volume

---

## Tips

1. **Pre-configure** the API key before recording — avoid showing credentials
2. **Use Demo Mode** for zero-configuration recording
3. **Record cursor movements** — helps viewers follow along
4. **Zoom in** on key UI elements (timeline, dashboard cards)
5. **Keep edits minimal** — authenticity > polish
