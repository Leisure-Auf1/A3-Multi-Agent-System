"""
A3-Agent v7.1.0 — Desktop Launcher (PyInstaller Entry Point)
===============================================================

Child-mode dispatch launcher for FastAPI + Streamlit in PyInstaller
frozen environment.

Architecture:
  - Normal launch: start FastAPI → health check → start Streamlit → browser
  - Child mode:    --child uvicorn   → run FastAPI in-process
                   --child streamlit → run Streamlit in-process

Usage:
  # Normal (double-click or terminal):
  A3-Agent.exe

  # Child mode (spawned by parent):
  A3-Agent.exe --child uvicorn --host 127.0.0.1 --port 8000
  A3-Agent.exe --child streamlit --server.port 8501

PyInstaller entry:
  pyinstaller --onedir ... desktop/launcher.py
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error
import webbrowser

# ── multiprocessing.freeze_support MUST be called first on Windows ──
import multiprocessing
multiprocessing.freeze_support()

# ── Local config ──────────────────────────
from desktop.config import (
    APP_NAME, APP_VERSION,
    API_PORT, UI_PORT, API_URL, UI_URL, HEALTH_URL,
    HEALTH_POLL_INTERVAL, HEALTH_POLL_TIMEOUT,
    BROWSER_OPEN_DELAY, SHUTDOWN_TIMEOUT,
    IS_WIN, USER_DATA_DIR, BUNDLE_ROOT,
    _CREATE_NO_WINDOW,
    verify_bundle_integrity,
)

# ── Logging ───────────────────────────────

LOG_DIR = os.path.join(USER_DATA_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "launcher.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Child-mode dispatch
# ═══════════════════════════════════════════════════════════════

def parse_child_args() -> tuple[str, list[str]] | None:
    """If --child is present, return (mode, remaining_args). Otherwise None."""
    if "--child" not in sys.argv:
        return None
    idx = sys.argv.index("--child")
    mode = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
    remaining = [a for i, a in enumerate(sys.argv) if i != idx and i != idx + 1]
    return mode, remaining


def run_uvicorn_child() -> None:
    """Run FastAPI as child process (in-process)."""
    import uvicorn
    host = "127.0.0.1"
    port = API_PORT
    # Parse --host and --port from remaining args
    for i, arg in enumerate(sys.argv):
        if arg == "--host" and i + 1 < len(sys.argv):
            host = sys.argv[i + 1]
        if arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
    log.info("FastAPI child starting on %s:%d", host, port)
    uvicorn.run("src.api.server:app", host=host, port=port, log_level="warning")


def run_streamlit_child() -> None:
    """Run Streamlit as child process (in-process)."""
    import streamlit.web.cli as stcli

    # Build args for streamlit
    args = [
        "streamlit", "run", os.path.join(BUNDLE_ROOT, "app.py"),
        "--server.port", str(UI_PORT),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--global.developmentMode", "false",
        "--logger.level", "error",
    ]
    log.info("Streamlit child starting on port %d", UI_PORT)
    sys.argv = args
    stcli.main()


# ═══════════════════════════════════════════════════════════════
# Parent launcher (normal mode)
# ═══════════════════════════════════════════════════════════════

def seed_user_data() -> None:
    """Copy seed DB to USER_DATA_DIR on first run (if not exists)."""
    seed_db = os.path.join(BUNDLE_ROOT, "storage", "a3.db")
    user_db_dir = os.path.join(USER_DATA_DIR, "storage")
    user_db = os.path.join(user_db_dir, "a3.db")

    if not os.path.exists(seed_db):
        log.warning("Seed DB not found: %s — skipping", seed_db)
        return

    if os.path.exists(user_db):
        log.info("User DB already exists: %s", user_db)
        return

    os.makedirs(user_db_dir, exist_ok=True)
    with open(seed_db, "rb") as src, open(user_db, "wb") as dst:
        dst.write(src.read())
    log.info("Seeded user DB: %s (%d bytes)", user_db, os.path.getsize(user_db))


def start_service(args: list[str], name: str) -> subprocess.Popen | None:
    """Start a child service process."""
    log_path = os.path.join(LOG_DIR, "subprocess.log")
    try:
        # Verify cwd exists before spawning — prevents pathlib/os.getcwd()
        # crashes inside child when bundle has been moved/deleted at runtime.
        if not os.path.isdir(BUNDLE_ROOT):
            log.error("Bundle root does not exist — cannot start %s: %s", name, BUNDLE_ROOT)
            return None
        with open(log_path, "a") as log_fp:
            log_fp.write(f"\n--- {name} started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            proc = subprocess.Popen(
                [sys.executable, "--child"] + args,
                cwd=BUNDLE_ROOT,
                creationflags=_CREATE_NO_WINDOW,
                stdout=log_fp,
                stderr=subprocess.STDOUT,
            )
        log.info("Started %s (PID %d)", name, proc.pid)
        return proc
    except Exception as e:
        log.error("Failed to start %s: %s", name, e)
        return None


def wait_for_health(url: str, timeout: float = HEALTH_POLL_TIMEOUT) -> bool:
    """Poll health endpoint until 200 or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(HEALTH_POLL_INTERVAL)
    return False


