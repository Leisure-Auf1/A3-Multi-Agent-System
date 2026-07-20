# Phase 19.0 — Windows + Linux Dual Platform Packaging Audit

**Date:** 2026-07-20
**Status:** ⏳ **AWAITING HUMAN GATE** — READ-ONLY audit.

**Baseline:** v1.0.0 (da953fa), 2857 tests.

---

## 1. Windows Build Chain Audit — Status: 🟡 Needs Repair

### 1.1 `desktop/build.bat`

| Item | Status | Notes |
|------|--------|-------|
| Version header | ✅ | `A3-Agent v1.0.0` |
| `--add-data "app.py;."` | ✅ | Root `app.py` exists (HF Spaces delegate) |
| `--add-data "src;src"` | ✅ | Source tree |
| `--add-data "web;web"` | ✅ | Streamlit UI |
| `--add-data "utils;utils"` | ✅ | `utils/` has `streaming.py` |
| `--add-data "desktop;desktop"` | ✅ | Launcher + config |
| `--add-data "knowledge_base;knowledge_base"` | ✅ | Course content |
| `--add-data "storage/a3.db;storage"` | ✅ | SQLite DB template |
| `--add-data "demo/fixtures;demo/fixtures"` | ✅ | Demo data |
| `--hidden-import` count | 22 | keyring chain + veritas modules |
| `--collect-all fastapi/uvicorn/streamlit/veritas` | ✅ | Full packages |
| `--exclude-module` list | 5 | pyarrow, scipy, pytest, matplotlib, tkinter |
| Launch entry | ✅ | `desktop/launcher.py` |

**Missing hidden imports:**
```
src.providers.anthropic_provider
src.providers.google_provider
src.providers.qwen_provider
src.providers.kimi_provider
src.providers.grok_provider
src.auth.password
src.auth.jwt_manager
src.orchestration.*
```

### 1.2 `A3-Agent.spec` (Windows)

| Item | Status | Notes |
|------|--------|-------|
| Version header | ❌ | No version comment |
| Path separator | ⚠️ | `'desktop\\\\launcher.py'` — backslash, Windows-only |
| `runtime_hooks` | ✅ | `desktop/hooks/runtime_hook.py` (forward-slash) |
| Hidden imports match build.bat | ✅ | Same 27 + collect_all |
| `app.py` data | ✅ | Root `app.py` exists |

### 1.3 `scripts/build-windows-release.ps1`

| Item | Status |
|------|--------|
| `$VERSION = "7.1.0"` | ❌ **Must be `1.0.0`** |
| Hardcoded `v7.1.0` in output paths | ❌ **Must be `v1.0.0`** |
| README copy to `README.txt` | ✅ |
| SHA256 generation | ✅ |
| gh release upload command | ✅ |

---

## 2. Linux Build Chain Audit — Status: 🟡 Needs Repair

### 2.1 `A3-Agent-linux.spec`

| Item | Status | Notes |
|------|--------|-------|
| Version header | ✅ | `v1.0.0` |
| Path separator | ✅ | Forward-slash |
| `runtime_hooks` | ✅ | `desktop/hooks/runtime_hook.py` |
| Hidden imports match build.bat | ✅ | Same 27 + collect_all |
| `excludes` | ✅ | pyarrow, scipy, pytest, matplotlib, tkinter |
| Missing hidden imports | ⚠️ | Same as Windows — `src.providers.*` etc |

### 2.2 `scripts/build-linux-package.sh`

| Item | Status |
|------|--------|
| `VERSION="7.1.0"` | ❌ **Must be `1.0.0`** |
| Hardcoded `v7.1.0` in `start.sh` template | ❌ **Must be `v1.0.0`** |
| Hardcoded `v7.1.0` in `INSTALL.md` template | ❌ **Must be `v1.0.0`** |
| Uses `rsync` with `--exclude='__pycache__'` | ✅ |
| Creates `start.sh` launcher with venv auto-setup | ✅ |
| `streamlit run app.py` (root-level) | ✅ Root `app.py` delegates to `web.app.main()` |

### 2.3 `scripts/build-release.sh`

| Item | Status |
|------|--------|
| `$VERSION = "7.1.0"` | ❌ **Must be `1.0.0`** |
| `release/A3-Agent-v7.1.0-linux-x64.tar.gz` | ❌ |

### 2.4 `scripts/release_check.py`

| Item | Status |
|------|--------|
| `A3-Agent v7.1.0` header | ❌ **Must be `v1.0.0`** |
| `v7.1.0` in output strings | ❌ |

---

## 3. Desktop Launcher — Status: ✅

| Item | Status | Evidence |
|------|--------|----------|
| `APP_VERSION = "1.0.0"` | ✅ | `desktop/config.py:18` |
| Windows `APPDATA` path | ✅ | `desktop/config.py:42-45` |
| Linux `~/.a3-agent` path | ✅ | `desktop/config.py:46-49` |
| `BUNDLE_ROOT` detection | ✅ | `sys._MEIPASS` (frozen) / project root (dev) |
| Bundle integrity check | ✅ | `verify_bundle_integrity()` with frozen-mode gating |
| Ports: 8000 + 8501 | ✅ | `desktop/config.py:22-23` |

---

## 4. v1.0.0 Tarball Contents Audit

### 4.1 Contents (`A3-Agent-v1.0.0-linux-x64.tar.gz`, 86 MB, 2098 files)

