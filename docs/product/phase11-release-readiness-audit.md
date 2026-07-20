# Phase 11.0 — Release Readiness Audit

> **Date**: 2026-07-20
> **Current**: v7.1.1
> **Tests**: 2640 passed, 0 failures
> **Status**: 🟡 READY WITH BLOCKERS

---

## 1. Build System Status

| Component | Windows | Linux | Docker |
|:----------|:------:|:-----:|:------:|
| PyInstaller spec | ✅ (needs update) | ❌ **MISSING** | N/A |
| Build script | ✅ `build.bat` | ❌ **MISSING** | ✅ `Dockerfile` |
| Cross-platform config | ✅ | ✅ | N/A |
| CI workflow | N/A | N/A | ✅ `docker-publish.yml` |
| Existing assets | ✅ `release/v7.1.1-win64.zip` | ✅ `release/v7.1.1-linux-x64.tar.gz` | ✅ GHCR |

---

## 2. Blockers (3 P0 items)

| # | Blocker | Fix Required |
|:--|:--------|:-------------|
| 1 | **Linux PyInstaller spec missing** | Create `A3-Agent-linux.spec` |
| 2 | **Version references stale** | Bump v7.1.0/v7.1.1 → v1.0.0 |
| 3 | **Hidden imports outdated** | Add `web.theme`, verify all modules bundled |

---

## 3. What's Ready

- ✅ 2640 tests, 0 failures
- ✅ Security: Auth + Permission + TokenBudget chain
- ✅ Persistence: SQLite + Filesystem, full lifecycle verified
- ✅ UI: 6-tab dashboard with onboarding
- ✅ Docs: User getting-started, installation, FAQ, architecture, API reference
- ✅ Docker: Multi-stage build, multi-arch (amd64+arm64), health check
- ✅ CI: Test matrix (Python 3.10-3.13), Docker build check, tag-triggered publish
- ✅ Existing v7.1.1 release assets functional

---

## 4. What Needs Work

### P0 — Blocking
- Linux PyInstaller build path
- Version string consistency
- Hidden import audit

### P1 — Important
- Remove bundled `storage/a3.db` (seed at runtime)
- Create `desktop/build.sh` for Linux
- Release automation script

### P2 — Future
- Code signing certificate
- Auto-update mechanism
- macOS support

---

## 5. Recommendation

**Proceed to v1.0.0 release** after resolving the 3 P0 blockers:

1. Create Linux `.spec` file
2. Bump all version strings to `v1.0.0`
3. Audit and update hidden imports for new modules

Estimated effort: ~1 hour. All other infrastructure is production-ready.

---

## 6. Files Audited

| File | Purpose | Status |
|:-----|:--------|:------:|
| `A3-Agent.spec` | PyInstaller spec (Windows) | ⚠️ needs Linux counterpart |
| `desktop/build.bat` | Windows build script | ✅ functional, needs version bump |
| `desktop/config.py` | Cross-platform launcher config | ✅ v7.1.1, both platforms |
| `desktop/launcher.py` | FastAPI + Streamlit child launcher | ✅ |
| `desktop/hooks/runtime_hook.py` | PyInstaller runtime hook | ✅ |
| `Dockerfile` | Multi-stage Docker build | ✅ |
| `docker-compose.yml` | Docker Compose config | ✅ |
| `scripts/start.sh` | Docker entry point | ✅ |
| `.github/workflows/test.yml` | CI test matrix | ✅ |
| `.github/workflows/docker-publish.yml` | Docker publish on tag | ✅ |
| `release/` | Existing v7.1.1 assets | ✅ |

---

*End of Phase 11.0 — Release Readiness Audit*
