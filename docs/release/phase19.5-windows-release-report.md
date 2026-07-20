# Phase 19.5 — Windows Release Packaging Report

**Date:** 2026-07-20
**Status:** ✅ Scripts fixed — ready for Windows build
**Platform:** Linux (scripts prepared, build requires Windows)

---

## 1. Audit Findings & Fixes

### 1.1 storage/a3.db References — REMOVED

`storage/a3.db` was excluded from Git tracking in Phase 19.2 (`.gitignore`). Three files still referenced it:

| File | Fix |
|------|-----|
| `A3-Agent.spec` | Removed `('storage/a3.db', 'storage')` from datas |
| `A3-Agent-linux.spec` | Removed `('storage/a3.db', 'storage')` from datas |
| `desktop/build.bat` | Removed `--add-data "storage/a3.db;storage"` line |

### 1.2 __pycache__ — CLEANED

| Path | Action |
|------|--------|
| `desktop/__pycache__/` | Deleted |

### 1.3 VERSION File — FIXED

`scripts/build-windows-release.ps1` was writing the package name instead of version:

```powershell
# Before (wrong)
"$PACKAGE_NAME" | Out-File ...  # → "A3-Agent-v1.0.0-win64"

# After (correct)
"$VERSION" | Out-File ...       # → "1.0.0"
```

### 1.4 start.bat — ADDED

Convenience launcher for Windows users:

```batch
@echo off
echo ============================================
echo   A3-Agent v1.0.0
echo ============================================
echo.
echo Starting A3-Agent...
echo.
A3-Agent.exe
pause
```

Generated automatically by `build-windows-release.ps1`.

### 1.5 config/ and assets/ Directories — ADDED

Empty placeholder directories for user configuration and assets, created by the packaging script.

---

## 2. Package Structure

```
release/
  A3-Agent-v1.0.0-win64.zip
    └── A3-Agent/
         ├── A3-Agent.exe         # PyInstaller bundled executable
         ├── start.bat            # Convenience launcher (double-click friendly)
         ├── VERSION              # "1.0.0"
         ├── LICENSE              # MIT License
         ├── README.txt           # Quick start guide
         ├── config/              # User configuration directory (empty)
         ├── assets/              # User assets directory (empty)
         └── _internal/           # PyInstaller bundled dependencies
              ├── web/i18n/       # ✅ Internationalization (en/zh)
              ├── web/components/ # ✅ Auth, chat, quiz, material panels
              ├── src/            # ✅ Core source
              ├── desktop/        # ✅ Launcher config
              └── ...             # Streamlit, FastAPI, uvicorn, veritas
```

---

## 3. i18n Included

Since `web/` directory is bundled entirely via `('web', 'web')` in the spec, the new `web/i18n/` module (Phase 19.4-B) is automatically included:

```
_internal/web/i18n/
├── __init__.py   # t() function
├── keys.py       # 146 key constants
├── en.toml       # English locale
└── zh.toml       # Chinese locale
```

No spec changes needed — `web/` glob covers all subdirectories.

---

## 4. Build Steps (Windows)

```powershell
# Step 1: Install dependencies
pip install -r requirements.txt

# Step 2: Build executable
desktop\build.bat
# Output: dist\A3-Agent\A3-Agent.exe

# Step 3: Create release package
powershell -File scripts\build-windows-release.ps1
# Output: release\A3-Agent-v1.0.0-win64.zip
#         release\A3-Agent-v1.0.0-win64.sha256

# Step 4: Upload to GitHub Release
gh release upload v1.0.0 `
  release\A3-Agent-v1.0.0-win64.zip `
  release\A3-Agent-v1.0.0-win64.sha256
```

---

## 5. Smoke Test Checklist

After building on Windows, verify:

| # | Test | Command / Action |
|---|------|------------------|
| 1 | exe launches | Double-click `A3-Agent.exe` or run from terminal |
| 2 | Health endpoint | `curl http://localhost:8000/health` → `{"status":"ok"}` |
| 3 | Guest login | Click "Continue as Guest" in web UI |
| 4 | Pipeline run | Enter learning goal → click "Run Pipeline" |
| 5 | Quiz panel | After pipeline, verify quiz renders |
| 6 | History replay | Navigate to History tab → verify session records |
| 7 | Language switch | Settings → 🌐 → switch to 中文 → verify UI |
| 8 | English switch back | Settings → 🌐 → switch to English → verify UI |

---

## 6. Files Changed

| File | Change |
|------|--------|
| `A3-Agent.spec` | Removed `storage/a3.db` from datas |
| `A3-Agent-linux.spec` | Removed `storage/a3.db` from datas |
| `desktop/build.bat` | Removed `--add-data storage/a3.db` line |
| `desktop/__pycache__/` | Deleted |
| `scripts/build-windows-release.ps1` | Fixed VERSION, added start.bat/config/assets |

---

## 7. Constraints

| Constraint | Status |
|------------|--------|
| No src/core modification | ✅ |
| No agents modification | ✅ |
| No workflow modification | ✅ |
| No API modification | ✅ |
| Linux release unchanged | ✅ |
