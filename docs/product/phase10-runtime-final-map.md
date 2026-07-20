# Phase 10.4-A — Runtime Governance Verification

> **Date**: 2026-07-20
> **Audit SHA**: `c4bb2b0` (A3-Multi-Agent-System, HEAD)
> **Test Baseline**: 2512 tests, 0 failures
> **Phase**: 10.4-A (Read-Only Audit)

---

## 1. Target Runtime Path

### POST /api/v2/learning/run — Actual Call Chain

```
User Request (Bearer Token)
    │
    ▼
Auth (require_auth)
    │ src/auth/middleware.py:20
    │ └─ Validates JWT token → AuthUser
    │
    ▼
TokenBudget (TokenBudgetManager)
    │ src/platform/token_budget.py:24
    │ └─ check_available(tokens=500) → raises 429 if exceeded
    │
    ▼
Permission (Role Check)
    │ src/user/permission.py
    │ └─ Free → rule-only; PRO/TEACHER/ADMIN → LLM-enabled
    │
    ▼
LearningPipelineService.run()
    │ src/services/learning_pipeline.py:48
    │ └─ Creates A3Workflow → calls workflow.run()
    │
    ▼
A3Workflow.run()
    │ src/workflow/__init__.py:102
    │ └─ ProfileAgent → PlannerAgent → ContentGeneratorAgent
    │     → ResourceAgent → ReviewGate → ReflectionAgent → Memory
    │
    ▼
EventBus (emit per step)
    │ src/core/event_bus.py
    │ └─ Timestamped events: ProfileAgent, PlannerAgent, etc.
    │
    ▼
TraceCollector
    │ src/core/event_trace.py
    │ └─ Collects full timeline → result.trace
    │
    ▼
MemoryManager
    │ veritas/memory
    │ └─ Saves experience + profile to persistent store
    │
    ▼
Response → JSON (PipelineRunResponse)
```

**Status**: ✅ Intact. Auth → Permission → TokenBudget → LearningPipelineService → A3Workflow chain verified.

---

## 2. Prohibited Items Scan

| Item | Status | Evidence |
|:-----|:-------|:---------|
| **PipelineExecutor** | ✅ DELETED | `test_product_runtime.py:111` — assert not in source; `test_runtime_consolidation.py:471` — confirm removed |
| **Direct Agent Call** | ❌ FOUND | `src/api/v2/learning.py:64` — `PlannerAgent()` called directly, bypassing A3Workflow |
| **New Runtime Class** | ⚠️ UNUSED | `OrchestratorRuntime` (463 lines) at `src/orchestration/runtime.py` — exists but not wired into any API route |

---

## 3. API Route Inventory

### v2 Routes (Production)

| Endpoint | File | Auth | A3Workflow |
|:---------|:-----|:----:|:----------:|
| `POST /api/v2/auth/register` | `src/api/routes/auth.py` | ❌ | N/A |
| `POST /api/v2/auth/login` | `src/api/routes/auth.py` | ❌ | N/A |
| `POST /api/v2/auth/logout` | `src/api/routes/auth.py` | ✅ | N/A |
| `GET /api/v2/auth/me` | `src/api/routes/auth.py` | ✅ | N/A |
| **`POST /api/v2/learning/run`** | `src/api/v2/pipeline.py` | ✅ | ✅ |
| `POST /api/v2/learning/plan` | `src/api/v2/learning.py` | ✅ | ❌ direct call |
| `GET /api/v2/learning/history` | `src/api/v2/learning.py` | ✅ | N/A |
| `GET /api/v2/learning/stats` | `src/api/v2/learning.py` | ✅ | N/A |
| `GET /api/v2/profile` | `src/api/v2/profile.py` | ✅ | N/A |
| `PUT /api/v2/profile` | `src/api/v2/profile.py` | ✅ | N/A |
| `POST /api/v2/profile/assess` | `src/api/v2/profile.py` | ✅ | N/A |
| `POST /api/v2/chat/message` | `src/api/v2/chat.py` | ✅ | N/A |
| `GET /api/v2/resources/*` | `src/api/v2/resources.py` | ✅ | N/A |
| `POST /api/v2/evaluation/*` | `src/api/v2/evaluation.py` | ✅ | N/A |
| `POST /api/v2/users` | `src/api/v2/users.py` | ✅ | N/A |
| `GET /api/v2/settings/llm` | `src/api/v2/settings.py` | ✅ | N/A |