def shutdown(processes: dict[str, subprocess.Popen | None]) -> None:
    """Graceful shutdown: terminate children, wait, kill if needed."""
    log.info("Shutting down...")
    for name, proc in processes.items():
        if proc is None or proc.poll() is not None:
            continue
        log.info("Stopping %s (PID %d)...", name, proc.pid)
        try:
            proc.terminate()
        except OSError:
            pass
    # Wait for graceful exit
    deadline = time.time() + SHUTDOWN_TIMEOUT
    for name, proc in processes.items():
        if proc is None:
            continue
        try:
            proc.wait(timeout=max(0, deadline - time.time()))
        except subprocess.TimeoutExpired:
            log.warning("%s did not exit gracefully — force killing", name)
            try:
                proc.kill()
            except OSError:
                pass


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    # ── Child mode dispatch ────────────────
    child = parse_child_args()
    if child:
        mode, _ = child
        if mode == "uvicorn":
            return run_uvicorn_child()
        elif mode == "streamlit":
            return run_streamlit_child()
        else:
            log.error("Unknown child mode: %s", mode)
            sys.exit(1)

    # ═══════════ Normal launcher ═══════════
    log.info("=" * 50)
    log.info("  %s v%s — Desktop Launcher", APP_NAME, APP_VERSION)
    log.info("  Bundle root : %s", BUNDLE_ROOT)
    log.info("  Executable  : %s", sys.executable)
    log.info("  Internal    : %s", os.path.join(BUNDLE_ROOT, "streamlit/static/index.html"))
    log.info("  User data   : %s", USER_DATA_DIR)

    # ── Bundle integrity check ─────────────
    bundle_ok, bundle_missing = verify_bundle_integrity()
    if bundle_ok:
        log.info("  Integ check : PASS")
    else:
        log.error("  Integ check : FAILED — %d missing", len(bundle_missing))
        for item in bundle_missing:
            log.error("    Missing: %s", item)
        log.error("")
        log.error("A3-Agent installation appears corrupted.")
        log.error("Please re-download from the official release:")
        log.error("  https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases")
        log.error("")
        log.info("=" * 50)
        sys.exit(1)
    log.info("=" * 50)

    processes: dict[str, subprocess.Popen | None] = {"api": None, "ui": None}

    # Handle Ctrl+C / SIGTERM
    def _handle_signal(signum, frame):
        log.info("Received signal %d", signum)
        shutdown(processes)
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        # [1/5] Seed user data
        log.info("[1/5] Initializing user data...")
        seed_user_data()
        log.info("      User data ready [OK]")

        # [2/5] Start FastAPI
        log.info("[2/5] Starting AI Backend (FastAPI)...")
        processes["api"] = start_service(
            ["uvicorn", "--host", "127.0.0.1", "--port", str(API_PORT)], "FastAPI"
        )
        if processes["api"] is None:
            log.error("Failed to start backend — aborting")
            sys.exit(1)

        # [3/5] Health check
        log.info("[3/5] Waiting for API health check...")
        if not wait_for_health(HEALTH_URL):
            log.error("=" * 50)
            log.error("  STARTUP FAILED — Backend did not become healthy")
            log.error("  Check subprocess log for details:")
            log.error("    %s", os.path.join(LOG_DIR, "subprocess.log"))
            log.error("=" * 50)
            shutdown(processes)
            sys.exit(1)
        log.info("      API is healthy [OK]")

        # [4/5] Start Streamlit
        log.info("[4/5] Starting Learning Interface (Streamlit)...")
        processes["ui"] = start_service(
            ["streamlit", "--server.port", str(UI_PORT)], "Streamlit"
        )
        if processes["ui"] is None:
            log.error("Failed to start Streamlit — aborting")
            shutdown(processes)
            sys.exit(1)

        # [5/5] Open browser
        log.info("[5/5] Opening browser: %s", UI_URL)
        time.sleep(BROWSER_OPEN_DELAY)
        webbrowser.open(UI_URL)

        log.info("A3-Agent is running. Press Ctrl+C to stop.")

        # Wait for children (blocking)
        for proc in processes.values():
            if proc:
                proc.wait()

    except KeyboardInterrupt:
        pass
    finally:
        shutdown(processes)
        log.info("A3-Agent stopped.")


if __name__ == "__main__":
    main()
