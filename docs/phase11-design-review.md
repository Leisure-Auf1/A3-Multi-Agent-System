# Phase 11 Design Review

> **Reviewer:** Systematic cross-reference audit  
> **Date:** 2026-07-18  
> **Result:** ❌ 7 issues found — requires revision

---

## Issue 1: Electron introduces unrelated tech stack

**Severity: HIGH**

A3 is a pure Python project. Adding Electron means:
- `package.json` + `node_modules/` (npm ecosystem)
- Electron binary (~150 MB)
- `electron-builder` for packaging
- Node.js runtime requirement on dev machine

None of this exists today. The design jumps from "Python monorepo" to "Electron + Docker + Python" without justifying why Electron is necessary.

**Fix:** Add a "Technology Evaluation" section that compares Electron vs PyWebView vs Tauri vs native Streamlit desktop wrapper. Provide rationale for the choice.

---

## Issue 2: No `docker-compose.desktop.yml` defined

**Severity: MEDIUM**

The design references `docker-compose.desktop.yml` multiple times but never defines it. The current `docker-compose.yml` is designed for server deployment (separate api + dashboard services, health checks). A desktop version needs different constraints:
- Both services in ONE container (simpler lifecycle)
- Port mapping to avoid conflicts (user may have other Docker services)
- Host volume path overrides (Windows: `C:\Users\...` vs Linux: `~/A3/`)

**Fix:** Add a section defining `docker-compose.desktop.yml` with merged single-container approach OR define overrides for the existing compose file.

---

## Issue 3: Data path inconsistency — `~/A3/` vs `%APPDATA%/A3/`

**Severity: MEDIUM**

Section 1.1 diagram says `~/A3/` (Unix path). Section 3.3 says `%APPDATA%/A3/` (Windows path). Section 7.1 uses `%APPDATA%`. These are inconsistent and the design doesn't address platform detection.

**Fix:** Define platform-specific paths clearly in one table.

---

## Issue 4: Over-detailed implementation for design phase

**Severity: LOW**

Section 2.2 includes full JavaScript `ContainerManager` class and `WindowManager` class. Section 2.3 defines all IPC channel names. This is implementation code, not design. The user said "先设计后开发" — this should be architecture diagrams and component specs, not runnable code.

**Fix:** Move pseudocode to an appendix or simplify to interface descriptions. Keep design focused on WHAT, not HOW.

---

## Issue 5: No handling of "Docker not running" scenario

**Severity: HIGH**

The most common user failure mode: user installs A3 Desktop, clicks the icon, but Docker Desktop isn't running. The design mentions `_checkDocker()` but doesn't specify what happens next. Does the app show an error? Try to start Docker? Guide the user?

**Fix:** Add a "Docker Prerequisites" section with user-facing error screens and recovery flows.

---

## Issue 6: Dual update mechanism not integrated

**Severity: MEDIUM**

The Electron shell updates via `electron-updater` (GitHub Releases). The Docker image updates via `docker pull`. These are two completely separate mechanisms. If the Electron shell updates to v1.1.0 but the Docker image is still v1.0.0, the app breaks.

**Fix:** Define a version compatibility matrix and a unified update strategy. Consider embedding the expected Docker image tag in the Electron release.

---

## Issue 7: Single-container vs multi-container confusion

**Severity: MEDIUM**

Current `docker-compose.yml` runs TWO containers (`api` + `dashboard`). The desktop version has them communicating via Docker network. But for a desktop app, running two containers is overkill — one container with both uvicorn + streamlit (like `start.sh`) is simpler. The design doesn't clarify which approach to use.

**Fix:** Either define a single-container `docker-compose.desktop.yml` with merged services, or explicitly keep the two-container approach with justification.

---

## Summary

| Issue | Severity | Action |
|:------|:---------|:-------|
| 1. Electron without justification | HIGH | Add technology evaluation section |
| 2. Missing desktop compose file | MEDIUM | Define `docker-compose.desktop.yml` |
| 3. Path inconsistency | MEDIUM | Platform-specific path table |
| 4. Over-detailed code | LOW | Simplify to interface descriptions |
| 5. Docker not running | HIGH | Add prerequisite handling flow |
| 6. Dual update mechanism | MEDIUM | Unified version strategy |
| 7. Container count confusion | MEDIUM | Clarify single vs multi container |
