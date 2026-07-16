"""
A3 Multi-Agent Learning System — HuggingFace Spaces Entry
==========================================================

Launcher for HuggingFace Spaces. Sets up path, then delegates
all rendering to web/app_v3.py's main().

HF Spaces will auto-detect this as a Streamlit app.
"""

import sys
import os

# Ensure project root is on path for src/ imports
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from web.app_v3 import main

if __name__ == "__main__":
    main()
