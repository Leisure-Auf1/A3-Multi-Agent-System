# Repository Extraction Boundary — Readiness Audit

> **Generated:** 2026-07-17 | **Phase:** 6.0 freeze | **Tests:** 1000
>
> This document defines the exact extraction boundary between
> Veritas-Core (Framework) and A3-Multi-Agent-System (Application).
> Every file in `src/` is classified with its post-extraction
> ownership and migration plan.

---

## 1. File Classification — Complete Map

### Legend

| Symbol | Meaning |
|:------:|:--------|
| 🟦 **V** | Veritas Framework — moves to Veritas-Core |
| 🟩 **A** | A3 Application — stays in A3 |
| 🟨 **S** | Shared/Undecided — needs decision before Phase 2 |
| 🔴 **B** | Blocker — imports cross-boundary, must be resolved |
| ⬜ **X** | Exclude — deprecated, docs-only, or empty stub |

---

### 1.1 Runtime Engine (All → V)

| File | Owner | Notes |
|:-----|:-----:|:------|
| `src/runtime/state.py` | 🟦 V | AgentState enum |
| `src/runtime/transition.py` | 🟦 V | StateTransition, TransitionTable |
| `src/runtime/runtime.py` | 🟦 V | RuntimeEngine, RuntimeContext |
| `src/runtime/checkpoint.py` | 🟦 V | RuntimeCheckpoint |
| `src/runtime/hooks.py` | 🟦 V | RuntimeHook base, CompositeHook |
| `src/runtime/events.py` | 🟦 V | RuntimeEvent, RuntimeEventBus |
| `src/runtime/observer.py` | 🟦 V | RuntimeObserver |
| `src/runtime/metrics.py` | 🟦 V | RuntimeMetrics |
| `src/runtime/snapshot.py` | 🟦 V | RuntimeSnapshot, RuntimeBus |
| `src/runtime/store.py` | 🟦 V | RuntimeStore, SessionRecord |
| `src/runtime/__init__.py` | 🟦 V | Public exports |

### 1.2 Runtime Intelligence (All → V)

| File | Owner | Notes |
|:-----|:-----:|:------|
| `src/runtime/analyzer.py` | 🟦 V | RuntimeAnalyzer, HealthReport |
| `src/runtime/failure_detector.py` | 🟦 V | FailureDetector, FailureEvent |
| `src/runtime/policy.py` | 🟦 V | RuntimePolicyEngine |
| `src/runtime/decision.py` | 🟦 V | RuntimeDecision, DecisionLog |

### 1.3 Runtime Recovery (All → V)

| File | Owner | Notes |
|:-----|:-----:|:------|
| `src/runtime/recovery/strategy.py` | 🟦 V | RecoveryStrategy, RecoveryConfig |
| `src/runtime/recovery/checkpoint_manager.py` | 🟦 V | CheckpointManager |
| `src/runtime/recovery/recovery.py` | 🟦 V | RecoveryManager, ProviderFallback |
| `src/runtime/recovery/__init__.py` | 🟦 V | |

### 1.4 Runtime Lifecycle (All → V)

| File | Owner | Notes |
|:-----|:-----:|:------|
| `src/runtime/lifecycle/lifecycle.py` | 🟦 V | AgentLifecycle, LifecycleManager |
| `src/runtime/lifecycle/session.py` | 🟦 V | RuntimeSession |
| `src/runtime/lifecycle/__init__.py` | 🟦 V | |

### 1.5 Runtime Explainability (All → V)

| File | Owner | Notes |
|:-----|:-----:|:------|
| `src/runtime/explain/trace.py` | 🟦 V | DecisionTrace, DecisionReason |
| `src/runtime/explain/recorder.py` | 🟦 V | ExplanationRecorder |
| `src/runtime/explain/__init__.py` | 🟦 V | |

### 1.6 Runtime Plugins (All → V)

