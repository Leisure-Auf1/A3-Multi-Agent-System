# Phase 19.0 — Release Packaging & Distribution Audit

**Date:** 2026-07-20
**Status:** ⏳ **AWAITING HUMAN GATE** — READ-ONLY audit.

**Baseline:** v1.0.0 (da953fa), 2857 tests, Phase 18.1 complete.

---

## 1. Build System Audit

### 1.1 PyInstaller Specs

| Spec | Status | Issues |
|------|--------|--------|
| `A3-Agent-linux.spec` | ✅ v1.0.0 | Header says v1.0.0; `app.py` referenced as data but root-level `app.py` doesn't exist — only `web/app.py` ⚠️ |
| `A3-Agent.spec` (Windows) | 🟡 | No version header; backslash paths (`desktop\\launcher.py`); `app.py` same issue; `runtime_hooks` uses forward-slash — inconsistent |

**Hidden imports audit:**
- Linux spec: 27 hidden imports + `collect_all` for fastapi/uvicorn/streamlit/veritas
- Windows spec: Same 27 hidden imports + `collect_all`
- Both specs: missing `src.providers.*` (8 provider modules), `src.auth.*`, `src.orchestration.*`
- Both specs: `keyring` + `SecretStorage` + `jeepney` — Linux-specific but included in Windows spec

### 1.2 Build Scripts

| Script | Target | Version | Status |
|--------|--------|---------|--------|
| `desktop/build.bat` | Windows PyInstaller | **v1.0.0** ✅ | 23 hidden-imports, 10 add-data |
| `scripts/build-linux-package.sh` | Linux tar.gz | **v7.1.0** ❌ | Hardcoded v7.1.0 in paths/README |
| `scripts/build-windows-release.ps1` | Windows zip | **v7.1.0** ❌ | Hardcoded v7.1.0 |
| `scripts/build-release.sh` | Both | **v7.1.0** ❌ | Hardcoded v7.1.0 |
| `scripts/release_check.py` | Validation | **v7.1.0** ❌ | Hardcoded v7.1.0 |
| `scripts/verify-release.sh` | 7-stage verification | Auto-detect ✅ | No hardcoded version |

### 1.3 Docker

| File | Status | Notes |
|------|--------|-------|
| `Dockerfile` | ✅ | Multi-stage build, pinned Veritas-Core commit |
| `docker-compose.yml` | ✅ | API + Streamlit services, profiles |
| `.github/workflows/docker-publish.yml` | ✅ | CI/CD with tags |

**Docker image not version-tagged** — latest only. No `v1.0.0` tag.

### 1.4 `app.py` Data File Issue

Both `.spec` files include:
```python
datas = [('app.py', '.'), ...]
```

But `app.py` is now at `web/app.py`. The root-level `app.py` was removed during Phase 10.1 UI unification. This will cause PyInstaller builds to fail.

---

## 2. Version Inconsistency Audit

### Files with Correct `v1.0.0`

| File | Line | Value |
|------|------|-------|
| `VERSION` | 1 | `A3-Agent v1.0.0` ✅ |
| `desktop/config.py` | 18 | `APP_VERSION = "1.0.0"` ✅ |
| `desktop/launcher.py` | 2 | `A3-Agent v1.0.0` ✅ |
| `desktop/__init__.py` | 1 | `A3-Agent v1.0.0` ✅ |
| `desktop/build.bat` | 3, 14 | `v1.0.0` ✅ |
| `desktop/hooks/runtime_hook.py` | 2 | `v1.0.0` ✅ |
| `A3-Agent-linux.spec` | 2 | `v1.0.0` ✅ |
| `README.md` (badge) | 7 | `v1.0.0` ✅ |

### Files with Stale `v7.1.0`

