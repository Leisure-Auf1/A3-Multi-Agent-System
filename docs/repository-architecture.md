# Repository Architecture — Governance Document

> **Version:** 1.0 | **Phase:** 6.0 freeze | **Tests:** 1000 | **Date:** 2026-07-17
>
> This document governs the relationship between the three repositories
> in the Veritas / A3 ecosystem. It is the single source of truth for
> repository responsibilities, dependency direction, and migration planning.

---

## 1. Repository Overview

### 1.1 Terence-Agent

| Property | Value |
|:---------|:------|
| **Repository** | `github.com/Leisure-Auf1/Terence-Agent` |
| **Role** | AI Development Orchestration / Engineering Governance |
| **Type** | Meta-repository (orchestrator) |
| **Contains code?** | No — skills, events, configs only |

**Responsibilities:**

- Define architecture constraints (what can call what)
- Maintain error registry (38 known error codes)
- Log daily event reports (operation timeline)
- Track task progress across projects
- Manage skill registry (41 skill categories)
- Run preflight checks before project work
- Own Agent Team definitions (5 agents)

**Does NOT contain:**

- Runtime engine code
- Application code
- Agent business logic
- Package dependencies

**Key files:**

```
Terence-Agent/
├── architecture-constraints/   # Stack rules, context scoping, error cascade
├── error-registry/             # 38 error codes (L0–L3)
├── event-report/               # Daily operation logs
├── task-progress/              # Cross-session progress tracking
├── skill-manager/              # Skill registry (JSON)
├── agent-team/                 # 5 agent definitions
├── scripts/check-preflight.sh  # 9-step preflight gate
├── sync.sh                     # Skills → markdown sync
└── projects/                   # Stale snapshots (DO NOT USE for development)
```

### 1.2 A3-Multi-Agent-System

| Property | Value |
|:---------|:------|
| **Repository** | `github.com/Leisure-Auf1/A3-Multi-Agent-System` |
| **Role** | Current monolithic implementation |
| **Type** | Application + Runtime (single repo) |
| **Contains code?** | Yes — 37 runtime files, 9 agent modules, SDK, benchmark |

**Responsibilities (Current — pre-extraction):**

- Provide A3 learning application (agents, workflow, dashboard)
- Host ALL Veritas runtime infrastructure (runtime, sdk, security, memory, distributed, benchmark)
- Run 1000 tests covering both layers
- Serve as the single development workspace

**Layers currently co-located:**

```
A3-Multi-Agent-System/
│
├── Framework Layer (future Veritas-Core) ──
│   ├── src/runtime/         (37 files)   ← Phases 4.8–5.9
│   ├── src/sdk/             (8 files)    ← Phase 6.0
│   ├── src/security/        (5 files)    ← Phase 5.3
│   ├── src/memory/          (5 files)    ← Phase 5.1
│   ├── src/benchmark/       (5 files)    ← Phase 5.6
│   └── src/runtime/distributed/ (6 files) ← Phase 5.9
│
├── Application Layer (stays in A3) ──
│   ├── src/agents/          (9 modules)  ← A3-specific
│   ├── src/workflow/        (A3Workflow) ← A3-specific
│   ├── src/api/             (FastAPI)    ← A3-specific
│   └── src/evaluation/      (evaluator)  ← A3-specific
│
└── Shared / Unclassified ──
    ├── src/core/            (EventBus, MetaReflector)
    ├── src/llm/             (Provider abstraction)
    ├── src/rag/             (TF-IDF retriever)
    └── web/                 (Streamlit dashboard)
```

### 1.3 Veritas-Core

| Property | Value |
|:---------|:------|
| **Repository** | `github.com/Leisure-Auf1/Veritas-Core` |
| **Role** | Future standalone Agent Runtime Framework |
| **Type** | Package (framework) |
| **Contains code?** | **No — empty stub** |

**Current state:**

- Repository exists on GitHub
- Contains README.md only (describes intent)
- No `src/` directory
- No packages, no tests, no code
- Referenced by A3 README as "Next Evolution"

**Target state:**

- Standalone Python package: `pip install veritas-core`
- Contains: runtime engine, SDK, security, memory, plugins, distributed, benchmark
- Zero A3-specific code
- Independent release cycle
- Consumed by A3 and future applications

---

## 2. Current Architecture

