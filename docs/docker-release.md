# Docker Release Guide

> Publish A3-Multi-Agent-System to Docker Hub and GHCR.

---

## Version Tag Strategy

```
Tag        →  Image
────────────────────────────────────
v1.0.0     →  leisureauf1/a3-multi-agent-system:1.0.0
v1.0.0     →  leisureauf1/a3-multi-agent-system:1.0
v1.0.0     →  leisureauf1/a3-multi-agent-system:1
v1.0.0     →  leisureauf1/a3-multi-agent-system:latest
v1.0.0     →  ghcr.io/leisure-auf1/a3-multi-agent-system:1.0.0
```

**SemVer:** `MAJOR.MINOR.PATCH`
- **MAJOR**: Breaking API changes (e.g., Veritas-Core API change)
- **MINOR**: New features (new agent, new resource type)
- **PATCH**: Bug fixes, docs, non-breaking improvements

---

## Creating a Release

### 1. Update version in setup.py

```python
# setup.py
setup(
    name="a3-multi-agent-system",
    version="1.0.0",  # ← Update this
    ...
)
```

### 2. Tag and push

```bash
# Ensure all tests pass
make test

# Create tag
git tag -a v1.0.0 -m "Release v1.0.0 — Initial Docker release"

# Push tag (triggers CI)
git push origin v1.0.0
```

### 3. CI auto-publishes

GitHub Actions will:
1. Run test suite (1130+ tests gate)
2. Build multi-arch image (amd64 + arm64)
3. Push to Docker Hub + GHCR
4. Tag with version, major.minor, major, latest, and short SHA

### 4. Verify

```bash
# Pull from Docker Hub
docker pull leisureauf1/a3-multi-agent-system:latest

# Run
docker run -p 8000:8000 -p 8501:8501 leisureauf1/a3-multi-agent-system:latest

# Check health
curl http://localhost:8000/health
```

---

## Docker Hub Setup

### Repository
- **Name:** `leisureauf1/a3-multi-agent-system`
- **Visibility:** Public
- **Description:** "A3 Multi-Agent Personalized Learning System — AI-powered education platform"

### Secrets (GitHub → Settings → Secrets)

| Secret | Value |
|:-------|:------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token (not password) |

**Create access token:** Docker Hub → Account Settings → Security → New Access Token

---

## Image Details

### Multi-Architecture
- `linux/amd64` — Intel/AMD (most servers, desktops)
- `linux/arm64` — Apple Silicon, ARM servers (Raspberry Pi)

### Layers
```
python:3.12-slim (base)
  → pip install veritas-core (framework)
  → pip install -r requirements.txt (A3 deps)
  → COPY . (application code)
  → non-root user
```

### Size
- Base: ~150 MB (python:3.12-slim)
- Estimated final: ~300 MB

---

## Release History

| Version | Date | Highlights |
|:--------|:-----|:-----------|
| v1.0.0 | 2026-07 | Initial release. 9 agents, 7 resource types, Docker, CI/CD |

---

## Next Steps

- [Desktop Application](../docs/phase10.3-desktop.md)
- [API Reference](http://localhost:8000/docs)
- [Docker Quickstart](docker-quickstart.md)
