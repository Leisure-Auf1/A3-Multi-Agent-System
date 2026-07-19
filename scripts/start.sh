#!/bin/bash
# scripts/start.sh — Launch both FastAPI + Streamlit
# Used as Docker CMD entry point.

set -e

echo "============================================"
echo "  A3 Multi-Agent System — Starting"
echo "============================================"
echo ""

# Ensure storage directory exists
mkdir -p /app/storage

# Start FastAPI in background
echo "[1/2] Starting FastAPI on port 8000..."
uvicorn src.api.server:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info &
API_PID=$!

# Wait for API to be ready (stdlib check — image has no curl)
echo "      Waiting for API health check..."
for i in $(seq 1 30); do
    if python -c "import urllib.request,sys; r=urllib.request.urlopen('http://localhost:8000/health', timeout=2); sys.exit(0 if r.status==200 else 1)" > /dev/null 2>&1; then
        echo "      API is ready."
        break
    fi
    sleep 1
done

# Start Streamlit in foreground (keeps container alive)
echo "[2/2] Starting Streamlit on port 8501..."
exec streamlit run app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false
