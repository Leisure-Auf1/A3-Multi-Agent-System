"""
A3 Multi-Agent Learning System — Deployment Entry
==================================================

Launcher for HuggingFace Spaces / Render / local. Sets up path,
then delegates to web/app.py (Phase 10.1 unified product UI).

HF Spaces auto-detects this as a Streamlit app.
Render start command (see render.yaml):
    streamlit run app.py --server.port $PORT --server.address 0.0.0.0
"""

import sys
import os

# Ensure project root is on path for src/ imports
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Phase 10.1 — use unified product entry
from web.app import main

if __name__ == "__main__":
    main()
