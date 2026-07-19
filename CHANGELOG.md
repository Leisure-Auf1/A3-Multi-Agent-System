# Changelog

All notable changes to the A3-Multi-Agent-System.

---

## [v7.1.0] — 2026-07-19

### Added
- **System keyring integration** for API key storage
  - Windows: Credential Manager · Linux: Secret Service · macOS: Keychain
  - Automatic fallback to local XOR encryption (headless/server)
- **Provider capability detection** (`validate_provider_capability`)
  - Validates API key, provider, model, and chat completion before saving
- **First-run onboarding wizard** (Phase 5.0)
  - Welcome page with A3 introduction + provider setup wizard
  - "Demo mode" skip option
- **User-friendly error messages** (Phase 5.0)
  - Chinese titles/reasons/solutions for 8 error categories
- **Linux distribution package builder**
- **Demo freeze fixtures** (sample profile, trace, resources)
- **Competition demo UI** (Phase 8.0/9.0)
  - Architecture overview page with 5-layer diagram
  - Demo dashboard: KPI cards, agent timeline, explainability chain
  - One-click competition demo mode (auto-loads fixtures, no API key)
  - Competition docs: architecture, agent design, memory/RAG, evaluation, demo script, benchmark
  - Competition-ready README with badges and benchmark table
  - Release checklist (cross-platform validation)
- **Database migration fix**
  - Fixed `is_guest` column missing in existing databases
  - Tests: 1154/1154 passed (resolved 65 pre-existing failures)

### Changed
- **Version**: 7.0.0 → 7.1.0
- **Dependencies**: Added `keyring>=25.0.0`
- **README**: Competition-ready with badges, architecture diagram, benchmark
- **Documentation**: 8 new docs in `docs/competition/` and `docs/`
- **Streamlit UI**: 7 tabs (was 4)

### Fixed
- SQLite schema migration: `ALTER TABLE users ADD COLUMN is_guest`
- Backward compatible: existing XOR-encrypted keys still decrypt

### Architecture
- 0 changes to `src/agents/`, `src/workflow/`, Veritas-Core

---

## [v7.0.0] — 2026-07-19

### Added
- **User LLM configuration layer** (Phase 4.0)
  - File-based config with encrypted API key storage
  - Settings API + Streamlit AI settings tab
- ProviderFactory: user config > env > mock > rule priority

---

## [v6.x] — 2026-06 to 2026-07

### Added
- Multimodal generation (7 resource types)
- Product API v2 + Streamlit UI v3
- TutorAgent (streaming chat) + EvaluationAgent (quiz/scoring)
- Data layer (auth, SQLite, learning records)
- Repository independence (Veritas-Core extraction)
- Runtime engine, SDK, recovery, lifecycle, CLI

---

## Legend

| Icon | Meaning |
|:-----|:--------|
| ✅ | Merged to main |
| 🔴 | In review |
