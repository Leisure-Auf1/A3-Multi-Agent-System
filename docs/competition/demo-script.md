# Competition Demo Script (5 Minutes)

## Pre-Demo Checklist

- [ ] Delete `~/.a3-agent/config/llm.json` (fresh start)
- [ ] Kill any running Streamlit/FastAPI processes
- [ ] Open terminal in `A3-Multi-Agent-System/`
- [ ] Ensure mock provider is default
- [ ] Have demo/fixtures/ verified with `python -c "import json; [json.load(open(f'demo/fixtures/{f}')) for f in ['sample_profile.json','learning_trace.json','generated_resources.json']]; print('OK')"`

---

## Minute 1: Architecture Overview (0:00–1:00)

**What to show**: README architecture diagram

**What to say**:
> "A3 is a 5-layer AI learning system. Students describe what they want to learn in natural language. Twelve specialized agents collaborate through an EventBus — not a single LLM call, but a real multi-agent pipeline."

**Demo action**:
1. Point to architecture diagram in README
2. Highlight: Agent Pipeline → Intelligence → Trust layers

**Transition**: "Let me show you the live system."

---

## Minute 2: Agent Pipeline Demo (1:00–2:00)

**What to show**: Competition Demo Tab execution

**Demo action**:
```bash
streamlit run app.py
# → Wait for browser to open
# → Click "🏆 比赛演示" tab
# → Click "🚀 运行完整 Pipeline"
```

**What to say**:
> "This runs 6 agents in sequence — Profile, Planner, Resource, Evaluation, Reflection — all with mock providers. No API key, no network, zero configuration. The entire pipeline completes in under a second."

**Expected output**: Agent timeline with bars, success marks, durations.

**Transition**: "Now let's look at the evaluation metrics."

---

## Minute 3: Evaluation & Trust (2:00–3:00)

**What to show**: Dashboard Tab

**Demo action**:
1. Click "🎯 仪表盘" tab
2. Show KPI cards (agent count, success rate, score)
3. Point to ReviewGate metrics: correctness 92%, personalization 85%

**What to say**:
> "Every agent output passes through our ReviewGate — a 3-tier quality system. AST audit, functional testing, and 4-dimensional scoring. We track correctness, personalization, explainability, and efficiency."

**Transition**: "And here's how students interact with the system."

---

## Minute 4: Student Experience (3:00–4:00)

**What to show**: Learning tabs (画像, 学习空间)

**Demo action**:
1. Click "👤 学习画像" → show 6-dimension profile
2. Click "📚 学习空间" → show learning path + resources
3. Click "🏗️ 架构概览" → show architecture flow

**What to say**:
> "The student profile is extracted automatically from natural language. Six dimensions — from knowledge base to frustration threshold. The learning path adapts to each student's cognitive style and pace."

**Transition**: "Finally, let me show how we handle real LLM integration."

---

## Minute 5: LLM Switch & Security (4:00–5:00)

**What to show**: Settings Tab + Provider Switch

**Demo action**:
1. Click "⚙️ AI模型设置"
2. Show provider selector (DeepSeek/OpenAI/Spark/Mock)
3. Mention: "API keys stored in OS keyring — Windows Credential Manager, Linux Secret Service"
4. (If time) Click "🏆 比赛演示" to re-run with demo data

**What to say**:
> "A3 works with multiple LLM providers. DeepSeek, OpenAI, Spark — all through our ProviderFactory abstraction. API keys are encrypted in the OS credential store, never in plaintext. And when no key is available, the system works fully offline with mock providers — perfect for demos, testing, and competition presentations."

**Closing**:
> "A3: 12 agents, 5 layers, 1154 tests, 100% pass rate. Competition-ready. Thank you."

---

## Backup Slides (if extra time)

### Technical Depth
- Show `docs/competition/agent-design.md` for agent communication patterns
- Show `tests/` directory — 1154 passing tests
- Show `src/config/secret_manager.py` — keyring integration

### Architecture Walkthrough
- Show `docs/competition/architecture.md`
- Point out: separation of concerns, provider abstraction, event-driven communication

### Benchmark
- Show `docs/competition/benchmark.md`
- Mock mode: ~500ms full pipeline
- LLM mode: ~2-5s with network

---

## Troubleshooting

| Problem | Fix |
|:--------|:----|
| Streamlit won't start | `kill $(lsof -t -i:8501)` |
| Port 8000 in use | `kill $(lsof -t -i:8000)` |
| Demo fixtures missing | Verify `demo/fixtures/*.json` exist |
| Onboarding wizard appears | Delete `~/.a3-agent/config/llm.json` |
| Slow pipeline | Switch to Mock mode in Tab 4 |
