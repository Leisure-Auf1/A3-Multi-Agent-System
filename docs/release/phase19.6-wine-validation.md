# Phase 19.6-A — Wine Windows Compatibility Pre-Flight Validation

**Date:** 2026-07-20
**Status:** ⚠️ Pre-flight — Windows build required, Wine unavailable

---

## 0. Blockers

| Blocker | Detail |
|---------|--------|
| **No Windows .zip** | `release/A3-Agent-v1.0.0-win64.zip` does not exist — PyInstaller cannot cross-compile Linux→Windows |
| **No Wine** | `wine` not installed — `sudo pacman -S wine` requires password (not available in session) |
| **PyInstaller ready** | ✅ v6.21.0 installed, scripts are prepared |

**Verdict:** Cannot perform live Wine validation. This report serves as a **pre-flight structural audit** — verifying that the build scripts will produce the correct package when executed on Windows.

---

## 1. Package Structure Audit (Predicted from Scripts)

### 1.1 From `A3-Agent.spec` (PyInstaller datas)

| Source | Destination | Status |
|--------|-------------|--------|
| `app.py` | `.` | ✅ |
| `src/` | `src/` | ✅ |
| `web/` | `web/` | ✅ — includes `web/i18n/` |
| `utils/` | `utils/` | ✅ |
| `desktop/` | `desktop/` | ✅ |
| `knowledge_base/` | `knowledge_base/` | ✅ |
| `demo/fixtures/` | `demo/fixtures/` | ✅ |
| `.streamlit/config.toml` | `.streamlit/` | ✅ |
| `.env.example` | `.` | ✅ |
| `LICENSE` | `.` | ✅ |
| `storage/a3.db` | — | ❌ **REMOVED** (Phase 19.2) |

### 1.2 From `build-windows-release.ps1` (Package additions)

| File/Dir | Source | Status |
|----------|--------|--------|
| `A3-Agent.exe` | PyInstaller `dist/` | ✅ |
| `_internal/` | PyInstaller bundled deps | ✅ |
| `VERSION` | Generated (`"1.0.0"`) | ✅ Fixed |
| `LICENSE` | Project root | ✅ |
| `README.txt` | `README.md` (copied) | ✅ |
| `start.bat` | Auto-generated | ✅ New |
| `config/` | Created empty | ✅ New |
| `assets/` | Created empty | ✅ New |

### 1.3 Final Predicted Structure

```
A3-Agent-v1.0.0-win64.zip
  └── A3-Agent/
       ├── A3-Agent.exe          # PyInstaller bundled executable
       ├── start.bat             # Double-click launcher
       ├── VERSION               # "1.0.0"
       ├── LICENSE               # MIT license
       ├── README.txt            # Quick start guide
       ├── config/               # Empty — user settings go here
       ├── assets/               # Empty — user files go here
       └── _internal/
            ├── app.py
            ├── src/             # Core agent source
            ├── web/
            │   ├── app.py       # Main Streamlit UI
            │   ├── i18n/        # ✅ en.toml + zh.toml
            │   ├── components/  # auth, chat, quiz, material
            │   ├── dashboard/
            │   ├── v1/
            │   └── utils/
            ├── desktop/
            ├── knowledge_base/
            └── ...              # streamlit, fastapi, uvicorn, veritas
```

---

## 2. i18n Integrity Check

### Files Present

```
web/i18n/
├── __init__.py   # 125 lines — t(), set_lang(), _detect_lang()
├── keys.py       # 130 lines — 146 key constants
├── en.toml       # 146 keys — verified valid TOML
└── zh.toml       # 146 keys — symmetric with en.toml
```

### Coverage

| Module | Keys |
|--------|------|
| `auth` | 14 |
| `tab` | 6 |
| `sidebar` | 2 |
| `dash` | 18 |
| `learn` | 16 |
| `stage` | 7 |
| `err` | 9 |
| `onboard` | 22 |
| `settings` | 24 |
| `fw` (fallback welcome) | 4 |
| `demo_suggestions` | 6 |
| **Total** | **146** |

All 146 keys verified non-empty and symmetric between en↔zh (tested in `test_i18n.py::TestLocaleLoading::test_en_and_zh_have_same_keys`).

---

## 3. Pre-Flight Checklist (for Windows Machine)

When the Windows build is run, verify:

### 3.1 Package Structure

| # | Check | Expected |
|---|-------|----------|
| 1 | Zip exists | `release/A3-Agent-v1.0.0-win64.zip` |
| 2 | `A3-Agent.exe` present | ✅ |
| 3 | `start.bat` present | ✅ |
| 4 | `VERSION` = `1.0.0` | ✅ |
| 5 | `LICENSE` present | ✅ |
| 6 | `README.txt` present | ✅ |
| 7 | `config/` directory | ✅ |
| 8 | `assets/` directory | ✅ |
| 9 | `web/i18n/en.toml` | ✅ |
| 10 | `web/i18n/zh.toml` | ✅ |

### 3.2 Wine Smoke Test (when Wine is available)

| # | Test | Command |
|---|------|---------|
| 1 | exe launch | `wine A3-Agent.exe` |
| 2 | Batch launcher | `wine cmd /c start.bat` |
| 3 | Health endpoint | `curl http://localhost:8000/health` |
| 4 | Guest login | Browser → Continue as Guest |
| 5 | Pipeline run | Enter goal → Run Pipeline |
| 6 | Quiz render | Verify quiz panel after pipeline |
| 7 | History replay | History tab → session records |
| 8 | Language: 中文 | Settings → 🌐 → 中文 |
| 9 | Language: English | Settings → 🌐 → English |

### 3.3 DLL Dependencies

Common Wine issues to watch for:

| Symptom | Likely Cause |
|---------|-------------|
| `err:module:import_dll` | Missing VC++ runtime → install `vcrun2019` via `winetricks` |
| `wine: could not load kernel32.dll` | 64-bit exe on 32-bit Wine prefix |
| `ImportError: No module named X` | PyInstaller hidden import missing |
| `OSError: [WinError 193]` | Architecture mismatch (32/64 bit) |

---

## 4. Constraints

| Constraint | Status |
|------------|--------|
| No src/core modification | ✅ |
| No src/agents modification | ✅ |
| No src/workflow modification | ✅ |
| No source code changes in this phase | ✅ |

---

## 5. Next Steps

1. **On Windows machine:** Run `desktop/build.bat` → `build-windows-release.ps1`
2. **Upload to GitHub:** `gh release upload v1.0.0 release/A3-Agent-v1.0.0-win64.zip release/A3-Agent-v1.0.0-win64.sha256`
3. **Publish Release:** `gh release edit v1.0.0 --draft=false`
4. **Re-run Phase 19.6** on a machine with Wine installed for live validation

---

**Verdict:** Scripts are structurally correct. Blocked on Windows build machine + Wine. Report serves as validated pre-flight checklist.
