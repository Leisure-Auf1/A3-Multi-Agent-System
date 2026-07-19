# A3-Multi-Agent-System — Dockerfile
# Multi-stage build for production deployment
#
# Build:  docker build -t a3-multi-agent-system .
# Run:    docker run -p 8000:8000 -p 8501:8501 a3-multi-agent-system
#
# ── Stage 1: Builder ────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# System dependencies:
#   gcc/libc-dev — build deps for python-pptx (optional slides generation)
#   git          — required by pip to install veritas-core from GitHub
#                  (veritas-core @ git+https://... in requirements.txt)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libc-dev git && \
    rm -rf /var/lib/apt/lists/*

# Install A3 dependencies.
# Optional build-time knobs for constrained networks (defaults = standard PyPI,
# so CI / Render / plain `docker build` behavior is unchanged):
#   PIP_INDEX_URL      — alternate package index (e.g. a domestic mirror)
#   PIP_INDEX_NO_PROXY — extra hosts exempted from any build proxy (pip layers only)
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_INDEX_NO_PROXY=""
COPY requirements.txt .
RUN PIP_INDEX_URL="${PIP_INDEX_URL}" \
    NO_PROXY="${NO_PROXY:+${NO_PROXY},}${PIP_INDEX_NO_PROXY}" \
    no_proxy="${no_proxy:+${no_proxy},}${PIP_INDEX_NO_PROXY}" \
    pip install --no-cache-dir --user -r requirements.txt

# Install optional extras (python-pptx for PPT generation)
RUN PIP_INDEX_URL="${PIP_INDEX_URL}" \
    NO_PROXY="${NO_PROXY:+${NO_PROXY},}${PIP_INDEX_NO_PROXY}" \
    no_proxy="${no_proxy:+${no_proxy},}${PIP_INDEX_NO_PROXY}" \
    pip install --no-cache-dir --user python-pptx 2>/dev/null || true

# ── Stage 2: Runtime ────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Create non-root user FIRST so the dependency copy can target its home
RUN useradd -m -u 1000 a3

# Copy installed packages from builder into a3's user site-packages.
# Builder installs with `pip install --user` as root → /root/.local,
# but runtime runs as a3 (uid 1000): /root is 0700 and root's .local is
# not on a3's sys.path. Packages must live in /home/a3/.local (a3's
# USER_SITE) with a3 ownership.
COPY --from=builder --chown=a3:a3 /root/.local /home/a3/.local
ENV PATH=/home/a3/.local/bin:$PATH

# Copy application code
COPY . .

RUN chown -R a3:a3 /app
USER a3

# Expose API + Streamlit ports
EXPOSE 8000 8501

# Health check via FastAPI endpoint.
# python:3.12-slim has NO curl — use stdlib urllib (zero extra deps).
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; r=urllib.request.urlopen('http://localhost:8000/health', timeout=4); sys.exit(0 if r.status==200 else 1)" || exit 1

# Default: run both services via start script
CMD ["/app/scripts/start.sh"]
