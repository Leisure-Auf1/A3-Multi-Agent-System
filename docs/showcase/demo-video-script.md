# A3-Agent Demo Video Script (3-5 minutes)

## Pre-recording Checklist

- [ ] Start with clean config: `rm -f ~/.a3-agent/config/llm.json`
- [ ] Kill any running Streamlit/FastAPI processes
- [ ] Open terminal + Chrome side by side
- [ ] Screen recording: OBS / GNOME Screen Recorder / QuickTime
- [ ] 1920×1080 resolution, 30fps
- [ ] Microphone: USB headset (no background noise)
- [ ] Timer visible on secondary monitor

---

## Scene 1: Opening Hook (0:00–0:20)

**Visual**: Terminal → `streamlit run app.py` → browser opens

**Narration**:
> "A3 is a multi-agent AI learning system. Students describe what they want to learn in natural language, and a team of 12 AI agents generates personalized learning paths, resources, and evaluations. Let me show you how it works."

**Action**: Type `streamlit run app.py` in terminal, wait for browser.

---

## Scene 2: First-Run Welcome (0:20–0:50)

**Visual**: Welcome page with two buttons

**Narration**:
> "On first launch, A3 detects no configuration and shows this Welcome page. Users can set up their AI provider or jump straight into Demo mode — no API key required."

**Action**: Click "🎭 先体验 Demo" → enter main UI.

---

## Scene 3: Competition Demo (0:50–1:40)

**Visual**: 🏆 比赛演示 tab → clicking Run → agent timeline appears

**Narration**:
> "For competitions, we have a one-click demo. It runs the full 6-agent pipeline with mock providers — no API key, no network, no configuration. Profiling, planning, resource recommendation, evaluation, and reflection happen in under a second."

**Action**: Click 🏆 比赛演示 → "🚀 运行完整 Pipeline" → timeline bars animate.

---

## Scene 4: Architecture Overview (1:40–2:20)

**Visual**: 🏗️ 架构概览 tab — scroll through the 5-layer diagram

**Narration**:
> "A3 has a 5-layer architecture. The Presentation layer handles UI and API. The Agent layer runs 12 specialized agents through an EventBus — not single LLM calls. The Intelligence layer provides LLM abstraction, RAG retrieval, and memory management. The Trust layer enforces quality through ReviewGate. And the Data layer uses SQLite for persistence."

**Action**: Click 🏗️ 架构概览 → scroll from top to bottom.

---

## Scene 5: Dashboard & Trust (2:20–2:50)

**Visual**: 🎯 仪表盘 tab — KPI cards + explainability chain

**Narration**:
> "Every pipeline run produces traceable metrics. The dashboard shows agent execution time, success rates, evaluation scores, and confidence. The explainability chain traces every decision from input to output. ReviewGate scores 92% correctness, 85% personalization."

**Action**: Click 🎯 仪表盘 → point to KPI cards → scroll to explainability chain.

---

## Scene 6: Student Profile (2:50–3:20)

**Visual**: 👤 学习画像 tab — 6-dimension radar + detail cards

**Narration**:
> "The ProfileAgent extracts 6 dimensions from natural language — knowledge base, cognitive style, error patterns, learning pace, interaction preference, and frustration threshold. This drives personalization across the entire pipeline."

**Action**: Click 👤 学习画像 → scroll through dimension cards.

---

## Scene 7: LLM Configuration (3:20–3:50)

**Visual**: ⚙️ AI模型设置 tab → select DeepSeek → enter API key

**Narration**:
> "A3 supports multiple LLM providers — DeepSeek, OpenAI, Spark — through a unified ProviderFactory. API keys are stored in the OS credential store, never in plaintext. When no key is available, the system falls back to mock mode transparently."

**Action**: Click ⚙️ AI模型设置 → select DeepSeek → show keyring security note.

---

## Scene 8: Closing (3:50–4:00)

**Visual**: Return to 🏠 学习助手

**Narration**:
> "A3-Agent v7.1.0: 12 agents, 5 layers, 1154 tests, 0 failures. Competition-ready. Open source on GitHub. Thank you."

**Action**: Show README with badges on GitHub.

---

## Post-production

- Trim dead air to keep under 5 minutes
- Add subtitle captions for accessibility
- Add chapter markers for each section
- Upload to YouTube/Vimeo as unlisted for review

## Alternative: Quick 2-Minute Version

| Time | Scene |
|:-----|:------|
| 0:00–0:15 | Opening: start app, welcome page |
| 0:15–0:45 | Competition Demo: one-click pipeline |
| 0:45–1:15 | Architecture: 5-layer diagram |
| 1:15–1:40 | Dashboard: metrics + trust |
| 1:40–1:55 | Settings: provider switch |
| 1:55–2:00 | Closing: repo + contact |
