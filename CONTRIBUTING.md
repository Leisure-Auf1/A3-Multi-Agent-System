# Contributing to A3-Agent

Thanks for your interest in contributing! A3-Agent is an open-source multi-agent learning assistant built with Python.

## How Can I Contribute?

### Bug Reports
File issues using the [Bug Report](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/issues/new?template=bug_report.md) template.

### Feature Requests
Suggest enhancements using the [Feature Request](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/issues/new?template=feature_request.md) template.

### Pull Requests

1. **Fork** the repository
2. **Clone** your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/A3-Multi-Agent-System.git
   cd A3-Multi-Agent-System
   ```
3. **Create a branch**:
   ```bash
   git checkout -b feat/your-feature-name
   ```
4. **Make changes** — follow the code style and architecture constraints
5. **Test** — ensure all tests pass:
   ```bash
   make test
   ```
6. **Commit** with a descriptive message:
   ```bash
   git commit -m "feat: add your feature description"
   ```
7. **Push** and open a Pull Request against `main`

## Development Setup

```bash
# Clone
git clone https://github.com/Leisure-Auf1/A3-Multi-Agent-System.git
cd A3-Multi-Agent-System

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install pyinstaller  # for desktop builds

# Run tests
make test
```

## Architecture Constraints

> ⚠️ **CRITICAL**: These directories are **frozen** — do NOT modify:

| Directory | Reason |
|:----------|:-------|
| `src/agents/` | 12-agent pipeline — stable, tested |
| `src/workflow/` | A3Workflow orchestrator — stable |
| Veritas-Core | External framework dependency |

**Allowed areas for contribution**:
- `docs/` — documentation
- `web/` — Streamlit UI
- `desktop/` — packaging
- `scripts/` — build tooling
- `tests/` — test coverage
- `README.md`, `CHANGELOG.md`

## Code Style

- **Python**: PEP 8, 4-space indentation, 120-char max line length
- **Type Hints**: `from __future__ import annotations` + type annotations for public APIs
- **Docstrings**: Google-style for functions, concise for modules
- **Imports**: Standard library → third-party → project (alphabetical within groups)

## Testing

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_profile_agent.py -v

# Run with coverage
pytest --cov=src tests/
```

Target: **1154/1154 tests passing, 0 failures.**

## Commit Convention

```
<type>: <description>

feat: add new agent capability
fix: resolve database migration issue
docs: update installation guide
release: package v1.0.0 Windows .exe
```

## Questions?

Open a [GitHub Discussion](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/discussions) or file an issue.

---

Thanks for contributing! 🎉
