# Veritas-Core Extraction Plan

> **Status:** PLANNING | **Target:** Phase 6.3 | **Tests:** 1000 (pre-extraction)
>
> This document is the phased migration blueprint for extracting
> the Veritas Runtime Framework from A3-Multi-Agent-System into
> a standalone `veritas-core` Python package.

---

## Phase 0: Current State (COMPLETED ✅)

**What we have:**

```
A3-Multi-Agent-System/
├── src/runtime/         (37 files)  ← Runtime engine, hooks, events
├── src/sdk/             (8 files)   ← Public API (RuntimeClient)
├── src/security/        (5 files)   ← Permission, audit, prompt guard
├── src/memory/          (5 files)   ← Student memory, experience
├── src/benchmark/       (5 files)   ← Failure injection, metrics
├── src/runtime/recovery/    (4)     ← Retry, rollback, fallback
├── src/runtime/lifecycle/   (3)     ← Agent lifecycle, session
├── src/runtime/explain/     (3)     ← Decision trace, reasons
├── src/runtime/plugins/     (6)     ← Pluggable extensions
├── src/runtime/distributed/ (6)     ← Nodes, registry, events
├── src/agents/          (9 modules) ← A3 application agents
├── src/workflow/        (2 files)   ← A3Workflow
├── src/api/             (6 files)   ← FastAPI server
└── tests/               (1000 tests) ← Combined runtime + app tests
```

**Key metrics:**

| Metric | Value |
|:-------|:------|
| Runtime files | 37 + 8 SDK + 5 security + 5 memory + 5 benchmark = 60 files |
| Application files | 9 agents + 2 workflow = 11 files |
| Undecided/Shared | ~10 files (core/, llm/, rag/, evaluation/, web/) |
| Tests | 1000 (combined) |
| Internal imports | `from src.runtime import ...` pattern throughout |
| Public API | SDK layer exists (Phase 6.0) |

---

## Phase 1: Boundary Preparation

**Goal:** Define clear ownership before any file moves.

**Status:** ⏳ IN PROGRESS

### Actions

#### 1.1 Tag all tests by layer

```bash
# Tag framework tests (move to Veritas-Core)
grep -l "from src.runtime\|from src.sdk\|from src.security\|from src.memory\|from src.benchmark" tests/*.py
# These go to Veritas-Core

# Tag application tests (stay in A3)
grep -l "from src.agents\|from src.workflow" tests/*.py
# These stay in A3
```

#### 1.2 Generate import map

```bash
# Find all cross-layer imports
grep -rn "from src\." src/ --include="*.py" | \
  grep -v "__pycache__" | \
  sort > docs/import-map.txt
```

#### 1.3 Resolve shared components

| Component | Decision needed | Proposed owner |
|:----------|:----------------|:---------------|
| `src/core/` (EventBus, MetaReflector) | Runtime or app? | **Veritas-Core** (core infrastructure) |
| `src/llm/` (Provider abstraction) | Shared dependency | **Veritas-Core** (framework provides LLM layer) |
| `src/rag/` (TF-IDF retriever) | App-specific? | **A3** (application feature) |
| `web/dashboard.py` | UI or framework tool? | **A3** (Streamlit is app UI) |
| `src/evaluation/` | Framework or app? | **Veritas-Core** (evaluation is runtime concern) |

#### 1.4 Freeze SDK API

```
☑ Phase 6.0 RuntimeClient is stable
☐ Document all public methods in SDK
☐ Add deprecation warnings for any soon-to-change internals
☐ Tag SDK version as 1.0.0-alpha in preparation
```

#### 1.5 Add package metadata to Veritas-Core repo

```bash
cd Veritas-Core
# Create package structure
mkdir -p src/veritas
touch src/veritas/__init__.py

# Add setup files
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "veritas-core"
version = "0.1.0"
description = "Agent Runtime Framework"
requires-python = ">=3.10"
EOF
```

**Deliverables:**
- [ ] Test layer tags complete
- [ ] Import map generated
- [ ] Shared component ownership decided
- [ ] SDK API documented and frozen
- [ ] Veritas-Core repo has package scaffolding

---

## Phase 2: Repository Extraction

**Goal:** Move runtime code to Veritas-Core with history preserved.