| File | Owner | Notes |
|:-----|:-----:|:------|
| `src/runtime/plugins/base.py` | 🟦 V | RuntimePlugin ABC |
| `src/runtime/plugins/registry.py` | 🟦 V | PluginRegistry |
| `src/runtime/plugins/loader.py` | 🟦 V | PluginLoader |
| `src/runtime/plugins/bridge.py` | 🟦 V | PluginHookBridge |
| `src/runtime/plugins/manager.py` | 🟦 V | PluginManager |
| `src/runtime/plugins/__init__.py` | 🟦 V | |

### 1.7 Runtime Distributed (All → V)

| File | Owner | Notes |
|:-----|:-----:|:------|
| `src/runtime/distributed/node.py` | 🟦 V | RuntimeNode, NodeStatus |
| `src/runtime/distributed/registry.py` | 🟦 V | NodeRegistry |
| `src/runtime/distributed/event_bus.py` | 🟦 V | DistributedEventBus |
| `src/runtime/distributed/remote.py` | 🟦 V | RemoteExecutionManager |
| `src/runtime/distributed/trace_collector.py` | 🟦 V | DistributedTraceCollector |
| `src/runtime/distributed/__init__.py` | 🟦 V | |

### 1.8 SDK (All → V)

| File | Owner | Notes |
|:-----|:-----:|:------|
| `src/sdk/client.py` | 🟦 V | RuntimeClient |
| `src/sdk/contracts/task.py` | 🟦 V | TaskRequest, TaskResult, SessionInfo |
| `src/sdk/contracts/__init__.py` | 🟦 V | |
| `src/sdk/config/loader.py` | 🟦 V | RuntimeConfig, ConfigLoader |
| `src/sdk/config/__init__.py` | 🟦 V | |
| `src/sdk/adapters/runtime_adapter.py` | 🟦 V | RuntimeAdapter |
| `src/sdk/exceptions.py` | 🟦 V | VeritasError hierarchy |
| `src/sdk/__init__.py` | 🟦 V | |

### 1.9 Security (All → V)

| File | Owner | Notes |
|:-----|:-----:|:------|
| `src/security/__init__.py` | 🟦 V | |
| `src/security/permission.py` | 🟦 V | PermissionMatrix |
| `src/security/tool_gateway.py` | 🟦 V | ToolGateway — imports RuntimeHook |
| `src/security/prompt_guard.py` | 🟦 V | PromptGuard |
| `src/security/audit.py` | 🟦 V | AuditLogger |

### 1.10 Memory (All → V)

| File | Owner | Notes |
|:-----|:-----:|:------|
| `src/memory/__init__.py` | 🟦 V | |
| `src/memory/memory_manager.py` | 🟦 V | MemoryManager |
| `src/memory/student_memory.py` | 🟦 V | StudentMemory (generic) |
| `src/memory/experience_memory.py` | 🟦 V | ExperienceMemory |
| `src/memory/experience_extractor.py` | 🟦 V | ExperienceExtractor |

### 1.11 Benchmark (All → V)

| File | Owner | Notes |
|:-----|:-----:|:------|
| `src/benchmark/__init__.py` | 🟦 V | |
| `src/benchmark/scenarios.py` | 🟦 V | FailureScenario, FailureInjector |
| `src/benchmark/metrics.py` | 🟦 V | BenchmarkMetrics, ExplainabilityMetrics |
| `src/benchmark/runner.py` | 🟦 V | BenchmarkRunner |
| `src/benchmark/reporter.py` | 🟦 V | BenchmarkReporter |

### 1.12 A3 Agents (All → A)

| File | Owner | Notes |
|:-----|:-----:|:------|
| `src/agents/__init__.py` | 🟩 A | |
| `src/agents/profile_agent.py` | 🟩 A | |
| `src/agents/planner_agent.py` | 🟩 A | |
| `src/agents/reflection_agent.py` | 🟩 A | |
| `src/agents/resource_agent.py` | 🟩 A | |
| `src/agents/resource_generation_agent.py` | 🟩 A | |
| `src/agents/resource_recommendation_agent.py` | 🟩 A | |
| `src/agents/conversation_profile_agent.py` | 🟩 A | |

### 1.13 A3 Workflow (All → A)

| File | Owner | Notes |
|:-----|:-----:|:------|
| `src/workflow/__init__.py` | 🔴 B | **BLOCKER** — imports RuntimeEngine, RuntimeContext, AgentState |
| `src/workflow/result.py` | 🟩 A | WorkflowResult |

