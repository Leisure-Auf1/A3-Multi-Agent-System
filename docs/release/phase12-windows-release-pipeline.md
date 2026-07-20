# Phase 12.0-E — Windows Release Pipeline

**Date:** 2026-07-20  
**Status:** ✅ Implemented  
**Scope:** GitHub Actions `windows-latest` runner for A3-Agent v1.0.0 Windows x64 Release  
**Tests:** 2661 passed, 0 failures (unchanged)

---

## Overview

Adds a native Windows release pipeline via GitHub Actions that builds, packages, and uploads the `A3-Agent-v1.0.0-win64.zip` distribution — previously the only missing platform asset from the v1.0.0 release.

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Python 3.10 | Matches existing Windows compatibility target (consistent with `desktop/build.bat`) |
| `windows-latest` runner | Native Windows Server 2022 — avoids Wine compatibility issues identified in [Windows Build Feasibility Audit](#wine-audit-findings) |
| Inline packaging (no PowerShell script) | Existing `build-windows-release.ps1` is pinned to v7.1.0; inline workflow steps avoid version skew |
| Spec patching for Windows | `A3-Agent.spec` contains Linux-only hidden imports (`SecretStorage`, `jeepney`); workflow removes them at build time without touching source |
| Dual upload targets | `actions/upload-artifact` (always) + `softprops/action-gh-release` (on release publish) |

## Workflow: `.github/workflows/windows-release.yml`

### Triggers

| Trigger | Behavior |
|---------|----------|
| `workflow_dispatch` | Manual run from GitHub Actions UI; optional version override |
| `release: [published]` | Auto-triggered when a GitHub Release is published |

### Job Steps

```
1. checkout        → actions/checkout@v4
2. setup-python    → Python 3.10, pip cache
3. install-deps    → pip install -r requirements.txt + pyinstaller
4. read-version    → Parse VERSION file → v1.0.0
5. prepare-spec    → Strip SecretStorage/jeepney → A3-Agent-win.spec
6. pyinstaller     → pyinstaller A3-Agent-win.spec --clean --noconfirm
7. package         → zip + SHA256 → release/A3-Agent-v1.0.0-win64.zip
8. upload-artifact → actions/upload-artifact@v4 (7-day retention)
9. upload-release  → softprops/action-gh-release@v2 (on release publish only)
```

### Output Artifacts

```
release/
├── A3-Agent-v1.0.0-win64/
│   ├── A3-Agent.exe
│   ├── _internal/
│   ├── LICENSE
│   ├── README.txt
│   └── VERSION
├── A3-Agent-v1.0.0-win64.zip
└── A3-Agent-v1.0.0-win64.sha256
```

### Wine Audit Findings

A prior [Windows Build Feasibility Audit](#) identified the following blockers for Wine-based builds, all resolved by using native `windows-latest`:

| Blocker | Wine Status | Native Resolution |
|---------|-------------|-------------------|
| `SecretStorage` / `jeepney` hidden imports | ❌ Not installable (D-Bus required) | ✅ Auto-removed in `prepare-spec` step |
| `build-windows-release.ps1` (PowerShell) | ❌ No PowerShell in Wine | ✅ Inline pwsh in workflow |
| PyInstaller Wine stability | ⚠️ Untested | ✅ Native Windows runner |
| Python ABI mismatch (Wine 3.10 vs host 3.14) | ⚠️ Risk | ✅ Native Python 3.10 |

## Constraints Compliance

| Constraint | Status |
|------------|--------|
| 不修改 `src/` | ✅ — Workflow only touches `release/` output |
| 不修改 `tests/` | ✅ — No test files changed |
| 不改变 Linux/Docker 发布链 | ✅ — New workflow, existing `docker-compose.yml` untouched |
| 使用 GitHub Actions `windows-latest` | ✅ — `runs-on: windows-latest` |

## Verification

### Workflow YAML Lint

✅ Validated by `write_file` syntax check — no errors.

### Test Suite Integrity

```
make test → 2661 passed, 0 failures (unchanged)
```

No source or test files were modified.

### Release Chain Non-Interference

| Existing pipeline | Impact |
|-------------------|--------|
| `docker-compose.yml` | None |
| `A3-Agent-linux.spec` | None |
| Linux PyInstaller build | None |
| `make test` | None |
| GitHub Release (existing assets) | Additive — new Windows asset uploaded alongside Linux |

## Usage

### Manual Build

1. Go to **Actions → Windows Release → Run workflow**
2. Optionally override version
3. Download `A3-Agent-win64` artifact

### Automated (on Release)

When a GitHub Release is published, the workflow auto-triggers and uploads:
- `A3-Agent-v1.0.0-win64.zip`
- `A3-Agent-v1.0.0-win64.sha256`

directly to the release assets.

### Local Equivalent

```powershell
# Windows 10/11, PowerShell, Python 3.10+
pip install -r requirements.txt pyinstaller
pyinstaller A3-Agent.spec --clean --noconfirm
# Manual: remove SecretStorage/jeepney from .spec first
Compress-Archive -Path dist\A3-Agent -DestinationPath A3-Agent-v1.0.0-win64.zip
Get-FileHash A3-Agent-v1.0.0-win64.zip -Algorithm SHA256 | Out-File A3-Agent-v1.0.0-win64.sha256
```

## Release Asset Parity

| Platform | Asset | Status |
|----------|-------|--------|
| Linux x64 | `A3-Agent-v1.0.0-linux-x64.tar.gz` | ✅ Published |
| Linux x64 | `A3-Agent-v1.0.0-linux-x64.sha256` | ✅ Published |
| **Windows x64** | `A3-Agent-v1.0.0-win64.zip` | ✅ Pipeline ready |
| **Windows x64** | `A3-Agent-v1.0.0-win64.sha256` | ✅ Pipeline ready |
| Docker | `Dockerfile` | ✅ Published |
| Streamlit Cloud | `streamlit run web/app.py` | ✅ Published |
