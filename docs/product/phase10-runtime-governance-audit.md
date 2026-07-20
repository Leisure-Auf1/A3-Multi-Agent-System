# Phase 10.3 — Runtime Governance Audit

> **Type**: READ-ONLY audit  
> **Date**: 2026-07-20  
> **Baseline**: 2478 tests, 0 regression  
> **Scope**: Trace execution path through ALL runtime layers

---

## 1. Current Execution Architecture

There are currently **THREE runtime layers** in the codebase:

| Layer | File | Purpose | Used By |
|-------|------|---------|---------|
| **A3Workflow** | `src/workflow/__init__.py` | Full agent pipeline orchestration | `web/app_v3.py`, `web/legacy/` |
| **OrchestratorRuntime** | `src/orchestration/runtime.py` | Per-model-call orchestration (select/fallback/cost) | No API endpoint currently uses it |
| **PipelineExecutor** | `src/api/v2/pipeline.py` | Minimal pipeline (NEW, Phase 10.2) | `POST /api/v2/learning/run` |

### 1.1 Verification: Does PipelineExecutor use OrchestratorRuntime?

**NO.** The docstring header claims `API → Auth → Permission → OrchestratorRuntime → Agent Pipeline`, but the code:

```python
# Line 29-36: actual imports
from src.auth.middleware import require_auth    # ← only auth
from src.agents.profile_agent import ProfileAgent   # ← direct agent instantiation
from src.agents.planner_agent import PlannerAgent
from src.agents.resource_agent import ResourceAgent
from src.workspace.manager import WorkspaceManager
from src.data.learning_records import record_agent_action
from src.data.student_store import save_profile
```

The word "OrchestratorRuntime" appears **only in the docstring** — never in imports or code. `grep "OrchestratorRuntime" src/api/v2/pipeline.py` returns 2 hits, both in the docstring.

---

## 2. Call Graph

### 2.1 PipelineExecutor (Phase 10.2)

```
POST /api/v2/learning/run
  │
  ├─ Auth: require_auth ✅
  ├─ Permission: ❌ (not checked)
  ├─ TokenBudget: ❌ (not checked)
  ├─ RateLimit: ❌ (not checked)
  │
  └─ PipelineExecutor.execute(goal, depth)
       │
       ├─ ProfileAgent()     ← NEW instance, no LLM, no EventBus
       ├─ PlannerAgent()     ← NEW instance, no LLM, no EventBus
       ├─ ResourceAgent()    ← NEW instance, no LLM, no EventBus
       ├─ _run_evaluation()  ← inline rule-based, NOT ReviewGate
       └─ _persist_pipeline_result()
            ├─ WorkspaceManager.save_artifact()  ← 5 JSON/MD files
            └─ record_agent_action()             ← best-effort SQLite
```

**Missing from PipelineExecutor:**
- ❌ OrchestratorRuntime
- ❌ EventBus / TraceCollector (no trace_id, no agent events)
- ❌ MemoryManager (no Veritas-Core memory update)
- ❌ ReviewGate (not used; hardcoded rule-based eval)
- ❌ ContentGeneratorAgent (not run at all)
- ❌ ReflectionAgent (not run at all)
- ❌ LLM provider injection

### 2.2 A3Workflow (Phase 4, app_v3 uses it)

```
A3Workflow.run(user_goal)
  │
  ├─ EventBus.get_instance()        ← event recording
  ├─ TraceCollector                  ← trace collection
  │
  ├─ ProfileAgent.extract()          ← LLM-injected if provider set
  ├─ PlannerAgent.plan()             ← LLM-injected
  ├─ ContentGeneratorAgent.generate()← LLM-injected
  ├─ ResourceAgent.recommend()       ← LLM-injected
  ├─ ReviewAgent / ReviewGate        ← quality evaluation
  ├─ ReflectionAgent.reflect()       ← post-execution reflection
  └─ MemoryManager.update_student_memory() ← Veritas-Core persistence
```

**A3Workflow has but PipelineExecutor lacks:**
- EventBus + TraceCollector ✅
- MemoryManager (Veritas-Core) ✅
- ReviewGate ✅
- ContentGeneratorAgent ✅
- ReflectionAgent ✅
- LLM provider wiring across agents ✅

---

## 3. Runtime Ownership Map

