# Changelog

All notable changes to the A3-Multi-Agent-System.

---

## [v7.1.0] — 2026-07-19

### Added
- **System keyring integration** for API key storage
  - Windows: Credential Manager
  - Linux: Secret Service (GNOME Keyring / KDE Wallet)
  - macOS: Keychain
  - Automatic fallback to local XOR encryption (headless/server)
- **Provider capability detection** (`validate_provider_capability`)
  - Validates API key, provider availability, model, and chat completion before saving
- **First-run onboarding wizard** (Phase 5.0)
  - Welcome page with A3 introduction
  - Step-by-step provider setup: select → API key → test → save
  - "Demo mode" skip option for instant exploration
- **User-friendly error messages** (Phase 5.0)
  - Chinese error titles, reasons, and actionable solutions
  - Covers: auth, rate limit, quota, network, server errors
- **Linux distribution package builder** (`scripts/build-linux-package.sh`)
  - Creates `A3-Agent-linux-x64-v7.1.0.tar.gz` with self-contained launcher
- **Demo freeze fixtures** (`demo/fixtures/`)
  - Sample student profile, learning trace, generated resources
  - Stable deterministic data for competition demos
- **Windows validation checklist** (`docs/windows-validation-checklist.md`)
  - 23-step verification checklist for Windows .exe releases

### Changed
- **Version**: 7.0.0 → 7.1.0
- **Dependencies**: Added `keyring>=25.0.0`
- **README**: v7.1.0 badge, security note, phase table update
- ProviderFactory priority: `user config > env var > mock > rule`

### Fixed
- Backward compatible: existing XOR-encrypted API keys in llm.json still decrypt correctly
- Secret manager: added `delete_api_key()` for cleanup

### Architecture
- 0 changes to `src/agents/`
- 0 changes to `src/workflow/`
- 0 changes to Veritas-Core (external dependency)

---

## [v7.0.0] — 2026-07-19

### Added
- **User LLM configuration layer** (Phase 4.0)
  - File-based config: `~/.a3-agent/config/llm.json`
  - Windows: `%APPDATA%/A3-Agent/config/llm.json`
  - Provider selection: DeepSeek, OpenAI, Spark, Mock, Rule
  - Local API key encryption (XOR + base64)
  - Settings API: `GET/POST /api/v2/settings/llm`, `POST /api/v2/settings/test`
- **Streamlit AI settings tab** (⚙️ AI模型设置)
  - Provider selector with model presets
  - API key input (password-masked)
  - Test connection button with status display
  - First-launch demo mode notification

### Changed
- ProviderFactory: added user config priority layer
- `src/api/server.py`: includes settings_router
- `web/app_v3.py`: added 4th settings tab

---

## [v6.x] — 2026-06 to 2026-07

### Added
- **Phase 9.5**: Multimodal generation (7 resource types)
- **Phase 9.4**: Product API v2 + Streamlit UI v3
- **Phase 9.3**: Multimodal Gateway design
- **Phase 9.2**: TutorAgent (streaming chat) + EvaluationAgent (quiz/scoring)
- **Phase 9.1**: Data layer (auth, SQLite, learning records)
- **Phase 8.0**: Productization audit
- **Phase 7.0**: Repository independence (Veritas-Core extraction)
- **Phases 1–6**: Runtime engine, SDK, recovery, lifecycle, CLI

### Architecture
- 12-agent personalized learning pipeline
- Veritas-Core runtime framework
- Docker + Render deployment
- Windows .exe packaging

---

## Legend

| Icon | Meaning |
|:-----|:--------|
| ✅ | Merged to main |
| 🔴 | In review |
| 🟡 | In progress |
