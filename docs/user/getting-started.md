# Getting Started with A3

> **5 minutes to your first AI-powered learning experience.**

---

## Step 1: Launch A3

### Option A: Streamlit Cloud (fastest)

Visit [a3-agent.streamlit.app](https://a3-agent.streamlit.app) — no installation needed.

### Option B: Run Locally

```bash
git clone https://github.com/Leisure-Auf1/A3-Multi-Agent-System.git
cd A3-Multi-Agent-System
pip install -r requirements.txt
streamlit run web/app.py
```

---

## Step 2: Create an Account

1. The app opens with an **onboarding** screen — click **Get Started**
2. On the **Auth Gate**, choose **Register**
3. Enter your email and a password (min 4 characters)
4. Click **Register** — you're now logged in

> **Demo Mode**: No API key needed. A3 runs with rule-based agents only.

---

## Step 3: Run Your First Learning Task

1. Go to the **Dashboard** tab
2. In the **Quick Start** box, describe what you want to learn:

   ```
   I'm a CS student with basic Python. I want to understand 
   multi-agent AI systems. I learn best with visuals and 
   hands-on coding exercises.
   ```

3. Click **🚀 Start Learning**

The pipeline runs through 7 stages:
- 🧠 ProfileAgent analyzes your learning style
- 🗺️ PlannerAgent builds a personalized learning path
- 📝 ContentGenerator creates materials for your level
- 📚 ResourceAgent finds matching resources
- 🔍 ReviewGate checks quality
- 💭 ReflectionAgent reflects on the plan
- 💾 Memory persists everything for next time

---

## Step 4: Explore Your Results

After the pipeline completes:

| Tab | What You See |
|:----|:-------------|
| **Learning** | Your learning plan with nodes, agent execution trace, quality score |
| **History** | All past runs with scores and durations |
| **Workspace** | Generated artifacts — plans, resources, evaluations, downloadable |
| **Profile** | Your cognitive profile across 6 dimensions |

---

## Step 5: Configure LLM (Optional)

For AI-powered content generation:

1. Go to **Settings** tab
2. Select a provider (DeepSeek, OpenAI, Spark)
3. Enter your API key
4. Click **Test Connection**

Now your pipeline uses LLM for richer content generation!

---

## Next Steps

- 📖 [Full Installation Guide](installation.md)
- ❓ [FAQ](faq.md)
- 🎬 [Demo Script](../demo/demo-script.md)
- 🏗️ [Architecture](../developer/architecture.md)
