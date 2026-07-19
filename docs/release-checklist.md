# Release Checklist — A3-Agent v7.1.0

Competition release validation across all platforms and modes.

---

## Windows (.exe)

- [ ] Clean Windows environment (no Python)
- [ ] Double-click `A3-Agent.exe` — launches without errors
- [ ] First-run wizard appears ("欢迎使用 A3 智能学习伙伴")
- [ ] Select "🎭 Demo Mode" — enters main UI
- [ ] All 7 tabs render correctly
- [ ] Competition demo runs with fixtures
- [ ] Close and re-open — wizard skipped (llm.json exists)
- [ ] Delete `%APPDATA%/A3-Agent/config/llm.json` — wizard reappears
- [ ] Configure DeepSeek/OpenAI — test connection works
- [ ] API key stored in Credential Manager (check with `cmdkey /list`)
- [ ] Streamlit UI responsive, no CSS breakage
- [ ] No console errors in background

## Linux (tar.gz)

- [ ] Extract `A3-Agent-linux-x64-v7.1.0.tar.gz`
- [ ] Run `./start.sh` — venv created automatically
- [ ] Welcome page appears
- [ ] Competition demo runs with fixtures
- [ ] API key stored in Secret Service (check with `secret-tool search service A3-Agent`)
- [ ] `make test` → 1154/1154 passed
- [ ] Build script: `bash scripts/build-linux-package.sh` produces valid package
- [ ] Package size < 50MB

## Docker

- [ ] `docker pull leisureauf1/a3-multi-agent-system:latest`
- [ ] `docker run -p 8000:8000 -p 8501:8501 ...`
- [ ] Streamlit accessible at http://localhost:8501
- [ ] FastAPI docs at http://localhost:8000/docs
- [ ] Health check: `curl http://localhost:8000/health` → 200
- [ ] All providers selectable in settings

## API Mode (Mock)

- [ ] `uvicorn src.api.server:app` — starts without errors
- [ ] `curl http://localhost:8000/health` → `{"status":"ok"}`
- [ ] `curl http://localhost:8000/api/v2/settings/llm` → mock provider info
- [ ] `POST /api/v2/settings/test` → 200 (mock succeeds)
- [ ] All 25 endpoints registered in `/docs`

## API Mode (Real LLM)

- [ ] Configure DeepSeek API key via `POST /api/v2/settings/llm`
- [ ] `POST /api/v2/settings/test` → `{"success":true,"latency":...}`
- [ ] Full pipeline via API produces LLM-quality output
- [ ] Streaming chat via SSE works

## Offline Demo

- [ ] Disconnect network
- [ ] Launch A3 (mock mode)
- [ ] Competition demo runs (6 agents, new fixtures)
- [ ] All tabs render (no external dependencies)
- [ ] Dashboard shows KPI metrics

## Demo Fixtures

- [ ] `demo/fixtures/sample_profile.json` — valid JSON
- [ ] `demo/fixtures/learning_trace.json` — 6 agent events
- [ ] `demo/fixtures/generated_resources.json` — 6 resources, 3 types
- [ ] Competition demo loads fixtures correctly
- [ ] Dashboard renders fixture data correctly

## Documentation

- [ ] README.md — professional, badges, architecture diagram
- [ ] CHANGELOG.md — v7.1.0 entry complete
- [ ] docs/competition/ — 5 docs present (architecture, agent-design, memory-rag, evaluation, demo-script)
- [ ] docs/windows-validation-checklist.md — 23 steps
- [ ] docs/release-checklist.md — this file

## Test Suite

- [ ] `make test` → 1154/1154 passed, 0 failures
- [ ] Provider tests: 57/57 passed
- [ ] Workflow integration: 14/14 passed
- [ ] API tests: 122/122 passed
- [ ] DB migration: no errors on existing databases

## Architecture Constraints

- [ ] `git diff --stat main -- src/agents/` → 0 changes
- [ ] `git diff --stat main -- src/workflow/` → 0 changes
- [ ] Veritas-Core unchanged (external dependency)

---

## Sign-off

| Role | Name | Date | Signature |
|:-----|:-----|:-----|:----------|
| Developer | | | |
| Reviewer | | | |
| Competition Lead | | | |