| File | Line(s) | Fix |
|------|---------|-----|
| `scripts/build-linux-package.sh` | 11, 42, 66, 95, 105-106 | Replace `v7.1.0` with `v1.0.0` |
| `scripts/build-windows-release.ps1` | 2, 11-12 | Replace `v7.1.0` with `v1.0.0` |
| `scripts/build-release.sh` | 3, 8-9 | Replace `v7.1.0` with `v1.0.0` |
| `scripts/release_check.py` | 3, 162 | Replace `v7.1.0` with `v1.0.0` |
| `CONTRIBUTING.md` | 103 | Replace `v7.1.0` with `v1.0.0` |
| `A3-Agent.spec` (Win) | — | Add version header |
| `CHANGELOG.md` | — | Last entry is v7.1.0; needs v1.0.0 entry |

---

## 3. Release Structure Audit

### Current `release/` Contents

```
release/
├── A3-Agent-v1.0.0-linux-x64.tar.gz    86 MB  ✅ Current
├── A3-Agent-v1.0.0-linux-x64.sha256    99 B    ✅ Current
├── A3-Agent-v7.1.0-win64.zip            54 MB  🟡 Stale
├── A3-Agent-v7.1.0-win64.sha256         92 B   🟡 Stale
├── A3-Agent-v7.1.1-linux-x64/          274 MB  ❌ Extracted dir
├── A3-Agent-v7.1.1-linux-x64.tar.gz    160 MB  ❌ Old
├── A3-Agent-v7.1.1-linux-x64.sha256    99 B    ❌ Old
├── A3-Agent-v7.1.1-win64/              274 MB  ❌ Extracted dir
├── A3-Agent-v7.1.1-win64.zip           54 MB   ❌ Old
└── A3-Agent-v7.1.1-win64.sha256        92 B    ❌ Old
```

**Total:** 910 MB — needs cleanup. Stale v7.x files should be removed.

### Missing from v1.0.0 Release

| Asset | Status |
|-------|--------|
| `A3-Agent-v1.0.0-win64.zip` | ❌ Missing — only v7.x Windows builds exist |
| `A3-Agent-v1.0.0-linux-x64.tar.gz` | ✅ Present (86 MB) |
| `checksums.sha256` (unified) | ❌ Missing — individual `.sha256` files only |
| `README.txt` | ❌ Missing from v1.0.0 root (exists in v7.1.1 extracted dir) |
| Docker image tag `v1.0.0` | ❌ Missing — only `latest` |

---

## 4. Cleanup Audit

### Forbidden in Release Package

| Item | v1.0.0 tarball | v7.1.1 Linux | v7.1.1 Win |
|------|---------------|-------------|------------|
| `tests/` | 0 | 17 `.h` test files (pyarrow) | 0 |
| `__pycache__/` | ✅ Found ❌ | 19 dirs ❌ | 19 dirs ❌ |
| `.pytest_cache/` | 0 | 0 | 0 |
| Debug logs | 0 | 0 | 0 |
| Dev secrets | 0 | 0 | 0 |
| Local config | 0 | 0 | 0 |

### Missing from Release Package

| Item | Status |
|------|--------|
| `docs/` | ❌ Not bundled |
| `examples/` | ❌ Not bundled |
| `config templates` | ❌ `.env.example` only |
| `README.txt` | ❌ Missing from v1.0.0 |
| `VERSION` | ✅ In v7.1.1 extracted dir |

---

## 5. First Launch Experience

### Current State

| Platform | Launch | What Happens |
|----------|--------|-------------|
| **Dev mode** | `streamlit run web/app.py` | Works ✅ — health check passed |
| **Windows frozen** | `A3-Agent.exe` | Launcher → FastAPI → Streamlit → Browser |
| **Linux frozen** | `./A3-Agent` | Launcher → FastAPI → Streamlit → Browser |
| **Docker** | `docker compose up` | FastAPI + Streamlit in containers |

### First Launch Checklist

| Item | Status | Notes |
|------|--------|-------|
| Default dir: `~/.a3-agent/` | ✅ | Created by `desktop/config.py` |
| Config: `~/.a3-agent/config/` | ✅ | `llm.json`, `secrets` |
| Workspace: `~/.a3-agent/workspace/` | ✅ | Per-user isolation |
| Database: `storage/a3.db` | ✅ | SQLite auto-created |
| Health check: `/health` | ✅ | `{"status":"ok"}` |
| Streamlit: port 8501 | ✅ | `0.0.0.0:8501` |
| FastAPI: port 8000 | ✅ | via launcher |

