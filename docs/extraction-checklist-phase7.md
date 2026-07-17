# Phase 7.0 Extraction Checklist

> **Date:** 2026-07-17 | **Tests pre-extraction:** 1042 passed ✅  
> **Target:** Veritas-Core standalone repo with preserved git history

---

## Phase 0: Pre-extraction Verification ✅

- [x] All 1042 tests pass (A3-Multi-Agent-System)
- [x] extraction-boundary.md classified all 124 .py files
- [x] Only 4 cross-boundary imports (2 files)
- [x] SDK layer (Phase 6.0) provides stable public API
- [x] governance docs exist (repo-architecture, ownership-rules, extraction-plan)
- [x] Workspace clean (SHA: 8ab7f87, main branch)

---

## Phase 1: Package Structure

- [ ] Clone Veritas-Core from GitHub
- [ ] Set up A3 as remote for history access
- [ ] Create `pyproject.toml` with package metadata
- [ ] Create `setup.py` for `pip install -e`
- [ ] Create `veritas/__init__.py` (public namespace)
- [ ] Create `requirements.txt` (minimal deps)

---

## Phase 2: Code Migration (git history preserved)

**Files to migrate (68 total):**

### Runtime (37 files)
- [ ] `src/runtime/` — state, transition, runtime, checkpoint, hooks
- [ ] `src/runtime/` — events, observer, metrics, snapshot, store
- [ ] `src/runtime/` — analyzer, failure_detector, policy, decision
- [ ] `src/runtime/recovery/` — strategy, checkpoint_manager, recovery
- [ ] `src/runtime/lifecycle/` — lifecycle, session
- [ ] `src/runtime/explain/` — trace, recorder
- [ ] `src/runtime/plugins/` — base, registry, loader, bridge, manager
- [ ] `src/runtime/distributed/` — node, registry, event_bus, remote, trace_collector

### SDK (8 files)
- [ ] `src/sdk/` — client, contracts/, config/, adapters/, exceptions

### Security (5 files)
- [ ] `src/security/` — permission, tool_gateway, prompt_guard, audit

### Memory (5 files)
- [ ] `src/memory/` — memory_manager, student_memory, experience_memory, experience_extractor

### Benchmark (5 files)
- [ ] `src/benchmark/` — scenarios, metrics, runner, reporter

### CLI (directory)
- [ ] `src/cli/` — veritas CLI commands

### LLM (8 files)
- [ ] `src/llm/` — provider, factory, mock_provider, openai_provider, deepseek_provider, rule_provider, xunfei_provider

### Shared (undecided, to be evaluated)
- [ ] `src/core/event_bus.py` — AgentEventBus (shared)
- [ ] `src/core/meta_reflector.py` — MetaReflectorAgent
- [ ] `src/core/meta_reflection_adapter.py`
- [ ] `src/core/llm_agent_adapter.py`
- [ ] `src/core/review_gate.py`
- [ ] `src/core/decision_explainer.py`

**Method:** `git filter-branch --tree-filter` to remove A3 files from Veritas-Core, rename `src/` → `veritas/`

---

## Phase 3: Namespace & Imports

- [ ] Fix ALL imports in Veritas-Core: `s/from src\./from veritas./`
- [ ] Fix relative imports within runtime: `.state`, `.hooks`, etc.
- [ ] Create public `veritas/__init__.py` with clean exports
- [ ] Run Veritas-Core tests independently

---

## Phase 4: A3 Migration

**Cross-boundary imports to fix (4 lines, 2 files):**

- [ ] `src/workflow/__init__.py:544` — `from src.runtime import RuntimeEngine` → `from veritas import RuntimeClient`
- [ ] `src/workflow/__init__.py:602` — `from src.runtime import AgentState` → `from veritas.runtime import AgentState`
- [ ] `src/api/routes/runtime.py:19` — `from src.runtime.snapshot import ...` → `from veritas.runtime import ...`
- [ ] `src/workflow/__init__.py` — `from src.memory import ...` → `from veritas.memory import ...`

---

## Phase 5: Integration Test

- [ ] `pip install -e /path/to/Veritas-Core` in A3 venv
- [ ] Run Veritas-Core tests: 100% pass
- [ ] Run A3 tests: 100% pass (application tests)
- [ ] Verify `veritas` CLI works

---

## Phase 6: Cleanup

- [ ] Remove framework duplicates from A3:
  - `rm -r src/runtime/ src/sdk/ src/security/ src/memory/ src/benchmark/ src/cli/ src/llm/`
- [ ] Update A3 `requirements.txt` to include `veritas-core`
- [ ] Update A3 `render.yaml` (if needed)
- [ ] Update A3 `setup.py` / `Makefile`

---

## Phase 7: Governance Update

- [ ] Update `docs/repository-architecture.md` — mark Veritas-Core as ACTIVE
- [ ] Update `docs/ownership-rules.yaml` — remove PLANNED status
- [ ] Update `docs/veritas-extraction-plan.md` — mark complete
- [ ] Update `docs/extraction-checklist-phase7.md` — this file

---

## Risk Mitigation

| Risk | Mitigation | Status |
|:-----|:-----------|:------:|
| Git history loss | Use git filter-branch + clone-from-A3 | ⏳ |
| A3 breaks during migration | Phased: copy then replace | ⏳ |
| Import path breakage | Automated sed + test suite | ⏳ |
| Test split incorrectly | Run both suites independently | ⏳ |
