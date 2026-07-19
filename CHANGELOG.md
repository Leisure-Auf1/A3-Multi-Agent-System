# Changelog

All notable changes to the A3-Multi-Agent-System.

---

## [v7.1.0] — 2026-07-19 (Release)

🔗 [GitHub Release](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases/tag/v7.1.0)

### Added
- **System keyring integration** for API key storage (Windows Credential Manager, Linux Secret Service, macOS Keychain)
- **Provider capability detection** — validates API key, provider, model, and chat completion before saving
- **First-run onboarding wizard** with A3 introduction + provider setup flow
- **User-friendly Chinese error messages** covering 8 error categories with solutions
- **Linux distribution package** (`A3-Agent-v7.1.0-linux-x64.tar.gz`, 76 MB)
- **Competition demo UI**: architecture overview, dashboard with KPI cards, one-click pipeline
- **7-tab Streamlit UI**: 学习助手, 学习画像, 学习空间, AI模型设置, 比赛演示, 仪表盘, 架构概览
- **Demo freeze fixtures**: sample profile, learning trace, generated resources
- **Database migration fix**: `is_guest` column for existing databases (resolved 65 failures)
- **Release validation script** (`scripts/release_check.py`): 32-point automated check
- **User documentation**: INSTALL.md, USER_GUIDE.md, screenshots guide, Windows validation checklist

### Changed
- **Version**: 7.0.0 → 7.1.0
- **Dependencies**: Added `keyring>=25.0.0`
- **README**: Competition-ready with badges, architecture diagram, benchmark table
- **Documentation**: 12+ docs across `docs/competition/`, `docs/`, and `demo/fixtures/`

### Fixed
- SQLite schema migration: `ALTER TABLE users ADD COLUMN is_guest`
- Frozen binary `BUNDLE_ROOT`: use `sys._MEIPASS` for `--add-data` files
- Missing `desktop/` in `--add-data` for PyInstaller build

### Security
- API keys encrypted in OS credential store (keyring)
- Automatic fallback to XOR encryption when keyring unavailable
- `llm.json` permissions set to 0o600 (owner-only)

### Release Assets
| File | Size | SHA256 |
|:-----|:-----|:-------|
| `A3-Agent-v7.1.0-linux-x64.tar.gz` | 76 MB | `d0d8b88e...` |
| `A3-Agent-v7.1.0-win64.zip` | TBD | TBD |

### Architecture
- 0 changes to `src/agents/`, `src/workflow/`, Veritas-Core
- 1154/1154 tests passing (100%)

---

## [v7.0.0] — 2026-07-19

### Added
- User LLM configuration layer with encrypted API key storage
- Settings API (`/api/v2/settings/llm`, `/api/v2/settings/test`)
- Streamlit AI settings tab with provider/model selector
- ProviderFactory priority: user config > env > mock > rule

---

## [v6.x] — 2026-06 to 2026-07

### Added
- Multimodal generation (7 resource types)
- Product API v2 + Streamlit UI v3
- TutorAgent (streaming chat) + EvaluationAgent (quiz/scoring)
- Data layer (auth, SQLite, learning records)
- Repository independence (Veritas-Core extraction)
- Runtime engine, SDK, recovery, lifecycle, CLI