### 1.14 A3 API (All → A)

| File | Owner | Notes |
|:-----|:-----:|:------|
| `src/api/__init__.py` | 🟩 A | |
| `src/api/server.py` | 🟩 A | |
| `src/api/dependencies.py` | 🟩 A | |
| `src/api/schemas.py` | 🟩 A | |
| `src/api/routes/__init__.py` | 🟩 A | |
| `src/api/routes/learning.py` | 🟩 A | |
| `src/api/routes/runtime.py` | 🔴 B | **BLOCKER** — imports RuntimeBus, RuntimeSnapshot |

### 1.15 Shared / Undecided

| File | Owner | Notes |
|:-----|:-----:|:------|
| `src/core/event_bus.py` | 🟨 S | AgentEventBus — used by both layers |
| `src/core/meta_reflector.py` | 🟨 S | MetaReflectorAgent |
| `src/core/meta_reflection_adapter.py` | 🟨 S | MetaReflectionAdapter |
| `src/core/llm_agent_adapter.py` | 🟨 S | LLMAgentAdapter |
| `src/core/provider_factory.py` | 🟨 S | Re-exports from llm (deprecated) |
| `src/core/review_gate.py` | 🟨 S | ReviewGateManager |
| `src/core/decision_explainer.py` | 🟨 S | DecisionExplainer |
| `src/core/agent_router.py` | 🟨 S | AgentRouter |
| `src/core/agent_trace.py` | 🟨 S | Trace collector |
| `src/core/event_trace.py` | 🟨 S | Event trace |
| `src/core/feedback_loop.py` | 🟨 S | |
| `src/core/improvement_loop.py` | 🟨 S | |
| `src/core/contracts.py` | 🟨 S | |
| `src/core/user_simulation.py` | 🟨 S | |
| `src/core/sandbox.py` | 🟨 S | |
| `src/core/course_kb_loader.py` | 🟩 A | A3-specific course data |
| `src/core/content_agent.py` | 🟩 A | A3 content agent |
| `src/core/prompt_injector.py` | 🟩 A | A3 prompt |
| `src/core/quarantine.py` | 🟩 A | A3 quarantine |
| `src/core/reverse_committer.py` | 🟩 A | A3 reverse commit |
| `src/llm/provider.py` | 🟦 V | LLMProvider ABC |
| `src/llm/factory.py` | 🟦 V | create_provider, FallbackChain |
| `src/llm/mock_provider.py` | 🟦 V | |
| `src/llm/openai_provider.py` | 🟦 V | |
| `src/llm/deepseek_provider.py` | 🟦 V | |
| `src/llm/rule_provider.py` | 🟦 V | |
| `src/llm/xunfei_provider.py` | 🟦 V | |
| `src/llm/__init__.py` | 🟦 V | |
| `src/evaluation/evaluator.py` | 🟨 S | EvaluationManager |
| `src/evaluation/judge.py` | 🟨 S | |
| `src/evaluation/agent_evaluator.py` | 🟨 S | |
| `src/evaluation/review_adapter.py` | 🟨 S | |
| `src/evaluation/__init__.py` | 🟨 S | |
| `src/rag/` (4 files) | 🟩 A | TF-IDF retriever (app-specific) |
| `src/profile/` | 🟩 A | Student profile |
| `src/council/` | 🟩 A | Agent council |
| `src/knowledge_graph/` | 🟩 A | Knowledge graph |
| `src/multimodal/` | ⬜ X | Empty stub |
| `src/evolution/` | ⬜ X | Empty stub |
| `src/data/` | ⬜ X | Not present |
| `src/v4_integration.py` | 🟩 A | Migration docs |
| `src/__init__.py` | ⬜ X | Empty |

---

## 2. Import Dependency Graph

### 2.1 Current Status

```
97 total `from src.` import lines across 124 .py files.

Framework layer (V): 82 imports — all internal or within V boundary
Application layer (A): 11 imports — all within A boundary
Cross-boundary:        4 imports — THE BLOCKERS
```

### 2.2 Cross-Boundary Imports (BLOCKERS)

