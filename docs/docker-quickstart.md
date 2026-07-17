# A3 Docker Quickstart

> Deploy A3-Multi-Agent-System in 5 minutes with Docker.

---

## Prerequisites

- Docker 24+ and Docker Compose v2+
- 2 GB free disk space
- Python not required on host (all in container)

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/Leisure-Auf1/A3-Multi-Agent-System.git
cd A3-Multi-Agent-System

# 2. Build and start
docker compose up -d

# 3. Wait for services (first build takes ~2 min)
docker compose logs -f api
# Look for: "API is ready"

# 4. Access
# Streamlit Dashboard: http://localhost:8501
# FastAPI Docs:       http://localhost:8000/docs
# Health Check:       http://localhost:8000/health
```

---

## Services

| Service | Port | Description |
|:--------|:----:|:------------|
| `api` | 8000 | FastAPI backend — all business logic |
| `dashboard` | 8501 | Streamlit frontend — student UI |

---

## Common Commands

```bash
# View logs
docker compose logs -f api          # API logs
docker compose logs -f dashboard    # Dashboard logs

# Restart services
docker compose restart api

# Stop everything
docker compose down

# Rebuild after code changes
docker compose up -d --build

# Run tests inside container
docker compose exec api python -m pytest tests/ -v

# Access container shell
docker compose exec api bash
docker compose exec dashboard bash
```

---

## Configuration

Create a `.env` file in the project root:

```bash
# Provider: "mock" (zero API keys) or "deepseek" (needs key)
LLM_PROVIDER=mock

# Optional: API keys for enhanced generation
# DEEPSEEK_API_KEY=sk-...
# FAL_KEY=...

# Database (default: SQLite)
DATABASE_URL=sqlite:///storage/a3.db

# Tier: "free" | "pro"
DEFAULT_USER_TIER=free
```

**Zero API keys needed!** A3 runs fully offline with rule-based generators and SVG placeholders.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              Docker Host                     │
│                                             │
│  ┌──────────────┐    ┌──────────────┐       │
│  │  dashboard   │    │     api      │       │
│  │  (Streamlit) │───▶│  (FastAPI)   │       │
│  │  :8501       │    │  :8000       │       │
│  └──────────────┘    └──────┬───────┘       │
│                             │               │
│                             ▼               │
│                    ┌────────────────┐       │
│                    │   SQLite       │       │
│                    │   (volume)     │       │
│                    └────────────────┘       │
│                                             │
│  Volumes:                                   │
│    a3_data  → /app/storage (persistent)     │
│    a3_kb    → /app/knowledge_base (ro)      │
└─────────────────────────────────────────────┘
```

---

## Troubleshooting

### Container won't start
```bash
# Check logs
docker compose logs api

# Common issues:
# - Port conflict: lsof -i :8000
# - Missing volume: docker compose down -v && docker compose up -d
```

### Build fails
```bash
# Clear cache and rebuild
docker compose build --no-cache
docker compose up -d
```

### API not responding
```bash
# Check health
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# Restart API only
docker compose restart api
```

### Dashboard can't reach API
```bash
# Verify API_URL in dashboard
docker compose exec dashboard env | grep A3_API_URL
# Expected: A3_API_URL=http://api:8000
```

---

## Production Notes

### Resource Limits
```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
```

### PostgreSQL (Optional)
For multi-user production, switch to PostgreSQL:
```bash
# Start with PostgreSQL profile
docker compose --profile production up -d

# Update DATABASE_URL in .env:
# DATABASE_URL=postgresql://a3:a3_secret@postgres:5432/a3
```

### Backup
```bash
# Backup SQLite database
docker compose exec api cp /app/storage/a3.db /app/storage/a3.db.bak

# Restore
docker compose exec api cp /app/storage/a3.db.bak /app/storage/a3.db
```

---

## Next Steps

- [Render Deployment](../docs/phase10.1-deployment-design.md)
- [API Documentation](http://localhost:8000/docs)
- [Demo Scripts](../examples/)
