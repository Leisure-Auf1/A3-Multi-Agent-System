"""
# A3-Agent v1.0.0 — Desktop Launcher Configuration

Platform detection, paths, ports, and timeouts for the PyInstaller
frozen environment (Windows) or development mode (Linux).

Do NOT import from src/ — this module is for the launcher layer only.
"""

from __future__ import annotations

import os
import sys

# ── Version ───────────────────────────────

APP_NAME = "A3-Agent"
APP_VERSION = "1.0.0"

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


# ── Bundle Integrity ───────────────────────

# Files that must exist for the bundle to be considered intact.
# Order: most critical first. Format: (relative_to_BUNDLE_ROOT, description).
_BUNDLE_CRITICAL_PATHS = [
    ("streamlit/static/index.html", "Streamlit static assets"),
]


def verify_bundle_integrity() -> tuple[bool, list[str]]:
    """Check that the bundle root and critical files exist.

    Returns:
        (ok: bool, missing: list[str]) — ok=True means all checks passed.
        missing entries are human-readable descriptions of what's missing.

    In frozen mode (PyInstaller onedir): checks BUNDLE_ROOT, sys.executable,
    and critical bundle files (streamlit static assets, etc.).
    In dev mode: only checks BUNDLE_ROOT and sys.executable exist.
    """
    is_frozen = getattr(sys, "frozen", False)
    missing: list[str] = []

    # 1. BUNDLE_ROOT itself must exist
    if not os.path.isdir(BUNDLE_ROOT):
        missing.append(f"Bundle root directory: {BUNDLE_ROOT}")
        return False, missing

    # 2. sys.executable must exist (PyInstaller archive checker depends on it)
    exe = sys.executable
    if not os.path.isfile(exe):
        missing.append(f"Executable: {exe}")

    # 3. Critical paths — only checked in frozen mode.
    #    In dev mode, streamlit static files come from the installed package,
    #    not from BUNDLE_ROOT.
    if is_frozen:
        for rel_path, desc in _BUNDLE_CRITICAL_PATHS:
            abs_path = os.path.join(BUNDLE_ROOT, rel_path)
            if not os.path.isfile(abs_path):
                missing.append(f"{desc}: {abs_path}")

    return len(missing) == 0, missing