These must be resolved before Veritas-Core can be a separate package:

| # | File | Import | Resolution |
|:--|:-----|:-------|:-----------|
| 🔴1 | `src/workflow/__init__.py:544` | `from src.runtime import RuntimeEngine, RuntimeContext` | Replace with `from veritas import RuntimeClient` (SDK) |
| 🔴2 | `src/workflow/__init__.py:602` | `from src.runtime import AgentState` | Replace with `from veritas.runtime import AgentState` |
| 🔴3 | `src/api/routes/runtime.py:19` | `from src.runtime.snapshot import RuntimeBus, RuntimeSnapshot` | Replace with `from veritas.runtime import RuntimeBus, RuntimeSnapshot` |
| 🔴4 | `src/workflow/__init__.py` | `from src.memory import ...` | Replace with `from veritas.memory import ...` |

**Resolution effort: 2 files, ~4 import lines. Very low migration cost.**

### 2.3 Internal Imports (No Action Needed)

All imports within the Veritas boundary use relative imports (`.state`, `.hooks`, etc.) or same-package imports (`from src.runtime import ...` within `src/runtime/`). These continue to work after extraction — only the package root changes (`src/` → `veritas/`).

### 2.4 Dependency Direction Verification

```
✅ Veritas-Core does NOT import A3 agents
✅ Veritas-Core does NOT import A3 workflow
✅ Veritas-Core does NOT import A3 API
✅ Veritas-Core does NOT import A3 evaluation
❌ A3 workflow imports Veritas runtime (4 lines — fixable)
```

---

## 3. Migration Blockers

### 3.1 Package Name

| Blocker | Detail | Resolution |
|:--------|:-------|:-----------|
| Package root is `src/` | Python package resolution expects `src` as root | Change to `veritas/` or use namespace package |
| `from src.runtime import X` | 97 import lines use `src.` prefix | Automated sed: `s/from src\./from veritas./` |
| Relative imports (`.state`) | 50+ relative imports within runtime | Continue to work under new package root |

### 3.2 Test Paths

| Blocker | Detail | Resolution |
|:--------|:-------|:-----------|
| 17 framework test files | Tests import `from src.runtime import ...` | Move to Veritas-Core + update imports |
| `sys.path.insert(0, "..")` in tests | Hardcoded path manipulation | Replace with proper package install |
| Shared test fixtures | Some tests share fixtures across layers | Split fixtures or use conftest.py per repo |

### 3.3 Config & Build

| Blocker | Detail | Resolution |
|:--------|:-------|:-----------|
| No `pyproject.toml` | A3 uses bare `requirements.txt` | Add `pyproject.toml` to Veritas-Core |
| `Makefile` | `python -m pytest tests/` assumes single test directory | Split Makefile or use tox |
| No version pinning | A3 has no version for runtime | Pin `veritas-core>=1.0.0,<2.0.0` |

### 3.4 CI / CD

| Blocker | Detail | Resolution |
|:--------|:-------|:-----------|
| Single CI pipeline | GitHub Actions runs all 1000 tests together | Add Veritas-Core CI, A3 CI depends on Veritas |
| No package publishing | No release workflow exists | Add `gh release create` to Veritas-Core CI |
| Render deployment | `render.yaml` deploys A3 as monolith | Update to install veritas-core as dependency |

### 3.5 Data Files

| Blocker | Detail | Resolution |
|:--------|:-------|:-----------|
| `storage/memory/students/*.json` | Test data files modified frequently | Move to `tests/fixtures/` in Veritas-Core |
| `knowledge_base/` | Course knowledge base | Stays in A3 |
| `requirements.txt` | Lists all deps (mixed framework + app) | Split: veritas-core has minimal deps, A3 adds app deps |

---

## 4. Extraction Order

### Phase A: Copy Framework Code (Zero Breakage)

**Goal:** Veritas-Core has all framework code, A3 still works unchanged.