```
┌──────────────────────────────────────────────────────────┐
│                      RUNTIME LAYERS                       │
├─────────────────┬──────────────────┬─────────────────────┤
│ A3Workflow      │ Orchestrator     │ PipelineExecutor    │
│ (src/workflow)  │ Runtime          │ (src/api/v2)        │
│                 │ (src/orchestrat) │                     │
├─────────────────┼──────────────────┼─────────────────────┤
│ Purpose:        │ Purpose:         │ Purpose:            │
│ Agent pipeline  │ Per-call model   │ Agent pipeline      │
│ orchestration   │ selection +      │ orchestration       │
│                 │ fallback + cost  │ (DUPLICATE)         │
├─────────────────┼──────────────────┼─────────────────────┤
│ Agents:         │ Agents:          │ Agents:             │
│ 7 (full set)    │ N/A (model only) │ 3 (subset)          │
├─────────────────┼──────────────────┼─────────────────────┤
│ Infra:          │ Infra:           │ Infra:              │
│ EventBus ✅     │ ModelSelector ✅ │ EventBus ❌          │
│ TraceCol ✅     │ FallbackMgr ✅   │ TraceCol ❌          │
│ MemoryMgr ✅    │ CostOptimizer✅  │ MemoryMgr ❌         │
│ ReviewGate ✅   │ DecisionLog ✅   │ ReviewGate ❌        │
│ Reflection ✅   │ RateLimiter ✅   │ RateLimit ❌         │
├─────────────────┼──────────────────┼─────────────────────┤
│ LLM:            │ LLM:             │ LLM:                │
│ Injectable ✅   │ Core function    │ NOT used ❌          │
├─────────────────┼──────────────────┼─────────────────────┤
│ Used by:        │ Used by:         │ Used by:            │
│ app_v3 (legacy) │ NOT used by any  │ /learning/run API   │
│                 │ API endpoint     │                     │
└─────────────────┴──────────────────┴─────────────────────┘
```

**Relationship**: `PipelineExecutor` is a **parallel duplicate** of `A3Workflow`, not a wrapper. It implements a subset of functionality independently, without reusing existing infrastructure.

---

## 4. Security Boundary Audit

### 4.1 What `POST /api/v2/learning/run` checks

| Security Layer | Imported? | Enforced? | Evidence |
|---------------|:---:|:---:|------|
| **Authentication** | ✅ | ✅ | `Depends(require_auth)` (line 277) |
| **Permission** | ❌ | ❌ | No PermissionManager import; any role can call |
| **TokenBudget** | ❌ | ❌ | No TokenBudgetManager import; no daily limit check |
| **RateLimit** | ❌ | ❌ | No UserRateLimiter import; no per-user RPM limit |
| **AuditLog** | ❌ | ❌ | No AuditLogger import; no security event record |
| **RequestContext** | ❌ | ❌ | No build_context; no plan/permission resolution |

### 4.2 Comparison: what chat endpoint checks

```python
# src/api/v2/chat.py line 86:
user: AuthUser = Depends(require_auth),    # ← Auth only
```

Chat endpoint also only checks `require_auth` — same level. But chat is a low-cost operation while pipeline is resource-intensive. Pipeline should have stronger checks.

### 4.3 What should be checked

| Check | Rationale |
|-------|-----------|
| `require_auth` | ✅ Already done |
| `Depends(check_token_limit(500))` | Pipeline consumes tokens across 3+ agents |
| PermissionManager check | Free users may hit provider limits |
| Audit log entry | Pipeline runs should be auditable |

---

## 5. Data Persistence Map

| Artifact | PipelineExecutor | A3Workflow | Owner |
|----------|:---:|:---:|------|
| Profile | `save_profile()` → student_store JSON | Same path | `src/data/student_store.py` |
| Plan | `WorkspaceManager.save_artifact()` → JSON+MD | `WorkspaceManager.save_artifact()` | `src/workspace/manager.py` |
| Resources | `WorkspaceManager` → JSON | `WorkspaceManager` | `src/workspace/manager.py` |
| Teaching Material | ❌ NOT generated | `ContentGeneratorAgent` → Workspace | `src/agents/content_generator_agent.py` |
| Evaluation | inline rule-based score | `ReviewGate.score()` | Duplicated |
| Agent Events | ❌ NOT recorded | `EventBus` → `TraceCollector` | `src/core/event_bus.py` |
| Memory | ❌ NOT updated | `MemoryManager.update_student_memory()` | `veritas/memory/` |
| Reflection | ❌ NOT run | `ReflectionAgent` | `src/agents/reflection_agent.py` |

