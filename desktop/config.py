"""
A3-Agent v7.1.0 — Desktop Launcher Configuration

Platform detection, paths, ports, and timeouts for the PyInstaller
frozen environment (Windows) or development mode (Linux).

Do NOT import from src/ — this module is for the launcher layer only.
"""

from __future__ import annotations

import os
import sys

# ── Version ───────────────────────────────

APP_NAME = "A3-Agent"
APP_VERSION = "7.1.0"

# ── Ports ─────────────────────────────────

API_PORT = 8000
UI_PORT = 8501
API_URL = f"http://127.0.0.1:{API_PORT}"
UI_URL = f"http://127.0.0.1:{UI_PORT}"
HEALTH_URL = f"{API_URL}/health"

# ── Timeouts (seconds) ────────────────────

HEALTH_POLL_INTERVAL = 1.0     # How often to poll /health
HEALTH_POLL_TIMEOUT = 30.0     # Max time to wait for backend
BROWSER_OPEN_DELAY = 1.5       # Wait after Streamlit start before opening browser
SHUTDOWN_TIMEOUT = 5.0         # Max seconds to wait for graceful child exit

# ── Platform Detection ────────────────────

IS_WIN = sys.platform == "win32"

# ── User Data ─────────────────────────────

if IS_WIN:
    USER_DATA_DIR = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")),
        "A3-Agent",
    )
else:
    USER_DATA_DIR = os.path.join(
        os.path.expanduser("~"), ".a3-agent"
    )

# ── Subprocess Flags ──────────────────────

# CREATE_NO_WINDOW on Windows prevents console flash
_CREATE_NO_WINDOW = 0x08000000 if IS_WIN else 0

# ── Bundle Root ───────────────────────────

def get_bundle_root() -> str:
    """
    Return the PyInstaller bundle root directory.

    In frozen mode:  sys._MEIPASS (the _internal/ directory for --onedir).
    In dev mode:     project root (parent of this desktop/ directory).
    """
    if getattr(sys, "frozen", False):
        # --onedir: data files live in _internal/
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    # Dev mode: desktop/config.py → desktop/ → project root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BUNDLE_ROOT = get_bundle_root()
