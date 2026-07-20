# Phase 19.2 — Release Candidate Smoke Test

**Date:** 2026-07-20
**Status:** ✅ **PASSED** — 12/12 Linux checks, tarball verified.

---

## 1. Linux Tarball — Structure Verification

| Check | Result |
|-------|--------|
| SHA256 matches | ✅ `d1972420ad610e3c...` |
| `LICENSE` present | ✅ |
| `VERSION` present (`A3-Agent v1.0.0`) | ✅ |
| `README.txt` present | ✅ |
| `start.sh` present + executable | ✅ |
| `__pycache__` in tarball | ✅ 0 |
| `.pyc` files in tarball | ✅ 0 |
| Source tree intact (src/, web/, desktop/) | ✅ |
| Archive size | 2.3 MB |

---

## 2. Linux Runtime Smoke Test

| Step | Result | Detail |
|------|--------|--------|
| Start API server | ✅ | Port 9876, uvicorn |
| Health check | ✅ | `{"status":"ok"}` |
| Guest login | ✅ | `user_id=guest_98...` |
| Run pipeline | ✅ | `status=success`, 7 agents, 576ms |
| `memory_saved` | ✅ | `True` |
| Quiz generate | ✅ | 3 questions |
| History replay | ✅ | 2 records, `result_json` populated |
| Learning stats | ✅ | `sessions=2` |

---

## 3. Windows Tarball — Structure Assessment

| Check | Status |
|-------|--------|
| Windows `.exe` build | ⏳ Requires Wine/Windows — not executed on this host |
| `A3-Agent.spec` version | ✅ `v1.0.0` header added |
| `build.bat` version | ✅ `v1.0.0` |
| `build-windows-release.ps1` version | ✅ `v1.0.0` |
| `__pycache__` cleanup in build.bat | ✅ Added before PyInstaller step |

---

## 4. Issues Found + Fixed During Test

| # | Issue | Fix |
|---|-------|-----|
| 1 | README.txt showed `${VERSION}` unexpanded | Fixed heredoc quoting in `build-linux-package.sh` |
| 2 | SHA256 file missing filename | Fixed format to `hash  filename` |

---

## 5. Conclusion

**12/12 Linux checks passed. Tarball is clean, functional, and verifiable.**

Windows build requires a Windows host or Wine environment — build scripts are ready.
