# FAQ — A3 AI Learning Assistant

---

## General

**Q: What is A3?**

A3 is a multi-agent AI learning system. You describe what you want to learn in natural language, and a team of 7 specialized AI agents work together to profile you, build a personalized learning path, generate materials, and evaluate quality.

**Q: Do I need an API key?**

No. A3 works in **demo mode** with rule-based agents. An LLM API key (DeepSeek, OpenAI, Spark) enables richer content generation.

**Q: Is my data private?**

Yes. All data is stored locally on your machine — SQLite database under `~/.a3-agent/storage/a3.db` and workspace files under `~/.a3-agent/workspace/`. Nothing is sent to external servers unless you configure an LLM provider.

---

## Usage

**Q: How do I get started?**

See [Getting Started](getting-started.md). In 5 minutes: launch → register → describe your goal → get a personalized learning plan.

**Q: What should I write in the learning goal?**

Be specific about:
- Your current knowledge level
- What you want to learn
- Your preferred learning style

Example: *"I'm a CS student with basic Python. I want to understand multi-agent AI systems. I learn best with visuals and hands-on coding."*

**Q: How do I switch between tabs?**

Use the sidebar navigation: Dashboard, Learning, History, Workspace, Profile, Settings.

**Q: Where are my generated files?**

In the **Workspace** tab. You can preview and download artifacts (learning plans, resource recommendations, evaluations).

**Q: Can I run multiple pipelines?**

Yes. Each run creates a separate learning record. Visit the **History** tab to see all past runs.

---

## Technical

**Q: What database does A3 use?**

SQLite (`storage/a3.db`). Tables: users, sessions, student_profiles, learning_records, chat_threads, chat_messages.

**Q: Where are artifacts stored?**

`~/.a3-agent/workspace/{user_id}/artifacts/` — organized by category (materials, ppt, images, videos).

**Q: How does authentication work?**

A3 uses token-based auth with PBKDF2-SHA256 password hashing. Tokens expire after 24 hours.

**Q: What Python version is required?**

Python 3.10 or later.

**Q: Can I run A3 on a server?**

Yes. The FastAPI backend runs on port 8000, Streamlit UI on port 8501. Use Docker for production deployment.

**Q: How do I run tests?**

```bash
make test
# 2640 tests, 0 failures
```

---

## Troubleshooting

**Q: "Module not found" error?**

Run: `pip install -r requirements.txt`

**Q: Streamlit port already in use?**

```bash
streamlit run web/app.py --server.port 8502
```

**Q: API key not working?**

1. Verify the key has not expired
2. Check your provider account has credits
3. Run **Test Connection** in Settings

**Q: Docker container won't start?**

Check port 8501 and 8000 are available. Use `-p 8502:8501` to change port.

**Q: How do I reset everything?**

```bash
rm -rf ~/.a3-agent/
rm -f storage/a3.db
```