---

## 6. Runtime Dependencies

### Current `requirements.txt` (14 lines)

```
veritas-core @ git+https://github.com/Leisure-Auf1/Veritas-Core.git@29a42de
streamlit>=1.28.0
fastapi>=0.115.0
uvicorn>=0.30.0
keyring>=25.0.0
```

### Missing Dependencies

| Package | Why Needed | In requirements.txt? |
|---------|-----------|---------------------|
| `pydantic` | FastAPI dependency (transitive) | ❌ (implicit via fastapi) |
| `jinja2` | Streamlit dependency | ❌ (implicit) |
| `cryptography` | JWT token generation | ❌ |
| `pyjwt` | JWT verification | ❌ |
| `secretstorage` | Linux keyring backend | ❌ |
| `jeepney` | Linux D-Bus keyring | ❌ |

**Note:** These are transitive dependencies of `fastapi`/`streamlit`/`keyring` and get pulled in by pip. Not blockers for pip installs, but may need explicit listing for PyInstaller (`hiddenimports` already cover keyring/SecretStorage/jeepney).

---

## 7. P0/P1/P2 Issues

### P0 — Blocking (4 items)

| # | Issue | Impact |
|---|-------|--------|
| P0-1 | **`app.py` in PyInstaller specs points to non-existent file.** Both `A3-Agent.spec` and `A3-Agent-linux.spec` have `('app.py', '.')` in datas — this file was moved to `web/app.py` in Phase 10.1. Builds will fail. | 🔴 Blocker |
| P0-2 | **Build scripts hardcoded v7.1.0.** 4 scripts reference old version. Running them would produce `A3-Agent-v7.1.0-*` artifacts. | 🔴 Blocker |
| P0-3 | **v1.0.0 tarball contains `__pycache__/`.** Release artifact includes compiled bytecode. This shouldn't be in production distribution. | 🔴 Blocker |
| P0-4 | **No Windows v1.0.0 release.** Only Linux tarball exists. GitHub Release only has 1 asset. | 🔴 Blocker |

### P1 — Important (3 items)

| # | Issue | Impact |
|---|-------|--------|
| P1-1 | **Release directory is 910 MB.** Contains stale v7.x extracted directories + old artifacts. | 🟡 Waste |
| P1-2 | **No unified checksums file.** Individual `.sha256` files exist but no `checksums.sha256` with all checksums. | 🟡 |
| P1-3 | **Docker image v1.0.0 tag missing.** Only `latest` exists. | 🟡 |

### P2 — Polish (3 items)

| # | Issue | Impact |
|---|-------|--------|
| P2-1 | **`README.txt` missing from v1.0.0 tarball.** Extracted dir should have a README for the user. | 🟢 |
| P2-2 | **Missing hidden imports** in both specs: `src.providers.*`, `src.auth.*`, `src.orchestration.*` | 🟢 |
| P2-3 | **`requirements.txt` is minimal** — 5 direct deps. Transitive deps implicit. Works for pip but not for auditing. | 🟢 |

---

## 8. Recommended Fix Plan

### Phase 19.1 — Packaging Implementation

| Wave | Fixes | Files | Effort |
|------|-------|-------|--------|
| P0 | Fix `app.py` path in both specs; Update 4 build scripts to v1.0.0; Rebuild without `__pycache__`; Build Windows v1.0.0 release | 6 files | ~30 lines + build |
| P1 | Clean release directory; Create unified checksums; Tag Docker image | 2 files + manual | ~10 lines |
| P2 | Add `README.txt` to tarball; Add missing hidden imports; Expand requirements.txt | 3 files | ~20 lines |

---

## ⏳ Awaiting Human Gate

**4 P0 blockers, 3 P1 items, 3 P2 polish. ~60 lines of fixes + rebuild required.**