```
                    ┌──────────────────────────┐
                    │      Terence-Agent        │
                    │   (Orchestration Layer)    │
                    │                           │
                    │  skills/ ──→ documents     │
                    │  events/ ──→ logs progress │
                    │  preflight ──→ gates work  │
                    │                           │
                    │  DOES NOT:                 │
                    │  • import code             │
                    │  • run agents              │
                    │  • contain runtime         │
                    └────────────┬──────────────┘
                                 │
                                 │  references (README links)
                                 │  skills/veritas-core documents patterns
                                 │  event-report/ logs A3 progress
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │  A3-Multi-Agent-System    │
                    │    (Monolithic Repo)       │
                    │                           │
                    │  ┌─────────────────────┐  │
                    │  │  Framework Layer     │  │
                    │  │  (would be Veritas)  │  │
                    │  │  • runtime (37 py)   │  │
                    │  │  • sdk (8 py)        │  │
                    │  │  • security (5 py)   │  │
                    │  │  • memory (5 py)     │  │
                    │  │  • benchmark (5 py)  │  │
                    │  │  • distributed (6 py)│  │
                    │  └─────────────────────┘  │
                    │                           │
                    │  ┌─────────────────────┐  │
                    │  │  Application Layer   │  │
                    │  │  (A3-specific)       │  │
                    │  │  • agents (9 mod)    │  │
                    │  │  • workflow          │  │
                    │  │  • api               │  │
                    │  │  • evaluation        │  │
                    │  └─────────────────────┘  │
                    │                           │
                    │  Tests: 1000 (combined)    │
                    └───────────────────────────┘

                    ┌──────────────────────────┐
                    │      Veritas-Core         │
                    │     (Empty Stub)           │
                    │                           │
                    │  README.md only           │
                    │  No code — target only    │
                    └───────────────────────────┘
```

**Critical observation:** There is zero code-level dependency between any two repositories. Terence-Agent references A3 only in documentation. Veritas-Core has no code to import from. A3 is fully self-contained.

---

## 3. Target Architecture

```
                    ┌──────────────────────────────┐
                    │        Terence-Agent          │
                    │   Architecture Governance      │
                    │                               │
                    │  • owns: architecture rules    │
                    │  • owns: error registry        │
                    │  • owns: skill system          │
                    │  • owns: preflight gates       │
                    │  • validates: dependency rules │
                    │  • validates: ownership rules  │
                    │                               │
                    │  NEVER: imports runtime code   │
                    └──────────────┬───────────────┘
                                   │
                                   │  governance documents
                                   │  skill definitions
                                   │  preflight validation
                                   │
                    ┌──────────────▼───────────────┐
                    │         Veritas-Core          │
                    │   Agent Runtime Framework      │
                    │   pip install veritas-core     │
                    │                               │
                    │  • runtime engine              │
                    │  • public SDK (RuntimeClient)  │
                    │  • plugin system               │
                    │  • security layer              │
                    │  • memory management           │
                    │  • distributed runtime         │
                    │  • benchmark framework         │
                    │  • decision explainability     │
                    │  • recovery system             │
                    │  • lifecycle management        │
                    │                               │
                    │  NEVER: imports A3 agents      │
                    │  NEVER: imports Terence-Agent  │
                    └──────────────┬───────────────┘
                                   │
                                   │  pip install veritas-core
                                   │  from veritas import RuntimeClient
                                   │
                    ┌──────────────▼───────────────┐
                    │    A3-Multi-Agent-System      │
                    │      Application Layer         │
                    │                               │
                    │  • learning agents             │
                    │  • A3 workflow                 │
                    │  • dashboard                   │
                    │  • evaluation pipeline         │
                    │  • recommendation engine       │
                    │                               │
                    │  depends on: veritas-core      │
                    │  NEVER: contains runtime code  │
                    └───────────────────────────────┘
```

---

## 4. Dependency Direction

### 4.1 Allowed Dependencies

```
A3-Multi-Agent-System ──→ Veritas-Core     ✅ ALLOWED
                        (pip install)

A3-Multi-Agent-System ──→ Terence-Agent    ✅ ALLOWED (documentation only)
                        (README links)

Veritas-Core ──→ NONE                      ✅ ALLOWED
               (zero external deps)
```

