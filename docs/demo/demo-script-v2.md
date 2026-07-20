# A3 Demo Script v2 — Production Demo (Phase 18)

> **Duration:** 5 minutes
> **Setup:** Fresh install, no prior data, no API key

---

## Fast Path: 30-Second Quick Demo

| Time | Action | What Viewer Sees |
|------|--------|-----------------|
| 0:00 | Open app | Onboarding page → 🎭 "Try Demo" |
| 0:05 | Guest login | "Continue as Guest" → Dashboard |
| 0:10 | Click goal | 🎯 "Learn Python basics" → Learning tab |
| 0:15 | Run pipeline | 7 agents execute in ~600ms |
| 0:25 | Results | Plan (3 nodes) + Content + AI Execution Card |
| 0:30 | Done | "Pipeline complete" |

---

## Full Demo: 8 Scenes (5 minutes)

### Scene 1: Onboarding (30s)

```
1. Open app → A3 onboarding screen
2. "Welcome to A3" — hero + feature cards
3. Click 🎭 "Try Demo" — no API key needed

Key point: Zero-config demo — 2 clicks to start
```

### Scene 2: Dashboard (30s)

```
1. Guest login → "Continue as Guest"
2. Dashboard shows:
   🎭 Demo Mode banner
   📊 Stats row: Sessions, Avg Score, Time, Tokens
   🧠 AI Memory card: Mastered Concepts, Weak Areas, Sessions, Interactions
   🎯 "Try These": 3 clickable goal cards
   ✏️ Custom Goal input

Key point: 6-tab product UI, 3 clickable demo goals
```

### Scene 3: Run Learning Pipeline (1 min)

```
1. Click 🐍 "Learn Python basics"
2. Auto-jumps to Learning tab
3. Click 🚀 "Run Pipeline"
4. Watch progress bar: actual agent names from trace
   ✅ ProfileAgent — 15ms
   ✅ PlannerAgent — 120ms
   ✅ ContentGenerator — 450ms
   ✅ ResourceAgent — 30ms
   ✅ ReviewAgent — 25ms
   ✅ ReflectionAgent — 30ms
   ✅ Memory — 5ms
5. Pipeline complete in ~600ms

Key point: 7 agents, trace-driven progress, <1 second
```

### Scene 4: Pipeline Results (1 min)

```
Open each expander:

1. ⚡ AI Engine Details:
   engine=mockllm | model=mock-model-v1 | duration

2. 🤖 AI Execution Card:
   Provider: mockllm · Model: mock-model-v1
   Agents (LLM): 5  |  Agents (Rule): 2
   Shows which agents used AI vs rule logic

3. 🧠 "AI remembered this session" badge

4. 🗺️ Learning Plan: 3 nodes with concepts + hours

5. 📊 Quality Evaluation: score=90, passed

6. 💭 AI Reflection: summary + achievements + improvements

7. 📝 Generated Lesson: 3 chapters

8. 📚 Resources: recommended materials

Key point: Every agent's output visible, AI usage transparent
```

### Scene 5: Interactive Quiz (1 min)

```
1. Scroll to "✅ Interactive Quiz" section
2. Click "Verify Learning" → 3 questions generated
3. Answer each question → click "Submit Answers"
4. Score displayed: 100% (3/3)
5. 🏆 Mastered Topics: Python, Structured reasoning
6. 💡 Recommendations: "Explore advanced topics"

Key point: Full quiz loop — generate → answer → score → analysis
```

### Scene 6: History Replay (30s)

```
1. Go to 📜 History tab
2. Stats: Total Runs, Avg Score, Total Time
3. Expand latest pipeline run:
   📋 Session Replay
   - 🗺️ Learning Plan (3 nodes)
   - 📊 Evaluation (score=90)
   - 💭 AI Reflection (summary)
   - 📝 Generated Lesson (3 chapters)
   - 📚 Resources (1 item)
   - 🧠 AI remembered this session
   - 📂 View Workspace Artifacts

Key point: Every past session fully reconstructable
```

### Scene 7: Provider Settings (30s)

```
1. Go to ⚙️ Settings tab
2. 🚀 Production Models: 8 providers displayed
   🌊 DeepSeek  🤖 OpenAI  🧠 Claude  🔮 Gemini
   ☁️ Qwen     🌙 Kimi   🚀 Grok   ⭐ Spark
3. 🎭 Demo & Offline: Mock (Always On)
4. Provider selector → Model selector → API Key → Test → Save
5. Troubleshooting hints for failed connections

Key point: 8 LLM providers, test connection, error recovery
```

### Scene 8: Dashboard Recap (30s)

```
1. Return to 🏠 Dashboard
2. Recap all features seen:
   - 🧠 AI Memory with mastery tracking
   - 🎯 Goal suggestions for quick start
   - 🔒 Security (JWT auth, permissions, token budget)
   - 🖥️ Cross-platform (Win .exe, Linux, Docker, Streamlit)
3. Stats: 2857 tests, 0 failures

Key point: Production-quality AI learning platform
```

---

## Talking Points

| Topic | Key Stat |
|-------|----------|
| Tests | **2857 tests, 0 failures** |
| Agents | **7 specialized agents** in EventBus pipeline |
| Latency | **~600ms** pipeline execution |
| Providers | **8 LLM providers** configurable |
| AI Transparency | Per-agent execution card shows LLM vs rule |
| Demo | **Zero-config** — no API key, no install |
| History | Full session replay with 6 data sections |
| Memory | Learning profile across 6 cognitive dimensions |
| Platform | Windows `.exe` + Linux binary + Docker + Streamlit |

---

## Demo Environment Prep

```bash
# Clean state
rm -rf ~/.a3-agent/
rm -f storage/a3.db

# Launch
streamlit run web/app.py --server.port 8501
```

---

## What's New in v2 (Phase 18)

| Feature | v1 (Phase 10) | v2 (Phase 18) |
|---------|--------------|---------------|
| Demo goals | ❌ | ✅ 3 clickable cards |
| Provider badge | ❌ | ✅ Sidebar + Dashboard |
| AI Execution Card | ❌ | ✅ Per-agent LLM/rule display |
| Trace metadata | ❌ | ✅ `{source, provider, model, llm_used}` |
| History replay | ❌ | ✅ 6-section session replay |
| Memory dashboard | ❌ | ✅ Mastery + Weak Areas |
| Quiz + Reflection | ❌ | ✅ Full interactive loop |
| Progress accuracy | ❌ Hardcoded | ✅ Trace-driven agent names |
