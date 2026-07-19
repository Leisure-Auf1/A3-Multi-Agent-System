# A3-Agent Roadmap

> A production-oriented multi-agent personalized learning assistant.

---

## v7.1 — Stable Release ✅

*Released July 2026*

- **12-agent pipeline**: Profile → Planner → Resource → Tutor → Evaluation → Reflection
- **5-layer architecture**: Presentation → Agent Pipeline → Intelligence → Trust → Data
- **7-tab Streamlit UI**: Learning Assistant, Student Profile, Learning Space, AI Settings, Demo, Dashboard, Architecture
- **Pluggable LLM providers**: DeepSeek, OpenAI, Spark, Mock (offline)
- **OS-level API key encryption**: Windows Credential Manager, Linux Secret Service, XOR fallback
- **Cross-platform distribution**: Windows .exe (54 MB), Linux tar.gz (76 MB), Docker, Streamlit Cloud
- **First-run onboarding**: guided provider setup + demo mode
- **1154 tests**: zero failures, ~7s suite
- **Technical blog**: 6-part engineering deep-dive

---

## v7.2 — Planned: Advanced Agent Capability

*Target: Q3-Q4 2026*

### Tool Calling Integration
- Merge `feat/tool-calling` branch (725 lines of tested code)
- Web search via DuckDuckGo API
- Tool registry with permission gating
- TutorAgent tool-use loop

### LLM Provider Wiring Completion
- Wire `llm_provider` into TutorAgent and EvaluationAgent API endpoints
- Merge from `feat/python-curriculum-kb` branch

### Multimodal Input
- Image upload support for learning context
- Screenshot-based Q&A
- Document OCR integration

### Enhanced Memory
- Vector-based semantic memory (migrate from TF-IDF to embeddings)
- Cross-session knowledge retention improvements
- Memory visualization dashboard

### Quality of Life
- Streaming response in all agent outputs
- Progress indicators for long-running pipelines
- Error recovery with checkpoint/resume

---

## v8.0 — Vision: Community & Ecosystem

*Long-term direction — not committed*

### Plugin System
- Community-contributed agents via plugin interface
- Agent marketplace / registry
- Custom resource generators

### Multi-User Collaboration
- Group learning sessions
- Teacher dashboard with student analytics
- Collaborative learning paths

### Platform Expansion
- macOS native .app build
- Mobile companion (PWA or native)
- Offline-first mode with local LLM support (Ollama, llama.cpp)

### AI Advancements
- Agent self-improvement loops
- Automated curriculum generation from any knowledge domain
- Multi-modal RAG (text + image + code)

### Ecosystem
- SDK for custom agent development
- Documentation platform (tutorials, API reference, examples)
- Community forum / Discord

---

## Non-Goals

The following are explicitly out of scope for A3-Agent:

- Real-time video/audio processing
- Social networking features
- LMS (Learning Management System) integration
- Enterprise SSO / SAML
- Monetization / paid features

---

## Contribution

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development setup and PR process.

Feature requests and bug reports: [GitHub Issues](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/issues)

---

*Last updated: July 2026*