**Red flag**: The pipeline does NOT call `MemoryManager`, so student learning progress from new pipeline runs is never recorded in Veritas-Core memory. Each run is a fresh start.

---

## 6. Problems Found

### 🔴 P0 — Docstring/Architecture Dishonesty

`pipeline.py` line 7-13 claims the flow goes through `OrchestratorRuntime`, but **OrchestratorRuntime is never imported or called**. The docstring architecture diagram is false advertising.

### 🔴 P0 — Duplicate Runtime System

`PipelineExecutor` is a **3rd runtime** that duplicates agent orchestration with:
- 3 agents instead of 7 (missing ContentGenerator, ReviewGate, Reflection)
- No EventBus (no observability)
- No MemoryManager (no learning persistence)
- No LLM provider injection (rule-only)
- No TraceCollector (no execution timeline)

### 🟡 P1 — Security Bypass

Pipeline endpoint performs **only authentication**. Missing:
- Token budget check (pipeline is token-heavy: 3+ agent calls)
- Permission check (free users shouldn't hit expensive models)
- Rate limit check (pipeline is expensive; should be rate-limited)

### 🟡 P1 — No Memory Update

`MemoryManager` is never called. Student mastery, weak points, session summaries — none of this is updated. Every pipeline run is a fresh start with no learning history.

### 🟢 P2 — OrchestratorRuntime Unused

`OrchestratorRuntime` (463 lines, src/orchestration/runtime.py) with ModelSelector, FallbackManager, CostOptimizer, DecisionLog — **zero API endpoints use it**. It exists but is dead code in the API path.

### 🟢 P2 — No API for pipeline history

`GET /api/v2/learning/run` has no corresponding GET to retrieve past runs. Artifacts are saved to workspace but no API exposes them.

---

## 7. Phase 10.3 Implementation Recommendation

### Step 1: Unify — Replace PipelineExecutor with A3Workflow

```python
# src/api/v2/pipeline.py — refactored
from src.workflow import A3Workflow
from src.orchestration.runtime import OrchestratorRuntime

@router.post("/run")
def run_learning_pipeline(req, user=Depends(require_auth)):
    # Security checks
    check_token_limit(...)        # Phase 10.3 addition
    audit_logger.log(...)         # Phase 10.3 addition

    # Use the proven A3Workflow with student_id from auth
    workflow = A3Workflow(
        student_id=user.id,       # ← REAL user, not "app_v3_user"
        llm_provider=get_provider(),
    )
    result = workflow.run(
        user_goal=req.goal,
        session_id=f"api_{uuid4().hex}",
    )
    return _format_response(result)
```

**Benefits**:
- Eliminates duplicate runtime
- Gains EventBus + TraceCollector + MemoryManager + ReviewGate
- Student learning progress actually persists
- Single code path to maintain

### Step 2: Wire OrchestratorRuntime

Connect `OrchestratorRuntime` into `A3Workflow.run()` — when LLM provider is set, each agent call routes through `runtime.execute()` for model selection + fallback + cost tracking + decision logging.

### Step 3: Add Security Checks

```python
# pipeline endpoint additions:
Depends(require_auth)           # ✅ already have
Depends(check_token_limit(500)) # NEW
Depends(AuditLogger dependency) # NEW
```

### Step 4: Add GET Pipeline History

```python
@router.get("/run/history")
def get_pipeline_history(user=Depends(require_auth)):
    """List user's pipeline runs from workspace + DB."""
```

### Impact Estimate

| Metric | Estimate |
|--------|----------|
| Files modified | `pipeline.py` (refactor), `workflow/__init__.py` (inject orchestrator) |
| Lines changed | ~150 (replace PipelineExecutor, wire orchestrator) |
| Tests | Should remain 40+ with migration path |
| Risk | Low — A3Workflow is battle-tested (1002 lines, used by app_v3) |

---

> **Status**: ⏳ 等待 Human Gate 审批  
> **Next**: Phase 10.3 — Unify runtime, wire OrchestratorRuntime, add security checks