**Status:** 📋 PLANNED

### Actions

#### 2.1 Extract using git-filter-branch (preserves history)

```bash
cd A3-Multi-Agent-System

# Create a branch with only runtime files
git checkout -b extract-veritas

# Filter to keep only runtime-related paths
git filter-branch --prune-empty --subdirectory-filter \
  --index-filter ' \
    git rm --cached -r --ignore-unmatch \
      src/agents src/api src/evaluation src/rag src/web \
      storage datasets notebooks outputs \
  ' \
  HEAD
```

**Alternative (safer):** Use `git subtree split`

```bash
cd A3-Multi-Agent-System
git subtree split --prefix=src/runtime -b veritas-runtime-only
git subtree split --prefix=src/sdk -b veritas-sdk-only
# ... repeat for each top-level directory
```

#### 2.2 Merge into Veritas-Core

```bash
cd Veritas-Core
git remote add a3 ../A3-Multi-Agent-System
git fetch a3

# Merge runtime subtree
git merge --allow-unrelated-histories a3/veritas-runtime-only

# Repeat for sdk, security, memory, benchmark
```

#### 2.3 Update import paths (automated)

```bash
# In Veritas-Core: fix internal imports
find src/ -name '*.py' -exec sed -i \
  's/from \.\.runtime/from veritas.runtime/g; \
   s/from \.\.hooks/from veritas.runtime.hooks/g; \
   s/from \.\.state/from veritas.runtime.state/g' \
  {} +
```

#### 2.4 Verify both repos independently

```bash
cd Veritas-Core && python -m pytest tests/ -v
# Expect: all runtime tests pass

cd A3-Multi-Agent-System && python -m pytest tests/ -v
# Expect: application tests pass
# Runtime tests may fail until dependency is installed
```

**Deliverables:**
- [ ] Veritas-Core has all runtime code with git history
- [ ] Import paths updated
- [ ] Tests pass in Veritas-Core independently
- [ ] A3 can still run (with veritas-core installed)
- [ ] No duplicate code between repos

---

## Phase 3: Framework Packaging

**Goal:** Veritas-Core is installable via `pip install veritas-core`.

**Status:** 📋 PLANNED

### Actions

#### 3.1 Package structure

```
veritas-core/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── src/
│   └── veritas/
│       ├── __init__.py          # Public API exports
│       ├── runtime/
│       │   ├── __init__.py
│       │   ├── engine.py        # RuntimeEngine + RuntimeContext
│       │   ├── state.py
│       │   ├── hooks.py
│       │   ├── events.py
│       │   ├── recovery/
│       │   ├── lifecycle/
│       │   ├── explain/
│       │   ├── plugins/
│       │   └── distributed/
│       ├── sdk/
│       │   ├── __init__.py
│       │   ├── client.py        # RuntimeClient
│       │   ├── contracts/
│       │   └── config/
│       ├── security/
│       ├── memory/
│       └── benchmark/
└── tests/
```

#### 3.2 pyproject.toml

```toml
[project]
name = "veritas-core"
version = "1.0.0"
description = "Agent Runtime Framework — pluggable, observable, recoverable"
requires-python = ">=3.10"
dependencies = [
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov"]
all = ["fastapi", "streamlit"]

[project.urls]
Repository = "https://github.com/Leisure-Auf1/Veritas-Core"
```

#### 3.3 Release process

```bash
# Tag and release
git tag v1.0.0
git push origin v1.0.0
gh release create v1.0.0 --title "Veritas-Core v1.0.0"

# Publish to PyPI (optional)
python -m build
twine upload dist/*
```

**Deliverables:**
- [ ] `pip install veritas-core` works
- [ ] `from veritas import RuntimeClient` works
- [ ] Package published to GitHub Releases
- [ ] CHANGELOG maintained
- [ ] Version tagged with semver

---

## Phase 4: A3 Migration

**Goal:** A3 depends on Veritas-Core as an external package.

**Status:** 📋 PLANNED

### Actions

#### 4.1 Update requirements.txt

```
# A3-Multi-Agent-System/requirements.txt
veritas-core>=1.0.0,<2.0.0
```

#### 4.2 Update A3 imports