```
Actions:
  1. Create veritas/ package structure in Veritas-Core
  2. Copy src/runtime/ → Veritas-Core/src/veritas/runtime/
  3. Copy src/sdk/     → Veritas-Core/src/veritas/sdk/
  4. Copy src/security/ → Veritas-Core/src/veritas/security/
  5. Copy src/memory/   → Veritas-Core/src/veritas/memory/
  6. Copy src/benchmark/ → Veritas-Core/src/veritas/benchmark/
  7. Copy src/llm/      → Veritas-Core/src/veritas/llm/
  8. Copy framework tests → Veritas-Core/tests/
  9. Update ALL imports: s/from src\./from veritas./

  A3: UNCHANGED (still has original src/runtime/, still works)
  Veritas-Core: has all code, passes its own tests
```

### Phase B: Establish Veritas Package

**Goal:** `pip install veritas-core` works, independently testable.

```
Actions:
  1. Add pyproject.toml to Veritas-Core
  2. Add setup.cfg / MANIFEST.in
  3. Run: pip install -e .
  4. Verify: from veritas import RuntimeClient
  5. Run: pytest tests/ (Veritas-Core only)
  6. Tag: v1.0.0-alpha
  7. Publish: GitHub Release / PyPI

  A3: STILL UNCHANGED
  Veritas-Core: independently installable and testable
```

### Phase C: A3 Migration

**Goal:** A3 depends on Veritas-Core, old runtime code removed.

```
Actions:
  1. Add veritas-core to A3 requirements.txt
  2. Fix 4 cross-boundary imports (see §2.2):
     a. src/workflow/__init__.py → use veritas.sdk
     b. src/api/routes/runtime.py → use veritas.runtime
  3. Remove migrated code from A3:
     rm -r src/runtime/ src/sdk/ src/security/ src/memory/ src/benchmark/ src/llm/
  4. Move framework tests from A3 → Veritas-Core
  5. Run A3 tests: pytest tests/ (application tests only)

  A3: depends on veritas-core, only app code remains
  Veritas-Core: unchanged
```

### Phase D: Cleanup

**Goal:** Remove deprecated files, update docs.

```
Actions:
  1. Remove src/core/provider_factory.py (deprecated re-export)
  2. Update A3 README — link to Veritas-Core
  3. Update Terence-Agent skills — reference Veritas-Core SDK
  4. Update CI configs for dual-repo setup
  5. Tag A3 as v4.0.0 (post-extraction)
  6. Tag Veritas-Core as v1.0.0 (stable)
```

---

## 5. Summary

### File Counts

| Layer | Files | Owner |
|:------|:-----:|:-----:|
| Runtime Engine | 37 | 🟦 Veritas |
| SDK | 8 | 🟦 Veritas |
| Security | 5 | 🟦 Veritas |
| Memory | 5 | 🟦 Veritas |
| Benchmark | 5 | 🟦 Veritas |
| LLM Providers | 8 | 🟦 Veritas |
| **Framework subtotal** | **68** | **→ Veritas-Core** |
| A3 Agents | 9 | 🟩 A3 |
| A3 Workflow | 2 | 🟩 A3 |
| A3 API | 7 | 🟩 A3 |
| A3 RAG | 4 | 🟩 A3 |
| A3 Other (council, kg, profile, v4) | 8 | 🟩 A3 |
| **Application subtotal** | **30** | **→ stays in A3** |
| Shared / Undecided (core, evaluation) | 22 | 🟨 TBD |
| Empty / Exclude | 4 | ⬜ Skip |
| **Total** | **124** | |

### Migration Complexity

| Dimension | Score | Notes |
|:----------|:-----:|:------|
| Cross-boundary imports | **4 lines** | Only 2 files need changes |
| Files to move | **68** | All clearly owned by Veritas |
| Test files to split | **17 + 7 + 13** | Framework + App + Shared |
| Import migration effort | **LOW** | Automated sed + test suite |
| Risk of regression | **LOW** | SDK layer already provides stable API |
| Blockers | **2 files** | `src/workflow/__init__.py`, `src/api/routes/runtime.py` |

### Verdict: READY for Phase A

The extraction boundary is clean. The framework layer has zero dependencies on the application layer. Only 4 import lines cross the boundary, all in 2 files. The SDK (Phase 6.0) already provides the stable public API that A3 should use. **Extraction can proceed immediately.**