| Category | Files | Status |
|----------|-------|--------|
| Total files | 2098 | — |
| `A3-Agent/` binary | ✅ | PyInstaller onedir executable |
| `_internal/` dir | ✅ | Bundled Python + packages |
| `_internal/app.py` | ✅ | Root entry point (HF Spaces delegate) |
| `_internal/web/app.py` | ✅ | Streamlit UI |
| `_internal/src/` | ✅ | Application source |
| `_internal/desktop/launcher.py` | ✅ | PyInstaller entry point |
| `_internal/streamlit/static/index.html` | ✅ | Streamlit assets |

### 4.2 Forbidden Files

| Type | Count | Example | Severity |
|------|-------|---------|----------|
| `__pycache__/` | 19+ dirs | `src/security/__pycache__/`, `src/data/__pycache__/` | 🔴 **P0 — Must remove** |
| `.pyc` files | ~100+ | `*.cpython-314.pyc` | 🔴 **P0 — Must remove** |
| `pyarrow` test headers | 17 | `pyarrow/include/arrow/io/test_common.h` | 🟡 P1 |
| `tests/` | 0 | No A3 test files | ✅ |
| `.pytest_cache/` | 0 | Not present | ✅ |

### 4.3 Missing Files

| File | Expected Path | Status |
|------|--------------|--------|
| `LICENSE` | `A3-Agent/LICENSE` | ❌ Not in root — only inside `_internal/` |
| `VERSION` | `A3-Agent/VERSION` | ❌ Not in root |
| `README.txt` | `A3-Agent/README.txt` | ❌ Not in root |
| `config/` template | `A3-Agent/config/` | ❌ Not present |
| `workspace/` placeholder | `A3-Agent/workspace/` | ❌ Not present |

---

## 5. Cross-Platform First Launch Simulation

### 5.1 API Health Check

```
GET /health → 200 OK → {"status":"ok"}
```
✅ Backend responds correctly.

### 5.2 Guest Login Flow

```
POST /api/v2/auth/guest → 200 → token issued
POST /api/v2/learning/run → 200 → pipeline success
```
✅ Guest can register and run pipeline.

### 5.3 Pipeline Output (API-level)

| Section | Status |
|---------|--------|
| Profile | ✅ 6 dimensions |
| Plan | ✅ 3 nodes |
| Content | ✅ 3 chapters |
| Evaluation | ✅ score=90, passed=True |
| Reflection | ✅ source=llm, summary present |
| Resources | ✅ 1 resource |
| Trace | ✅ 9 events with metadata |
| Memory saved | ✅ True |

### 5.4 Quiz

```
POST /api/v2/evaluation/quiz/generate → 200 → 3 questions
POST /api/v2/evaluation/quiz/score → 200 → 100%
```
✅ Quiz flow works.

### 5.5 History Replay

```
GET /api/v2/learning/history → 200 → result_json with all 6 sections
```

---

## 6. Version Inconsistency Matrix

| File | Current | Required | Fix |
|------|---------|----------|-----|
| `VERSION` | `v1.0.0` | ✅ | — |
| `desktop/config.py` | `1.0.0` | ✅ | — |
| `desktop/build.bat` | `v1.0.0` | ✅ | — |
| `desktop/launcher.py` | `v1.0.0` | ✅ | — |
| `A3-Agent-linux.spec` | `v1.0.0` | ✅ | — |
| `A3-Agent.spec` | — | ⚠️ | Add header |
| `scripts/build-linux-package.sh` | `7.1.0` | ❌ | 6 locations |
| `scripts/build-windows-release.ps1` | `7.1.0` | ❌ | 3 locations |
| `scripts/build-release.sh` | `7.1.0` | ❌ | 3 locations |
| `scripts/release_check.py` | `7.1.0` | ❌ | 2 locations |
| `CONTRIBUTING.md` | `7.1.0` | ❌ | 1 location |

---

## 7. Release Checklist

### P0 — Blocking (4 items)

| # | Item | Fix |
|---|------|-----|
| 1 | **Remove `__pycache__/` from tarball** | Add `--exclude '__pycache__'` to rsync or PyInstaller `--clean` |
| 2 | **Update 4 build scripts to v1.0.0** | sed replace `7.1.0` → `1.0.0` in `.sh`, `.ps1`, `.py` |
| 3 | **Add LICENSE, VERSION, README.txt to tarball root** | Copy to `dist/A3-Agent/` before `tar czf` |
| 4 | **Build Windows v1.0.0 release** | Run `desktop/build.bat` → `build-windows-release.ps1` |

### P1 — Important (2 items)

| # | Item |
|---|------|
| 5 | Add missing hidden imports: `src.providers.*`, `src.auth.*`, `src.orchestration.*` |
| 6 | Clean release directory — remove stale v7.x files (350+ MB) |

### P2 — Polish (3 items)

| # | Item |
|---|------|
| 7 | Update `CONTRIBUTING.md` version reference |
| 8 | Add `A3-Agent.spec` version header |
| 9 | Create unified `checksums.sha256` |

---

## 8. Build Commands (Post-Repair)

### Windows
```batch
:: Build exe
desktop\build.bat
:: Package release
powershell -File scripts\build-windows-release.ps1
```

### Linux
```bash
# PyInstaller build
pyinstaller A3-Agent-linux.spec
# Package release
bash scripts/build-linux-package.sh
```

### Docker
```bash
docker build -t a3-agent:v1.0.0 .
docker compose up -d
```

---

## ⏳ Awaiting Human Gate

**4 P0 blockers, 2 P1 items, 3 P2 polish. ~30 lines of version fixes + rebuild.**