```python
# Before (Phase 0–6):
from src.runtime import RuntimeEngine, RuntimeContext
from src.sdk import RuntimeClient

# After (Phase 6.3+):
from veritas import RuntimeClient               # Public API
from veritas.runtime import RuntimeEngine        # Advanced use only
```

#### 4.3 Remove migrated code from A3

```bash
cd A3-Multi-Agent-System
git rm -r src/runtime/ src/sdk/ src/security/ src/memory/ src/benchmark/
git commit -m "refactor: migrate runtime to veritas-core dependency"
```

#### 4.4 Verify

```bash
cd A3-Multi-Agent-System
pip install -r requirements.txt
python -m pytest tests/ -v
# Expect: all application tests pass
# Runtime tests now live in Veritas-Core
```

**Deliverables:**
- [ ] A3 requirements.txt updated
- [ ] All A3 imports use `veritas.*`
- [ ] Runtime code removed from A3
- [ ] Application tests pass

---

## Phase 5: Ecosystem

**Goal:** Veritas-Core serves multiple applications.

**Status:** 🔮 FUTURE

### Planned Adapters

```
┌──────────────────┐
│   Veritas-Core    │
│   (Framework)     │
└────────┬─────────┘
         │
    ┌────┼────┬──────────┐
    │    │    │          │
    ▼    ▼    ▼          ▼
┌────┐ ┌───┐ ┌────────┐ ┌──────────┐
│ A3 │ │CA │ │Research│ │Coding    │
│    │ │   │ │Agent   │ │Agent     │
└────┘ └───┘ └────────┘ └──────────┘
```

| Adapter | Status | Description |
|:--------|:-------|:------------|
| A3 System | ✅ Active | Learning application |
| LangGraph adapter | 🔮 Planned | Interop with LangGraph Runtime |
| AutoGen adapter | 🔮 Planned | Interop with AutoGen agents |
| Coding Agent | 🔮 Planned | Autonomous coding via Veritas runtime |
| Research Agent | 🔮 Planned | Literature review agent |

### LangGraph Adapter design (sketch):

```python
from veritas import RuntimeClient
from langgraph.graph import StateGraph

class VeritasLangGraphAdapter:
    """Run Veritas runtime tasks as LangGraph nodes."""

    def __init__(self):
        self.client = RuntimeClient()

    def to_langgraph_node(self, task_request):
        def node(state):
            result = self.client.run(task_request)
            return {"output": result.output}
        return node
```

---

## Risk Matrix

| Phase | Risk | Likelihood | Impact | Mitigation |
|:------|:-----|:-----------|:-------|:-----------|
| 1 | Shared component ownership disputes | LOW | MEDIUM | Decide before Phase 2 |
| 2 | Git history loss | MEDIUM | HIGH | Use `git subtree split`, verify before merge |
| 2 | Import path breakage | HIGH | HIGH | Automated sed + test suite |
| 2 | Test suite split incorrectly | MEDIUM | HIGH | Tag tests by layer first |
| 3 | Package metadata errors | LOW | LOW | Test `pip install` locally |
| 4 | A3 imports point to removed code | HIGH | HIGH | CI gate — imports must resolve |
| 4 | Runtime regression after dependency bump | MEDIUM | HIGH | Pin exact version, test before bump |
| 5 | Adapter maintenance burden | LOW | LOW | Adapters are thin wrappers |

---

## Timeline (tentative)

```
Phase 0: COMPLETED ✅ (July 2026)
Phase 1: Q3 2026 (2–4 weeks)
  • Tag tests, generate import map, decide ownership
Phase 2: Q3 2026 (1–2 weeks)
  • git subtree split, merge, verify
Phase 3: Q3 2026 (1 week)
  • Package, release v1.0.0
Phase 4: Q3 2026 (1 week)
  • A3 migration, verify
Phase 5: Q4 2026+ (ongoing)
  • Adapters, ecosystem growth
```

---

## Success Criteria

- [x] Phase 0: 1000 tests, SDK stable
- [ ] Phase 1: All ownership decisions documented
- [ ] Phase 2: Both repos pass CI independently
- [ ] Phase 3: `pip install veritas-core` succeeds
- [ ] Phase 4: A3 works with veritas-core as dependency
- [ ] Phase 5: At least one external application uses Veritas
