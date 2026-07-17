# A3-Multi-Agent-System — Dockerfile
# Multi-stage build for production deployment
#
# Build:  docker build -t a3-multi-agent-system .
# Run:    docker run -p 8000:8000 -p 8501:8501 a3-multi-agent-system
#
# ── Stage 1: Builder ────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# System dependencies for python-pptx (optional slides generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libc-dev && \
    rm -rf /var/lib/apt/lists/*

# Install A3 dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Install optional extras (python-pptx for PPT generation)
RUN pip install --no-cache-dir --user python-pptx 2>/dev/null || true

# ── Stage 2: Runtime ────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 a3 && chown -R a3:a3 /app
USER a3

# Expose API + Streamlit ports
EXPOSE 8000 8501

# Health check via FastAPI endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

# Default: run both services via start script
CMD ["/app/scripts/start.sh"]
