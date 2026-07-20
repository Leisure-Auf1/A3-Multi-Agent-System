# A3 — Changelog

---

## v1.0.0 (2026-07-20) — First Stable Release 🎉

### Production Hardening (Phase 10.4)
- **Security**: v1 routes authentication retrofit, 33 security tests
- **Persistence**: Full lifecycle verified (register→login→run→logout→login), 40 persistence tests
- **UI**: 6-tab product dashboard, onboarding, pipeline visualization, artifact browser, dark theme, 54 UI tests
- **Documentation**: Getting Started, Installation, FAQ, Architecture, API Reference, Demo Script
- **Release Engineering**: Linux PyInstaller spec, smoke tests, verification script

### Release Candidate (Phase 11)
- Build: Windows `.exe`, Linux binary, Docker multi-arch
- 10/10 verification checks passed
- 7/7 user journey steps validated
- Cold startup <100ms

### Tests
- **2661 tests, 0 failures** (up from 2512 in v7.1.0, +149)

---

## v7.1.1 (2026-07-20) — Production Hardening

### Security
- v1 routes now require authentication (7 endpoints retrofitted with `require_auth`)
- Deprecation headers added (`X-Deprecated-API`, `Sunset: 2026-09-01`)
- 33 new security tests (unauthorized, permission, token budget, multi-user isolation)

### Persistence
- Full lifecycle verified: Register → Login → Run → Logout → Login → Restore
- 40 persistence tests (user, profile, history, artifacts, memory, restart simulation)
- Persistence matrix documented: SQLite + Filesystem, all user-isolated

### UI Polish
- 6-tab product dashboard (Dashboard, Learning, History, Workspace, Profile, Settings)
- First-launch onboarding gate
- Pipeline progress visualization (EventBus-driven, 7-stage progress bar)
- Artifact browser with preview and download
- Dark professional theme system
- 54 UI tests

### Documentation
- README overhauled (v7.1.1, 2640 tests)
- New user docs: Getting Started, Installation, FAQ
- New developer docs: Architecture, API Reference
- New release docs: Changelog, Release Checklist
- Demo script for presentations

### Tests
- **2640 tests, 0 failures** (up from 2512 in v7.1.0)

---

## v7.1.0 (2026-07-19) — Runtime Consolidation

- Unified `POST /api/v2/learning/run` pipeline endpoint
- `PipelineExecutor` removed (duplicate runtime)
- `LearningPipelineService` wraps `A3Workflow` with auth chain
- Auth → Permission → TokenBudget → Pipeline path enforced
- 2512 tests, 0 failures

---

## v7.0.0 (2026-07-17) — Platform Release

- Multi-user platform with auth (register/login/logout)
- JWT-like token auth with PBKDF2-SHA256
- Role-based permissions (free/pro/teacher/admin)
- SQLite database for users, sessions, profiles, records
- Token budget enforcement
- Docker support
- Desktop builds (Windows `.exe`, Linux binary)
- 2400+ tests

---

## v6.0.0 (2026-07-14) — Multi-Agent Core

- 7-agent A3Workflow pipeline
- ProfileAgent, PlannerAgent, ContentGeneratorAgent, ResourceAgent
- ReviewGate, ReflectionAgent, MemoryManager
- EventBus + TraceCollector
- Streamlit V1 interactive pipeline
- 1800+ tests

---

## v5.0.0 (2026-07-10) — Foundation

- Initial multi-agent architecture
- Veritas-Core memory system
- Basic pipeline with ProfileAgent + PlannerAgent
- 1000+ tests
