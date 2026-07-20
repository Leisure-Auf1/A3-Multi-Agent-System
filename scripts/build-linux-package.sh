#!/bin/bash
# =============================================================================
# Phase 7.0 — A3-Agent Linux Distribution Package Builder
# =============================================================================
# Creates a self-contained A3-Agent-linux-x64.tar.gz with launcher + deps.
#
# Usage:
#   bash scripts/build-linux-package.sh
#
# Output:
#   dist/A3-Agent-linux-x64-v1.0.0.tar.gz
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION="${A3_VERSION:-1.0.0}"
PACKAGE_NAME="A3-Agent-linux-x64-v${VERSION}"
BUILD_DIR="$PROJECT_ROOT/dist/$PACKAGE_NAME"

echo "============================================"
echo "  A3-Agent Linux Package Builder"
echo "  Version: v${VERSION}"
echo "============================================"
echo ""

# ── Clean previous build ──────────────────
rm -rf "$PROJECT_ROOT/dist/$PACKAGE_NAME" "$PROJECT_ROOT/dist/$PACKAGE_NAME.tar.gz"
mkdir -p "$BUILD_DIR"

# ── Copy application source ───────────────
echo "[1/5] Cleaning __pycache__ and stale artifacts..."
find "$PROJECT_ROOT/src" -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_ROOT/web" -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

echo "[2/5] Copying application source..."
cp -r "$PROJECT_ROOT"/* "$BUILD_DIR/" 2>/dev/null || true
# Remove unwanted directories
rm -rf "$BUILD_DIR/.venv" "$BUILD_DIR/.git" "$BUILD_DIR/dist" "$BUILD_DIR/build" "$BUILD_DIR/release" "$BUILD_DIR/.pytest_cache" 2>/dev/null || true
# Remove __pycache__ and .pyc files
find "$BUILD_DIR" -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -name "*.pyc" -delete 2>/dev/null || true
# Remove database files from storage
find "$BUILD_DIR" -name "*.db" -path "*/storage/*" -delete 2>/dev/null || true

# ── Copy start script ─────────────────────
echo "[3/5] Creating launcher..."
cat > "$BUILD_DIR/start.sh" << 'LAUNCHER'
#!/bin/bash
# A3-Agent v1.0.0 — Linux Launcher
# Starts FastAPI backend + Streamlit frontend.

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Create virtual environment on first run
if [ ! -d ".venv" ]; then
    echo "🔧 Setting up Python environment (first run)..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    echo "✅ Environment ready."
else
    source .venv/bin/activate
fi

# Ensure storage directory
mkdir -p storage

echo "============================================"
echo "  A3-Agent v1.0.0"
echo "  http://localhost:8501"
echo "============================================"

# Start FastAPI
echo "[1/2] Starting API server (port 8000)..."
uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --workers 1 --log-level warning &
API_PID=$!

# Wait for health
for i in $(seq 1 20); do
    if python -c "import urllib.request; r=urllib.request.urlopen('http://localhost:8000/health',timeout=2); exit(0 if r.status==200 else 1)" 2>/dev/null; then
        break
    fi
    sleep 1
done

# Start Streamlit
echo "[2/2] Starting Streamlit (port 8501)..."
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false

# Cleanup
kill $API_PID 2>/dev/null || true
LAUNCHER
chmod +x "$BUILD_DIR/start.sh"

# ── Create dist README ────────────────────
echo "[4/5] Creating package README..."
cat > "$BUILD_DIR/INSTALL.md" << 'README'
# A3-Agent v1.0.0 — Linux Installation

## Requirements
- Python 3.10+
- Internet connection (first run only, for dependency install)

## Quick Start

```bash
# 1. Extract
tar xzf A3-Agent-linux-x64-v1.0.0.tar.gz
cd A3-Agent-linux-x64-v1.0.0

# 2. Launch (auto-installs deps on first run)
./start.sh

# 3. Open http://localhost:8501
```

## First Run
On first launch, you'll see the Welcome page:
1. Select your AI provider (DeepSeek / OpenAI / Spark)
2. Enter your API key
3. Click "Test Connection" to verify
4. Click "Save & Start" to begin

Or choose "Demo Mode" to try without an API key.

## Troubleshooting

| Problem | Solution |
|:--------|:---------|
| Port 8000/8501 in use | `kill $(lsof -t -i:8000)` or change ports |
| "keyring" errors | Run in a desktop session (needs Secret Service) |
| API key not saving | Check `~/.a3-agent/config/llm.json` permissions |

## Files
- `start.sh` — Launcher script
- `src/` — Application source
- `web/` — Streamlit UI
- `knowledge_base/` — Course content
- `requirements.txt` — Python dependencies
README
chmod +x "$BUILD_DIR/INSTALL.md"

# ── Add root-level documentation ────────
echo "[4.5/6] Adding root documentation..."
cp "$PROJECT_ROOT/LICENSE" "$BUILD_DIR/LICENSE" 2>/dev/null || echo "(LICENSE not found)"
echo "A3-Agent v${VERSION}" > "$BUILD_DIR/VERSION"
cat > "$BUILD_DIR/README.txt" << README_TXT
A3-Agent v${VERSION} — AI Multi-Agent Learning System

Quick Start:
  1. Extract: tar xzf A3-Agent-linux-x64-v${VERSION}.tar.gz
  2. Launch: ./start.sh
  3. Open:   http://localhost:8501

Demo Mode: No API key needed.
Full pipeline with 7 agents, quizzes, reflection, and history replay.

Docs: https://github.com/Leisure-Auf1/A3-Multi-Agent-System
README_TXT

# ── Package ───────────────────────────────
echo "[5/6] Creating tarball..."
cd "$PROJECT_ROOT/dist"
tar czf "$PACKAGE_NAME.tar.gz" "$PACKAGE_NAME"

# ── Summary ───────────────────────────────
echo "[6/6] Done!"
echo ""
echo "Package: dist/$PACKAGE_NAME.tar.gz"
echo "Size:    $(du -h "$PACKAGE_NAME.tar.gz" | cut -f1)"
echo "Files:   $(tar tzf "$PACKAGE_NAME.tar.gz" | wc -l)"
echo ""
echo "To test:"
echo "  cd dist && tar xzf $PACKAGE_NAME.tar.gz"
echo "  cd $PACKAGE_NAME && ./start.sh"
