"""A3 AI Learning Assistant — Streamlit Launcher

Delegates to web/app_v4.py (PR #3 product UI).
For legacy demo, run: streamlit run web/app_v3.py
"""
import sys
from pathlib import Path

# Ensure project root on path
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from web.app_v4 import main

if __name__ == "__main__":
    main()
