# Phase 11.2 — Release Candidate Build Report

> **Date**: 2026-07-20
> **Version**: v1.0.0-rc1
> **Baseline**: 2640 tests

---

## 1. P0 — Critical Fixes

### 1.1 Linux PyInstaller Spec ✅

**Created**: `A3-Agent-linux.spec`

Differences from Windows spec:
- Line 18: `desktop/launcher.py` (forward slashes vs `desktop\\\\launcher.py`)
- Datas paths: forward slashes
- Removed Windows-specific `argv_emulation` and `target_arch` flags

```bash
# Build Linux package:
pyinstaller A3-Agent-linux.spec
# Output: dist/A3-Agent/
```

### 1.2 Version Normalization ✅

All version references updated to `v1.0.0-rc1`:

| File | Old | New |
|:-----|:----|:----|
| `desktop/config.py` (APP_VERSION) | `7.1.1` | `1.0.0-rc1` |
| `desktop/config.py` (docstring) | `v7.1.0` | `v1.0.0-rc1` |
| `desktop/launcher.py` (docstring) | `v7.1.0` | `v1.0.0-rc1` |
| `desktop/build.bat` (header) | `v7.1.0` | `v1.0.0-rc1` |
| `desktop/build.bat` (echo) | `v7.1.0` | `v1.0.0-rc1` |
| `desktop/__init__.py` | `v7.1.0` | `v1.0.0-rc1` |
| `desktop/hooks/runtime_hook.py` | `v7.1.0` | `v1.0.0-rc1` |
| `setup.py` (version) | `7.1.0` | `1.0.0-rc1` |

**Left as-is** (historical documentation):
- `CHANGELOG.md` — records v7.1.0/v7.1.1 history
- `docs/RELEASE_NOTES_v7.1.0.md` — historical release notes
- `docs/INSTALL.md` — user-facing install guide (update on final v1.0.0 tag)
- `docs/TROUBLESHOOTING.md` — references past versions

---

## 2. P1 — Release Infrastructure

### 2.1 Release Verification Script ✅

**Created**: `scripts/verify-release.sh`

Runs 7-stage verification:
1. Health check (`GET /health`)
2. Authentication (register → login → me)
3. Profile (assess → get)
4. Learning Pipeline (run → run_id verification)
5. Artifacts (generation check)
6. Security (unauthenticated request → 401)
7. Logout

```bash
bash scripts/verify-release.sh [API_URL]
```

### 2.2 Smoke Tests ✅

**Created**: `tests/test_rc_smoke.py` — 20 tests

| Category | Tests | Coverage |
|:---------|:-----:|:---------|
| Startup | 3 | Health, app title, app version |
| Auth | 5 | Register, login, me, unauthorized blocked, logout |
| Pipeline | 5 | Success, trace, artifacts, memory, multi-run |
| Artifacts | 3 | Disk existence, count, workspace browsable |
| History & Stats | 2 | History accessible, stats accumulated |
| Version | 2 | Config version, app version |

---

## 3. Build Commands

### Windows

```batch
cd desktop
build.bat
:: Output: dist\A3-Agent\A3-Agent.exe
```

### Linux

```bash
pyinstaller A3-Agent-linux.spec
# Output: dist/A3-Agent/A3-Agent
```

### Docker

```bash
docker build -t ghcr.io/leisureauf1/a3-multi-agent-system:v1.0.0-rc1 .
docker run -p 8501:8501 -p 8000:8000 ghcr.io/leisureauf1/a3-multi-agent-system:v1.0.0-rc1
```

---

## 4. Files Changed

| File | Change |
|:-----|:-------|
| `A3-Agent-linux.spec` | **NEW** — Linux PyInstaller spec |
| `scripts/verify-release.sh` | **NEW** — 7-stage verification (executable) |
| `tests/test_rc_smoke.py` | **NEW** — 20 smoke tests |
| `desktop/config.py` | Version: `7.1.1` → `1.0.0-rc1` |
| `desktop/launcher.py` | Docstring version |
| `desktop/build.bat` | Header + echo version |
| `desktop/__init__.py` | Docstring version |
| `desktop/hooks/runtime_hook.py` | Docstring version |
| `setup.py` | Version: `7.1.0` → `1.0.0-rc1` |
| `README.md` | Unchanged (updated on final v1.0.0 tag) |

---

## 5. Constraint Compliance

| Constraint | Status |
|:-----------|:------:|
| No src/core modification | ✅ |
| No agent modification | ✅ |
| No workflow/runtime modification | ✅ |
| Feature freeze | ✅ |
| Release engineering only | ✅ |

---

*End of Phase 11.2 — RC Build Report*