### v1 Routes (Legacy — NO AUTH)

| Endpoint | File | Auth | Risk |
|:---------|:-----|:----:|:-----|
| `POST /api/v1/learning/plan` | `src/api/routes/learning.py` | ❌ | 🔴 **HIGH** — Unauthenticated A3Workflow access |
| `GET /api/v1/runtime/snapshot` | `src/api/routes/runtime.py` | ❌ | 🟡 MEDIUM — Runtime state exposed |
| `GET /api/v1/runtime/metrics` | `src/api/routes/runtime.py` | ❌ | 🟡 MEDIUM — Runtime metrics exposed |
| `GET /api/v1/runtime/timeline` | `src/api/routes/runtime.py` | ❌ | 🟡 MEDIUM |
| `GET /api/v1/runtime/events` | `src/api/routes/runtime.py` | ❌ | 🟡 MEDIUM |
| `GET /api/v1/runtime/state` | `src/api/routes/runtime.py` | ❌ | 🟡 MEDIUM |
| `POST /api/v1/runtime/reset` | `src/api/routes/runtime.py` | ❌ | 🔴 **HIGH** — Unauthenticated runtime reset |

---

## 4. Architecture Issues

| # | Issue | Severity | Description |
|:--|:------|:---------|:------------|
| 1 | **v1 routes unauthenticated** | 🔴 HIGH | 4 endpoints at `/api/v1/runtime/*` + `/api/v1/learning/*` have ZERO auth — any caller can invoke A3Workflow or reset runtime |
| 2 | **v2 learning/plan bypasses A3Workflow** | 🟡 MEDIUM | `src/api/v2/learning.py:64` calls `PlannerAgent()` directly instead of routing through `LearningPipelineService` → `A3Workflow` |
| 3 | **Duplicate router prefix** | 🟢 LOW | Both `pipeline.py` and `learning.py` register `prefix="/api/v2/learning"` — FastAPI tolerates this but it's architecturally confusing |
| 4 | **OrchestratorRuntime dead code** | 🟢 LOW | 463 lines at `src/orchestration/runtime.py` — never instantiated in any API endpoint |

---

## 5. Component Location Map

| Component | Location | Lines | Status |
|:----------|:---------|:-----:|:------|
| A3Workflow | `src/workflow/__init__.py` | 1002 | ✅ Active |
| LearningPipelineService | `src/services/learning_pipeline.py` | 192 | ✅ Active |
| OrchestratorRuntime | `src/orchestration/runtime.py` | 463 | ⚠️ Unused |
| PipelineExecutor | `src/api/v2/pipeline.py` (removed) | — | ✅ Deleted |
| TokenBudget | `src/platform/token_budget.py` | ~100 | ✅ Active |
| PermissionManager | `src/user/permission.py` | ~150 | ✅ Active |
| Auth Middleware | `src/auth/middleware.py` | 166 | ✅ Active |
| EventBus | `src/core/event_bus.py` | — | ✅ Active |
| TraceCollector | `src/core/event_trace.py` | — | ✅ Active |
| MemoryManager | `veritas/memory/` | — | ✅ Active |

---

## 6. Known Limitations

1. **v1 routes** should be either migrated to v2 with auth, or deprecated + auth-protected
2. `POST /api/v2/learning/plan` should route through `LearningPipelineService` → `A3Workflow`, not call `PlannerAgent()` directly
3. `OrchestratorRuntime` should be either wired into the pipeline or removed
4. Dual `/api/v2/learning` router prefix should be consolidated into a single router

---

*End of Phase 10.4-A Audit*