### 4.2 Forbidden Dependencies

```
Veritas-Core ──→ A3-Multi-Agent-System     ❌ FORBIDDEN
               (framework must not import app code)

Terence-Agent ──→ Any repo code             ❌ FORBIDDEN
               (governance must not import code)

A3 agents ──→ Runtime internals directly    ❌ FORBIDDEN (post-extraction)
           (must use SDK/contract layer)
```

### 4.3 Documentation-Only Relationships

```
Terence-Agent ──→ A3-Multi-Agent-System
  • skills/veritas-core documents A3 runtime patterns
  • event-report/ logs A3 development progress
  • preflight checks reference A3 repo state
  • NO code imports ever
```

---

## 5. Migration Risks

### 5.1 Import Path Migration

| Risk | Severity | Impact |
|:-----|:---------|:-------|
| `from src.runtime import ...` → `from veritas.runtime import ...` | **HIGH** | 37 runtime files × N imports |
| `from src.sdk import ...` → `from veritas.sdk import ...` | MEDIUM | 8 SDK files |
| `from src.security import ...` → `from veritas.security import ...` | MEDIUM | 5 security files |
| Internal relative imports within runtime | **HIGH** | `.state`, `.transition`, `.hooks` — all change |

**Mitigation:** Use automated migration tool (sed/ripgrep + test suite) — not manual edits.

### 5.2 Test Split

| Risk | Severity | Impact |
|:-----|:---------|:-------|
| 1000 combined tests → split across repos | **HIGH** | Must identify which tests belong to which repo |
| Cross-layer tests in A3 | MEDIUM | A3 tests that import runtime directly break after extraction |
| Test fixtures shared between layers | MEDIUM | Runtime fixtures must move to Veritas-Core |

**Mitigation:** Tag tests by layer BEFORE extraction. Run both suites independently.

### 5.3 History Preservation

| Risk | Severity | Impact |
|:-----|:---------|:-------|
| Git history lost during file move | MEDIUM | Phase 4–6 commits contain both runtime and app changes |
| PR history references old file paths | LOW | GitHub PRs reference commit SHAs, not paths |

**Mitigation:** Use `git filter-branch` or `git subtree split` to preserve runtime file history.

### 5.4 Backward Compatibility

| Risk | Severity | Impact |
|:-----|:---------|:-------|
| Phase 6.0 SDK API changes during extraction | LOW | SDK is add-on layer — no breaking change needed |
| RuntimeEngine API changes | MEDIUM | Internal refactoring may be needed during extraction |
| Existing scripts/tools break | MEDIUM | `make test`, CI configs need updating |

**Mitigation:** Phase 6.0 SDK already provides stable public API. Freeze before extraction.

### 5.5 Dual Development

| Risk | Severity | Impact |
|:-----|:---------|:-------|
| Runtime development in both repos simultaneously | **HIGH** | Merge conflicts, duplicate effort |
| A3 team modifies runtime after extraction | **HIGH** | Violates ownership — Veritas-Core must be single source |

**Mitigation:** After extraction, A3 runtime code is READ-ONLY. All runtime changes go to Veritas-Core.

---

## 6. Undecided / Shared Components

These components currently live in A3 but their final ownership is unclear:

| Component | Current Location | Question |
|:----------|:-----------------|:---------|
| `src/core/` | A3 | EventBus, MetaReflector — are these runtime or app? |
| `src/llm/` | A3 | Provider abstraction — used by both runtime and agents |
| `src/rag/` | A3 | TF-IDF retriever — application-specific? |
| `web/dashboard.py` | A3 | Streamlit — application UI or framework tool? |
| `src/evaluation/` | A3 | EvaluationManager — framework or app? |

**Decision needed before Phase 6.3 extraction.**

---

## 7. Validation Checklist

Before any extraction, verify:

- [ ] `docs/ownership-rules.yaml` exists and is complete
- [ ] `docs/veritas-extraction-plan.md` exists and is approved
- [ ] All 1000 tests pass in current state
- [ ] Imports map generated (`grep -rn "from src\." src/`)
- [ ] Tests tagged by layer (framework vs application)
- [ ] Phase 6.0 SDK API is frozen (no breaking changes)
- [ ] Veritas-Core repo has package scaffolding ready
- [ ] CI/CD configs prepared for dual-repo setup
