# Screenshot Guide — Dashboard V2 Panels

> For competition slides and documentation
> Dashboard: `streamlit run web/app_v2.py`

---

## Screenshot Checklist

| # | Panel | What to Capture | Key Elements |
|:--|:------|:----------------|:-------------|
| 1 | 🏗️ System Overview | Full panel | 9-agent topology, memory stats, 4 metric cards |
| 2 | 🎯 Student Intelligence | Profile cards + mastery heatmap | 6-dim cards, red→green progress bars, weak points |
| 3 | 📜 Execution Timeline | Event table | Agent actions with reasoning_type icons, latency |
| 4 | 🔮 Decision Explainability | Explanation cards | Evidence chains, confidence scores, alternatives |
| 5 | 📊 Agent Evaluation | Per-agent score cards | 4-dim bar charts, overall scores, suggestions |
| 6 | 🔄 Self Improvement | Vertical timeline | Failure → Eval → Reflection → Experience → Strategy |

---

## How to Capture

```bash
# 1. Launch dashboard
cd projects/a3-multi-agent-system
streamlit run web/app_v2.py

# 2. Dashboard opens in browser at http://localhost:8501

# 3. Screenshot each panel (scroll down for all 6)
#    Linux: grim or spectacle
#    macOS: Cmd+Shift+4
#    Windows: Win+Shift+S

# 4. Save to docs/screenshots/
```

---

## Recommended Layout (for PPT Slide)

```
┌────────────────────────────────────────────┐
│  Slide 8: Dashboard Demo                    │
│                                             │
│  ┌─────────────┐  ┌─────────────────────┐  │
│  │ System      │  │ Student             │  │
│  │ Overview    │  │ Intelligence        │  │
│  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Agent       │  │ Decision            │  │
│  │ Timeline    │  │ Explainability      │  │
│  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Evaluation  │  │ Self Improvement    │  │
│  │ Dashboard   │  │ Timeline            │  │
│  └─────────────┘  └─────────────────────┘  │
└────────────────────────────────────────────┘
```

---

## Demo Mode Default State

When Dashboard V2 first opens (Demo Mode checked):

| Panel | What It Shows |
|:------|:--------------|
| System Overview | 9 agents (7 active, 2 idle), 42 traces, 12 lessons, avg score 82% |
| Student Intelligence | Xiao Lin: junior_dev, visual_dominant, code_sandbox. Mastery: llm_basics=92%, agent_loop=22%, eventbus_arch=8% |
| Execution Timeline | 12 events: ProfileAgent (5) → PlannerAgent (3) → ResourceRec (1) → Evaluator (1) → MetaReflector (1) |
| Decision Explainability | 8 decisions with confidence 85-95%. Course detection, mastery skip, weak point boost |
| Agent Evaluation | 4 agents scored. Profile=88%, Planner=82%, ResourceRec=78%, Content=67% |
| Self Improvement | 5-stage chain: failure→eval→reflection→experience→future_strategy |
