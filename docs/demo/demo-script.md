# A3 Demo Script

> **Duration**: ~8 minutes
> **Setup**: Fresh install, no prior data

---

## Scene 1: First Launch (30s)

1. Open A3 — onboarding screen appears
2. "Welcome to A3 AI Learning Assistant" — read the intro
3. Click **🚀 Get Started**

> **Key point**: Zero-config — no API key needed.

---

## Scene 2: Create Account (30s)

1. On the auth screen, switch to **Register**
2. Enter `demo@example.com` / `demo1234`
3. Click Register — you're in!

> **Key point**: Simple registration with local storage.

---

## Scene 3: Dashboard (30s)

1. Dashboard shows stats (0 sessions, 0 tokens — fresh start)
2. Point out the sidebar: Dashboard, Learning, History, Workspace, Profile, Settings

> **Key point**: Clean product layout, 6 functional tabs.

---

## Scene 4: Run Learning Pipeline (2 min)

1. Go to **Dashboard** tab
2. In the Quick Start box, paste:

   ```
   I'm a CS student comfortable with Python basics. I want to 
   learn how multi-agent AI systems work. I learn best through 
   visual diagrams and hands-on coding exercises.
   ```

3. Click **🚀 Start Learning**

4. Watch the pipeline progress:
   - 🧠 ProfileAgent: "Analyzing your learning profile"
   - 🗺️ PlannerAgent: "Building learning path"
   - 📝 ContentGeneratorAgent: "Generating materials"
   - 📚 ResourceAgent: "Finding resources"
   - 🔍 ReviewAgent: "Quality review"
   - 💭 ReflectionAgent: "Reflecting on plan"
   - 💾 Memory: "Saving to memory"

5. Results appear:
   - Learning Plan with nodes
   - Agent Execution Trace (timeline)
   - Quality Evaluation score

> **Key point**: 7-agent pipeline with live progress. Rule-based (no LLM).

---

## Scene 5: Browse History (30s)

1. Go to **History** tab
2. One run visible with stats
3. "Total Runs: 1, Avg Score: 85, Total Time: 2min"

> **Key point**: All runs persisted across sessions.

---

## Scene 6: Browse Workspace (30s)

1. Go to **Workspace** tab
2. Category selector: Materials (selected)
3. List of generated files: profile, plan (JSON + Markdown), resources, evaluation
4. Expand a file → preview content
5. Click Download button

> **Key point**: Generated artifacts browsable and downloadable.

---

## Scene 7: Configure LLM (1 min)

1. Go to **Settings** tab
2. Select provider: **DeepSeek**
3. Enter API key (or skip if no key)
4. Explain: "With an API key, A3 uses LLM for richer content generation"
5. Test Connection

> **Key point**: LLM optional — demo mode works without it.

---

## Scene 8: Profile View (30s)

1. Go to **Profile** tab
2. 6 cognitive dimensions displayed:
   - Knowledge Base, Cognitive Style, Error Prone, Learning Pace, Interaction, Frustration
3. Memory stats: interactions, mastery concepts, sessions

> **Key point**: AI-generated learning profile with memory tracking.

---

## Wrap-up (30s)

1. Return to Dashboard
2. Recap: "In 8 minutes, we: created an account, ran a 7-agent learning pipeline, browsed history, downloaded artifacts, configured an LLM provider, and viewed our AI-generated learning profile."
3. "A3 — open-source, local-first, 2640 tests, zero-config demo."

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

## Talking Points

- **Local-first**: All data stored on your machine
- **Zero-config**: Demo mode works without any API key
- **7 agents**: Profile, Plan, Content, Resource, Review, Reflect, Memory
- **Product quality**: 6-tab UI, dark theme, onboarding, error handling
- **Test coverage**: 2640 tests, 0 failures
- **Cross-platform**: Windows `.exe`, Linux binary, Docker, Streamlit Cloud
