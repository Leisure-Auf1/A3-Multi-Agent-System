#!/usr/bin/env python3
"""
A3-Agent v1.0.0 — Release Validation Script

Checks the PyInstaller build output for correctness before distribution.
Run from project root after a successful PyInstaller build.

Usage:
    python scripts/release_check.py [--dist dist/A3-Agent]
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import zipfile

# ── Config ────────────────────────────────

REQUIRED_FILES = [
    "A3-Agent",                # or A3-Agent.exe on Windows
    "A3-Agent.exe",            # Windows bootloader
    "_internal/",
    "_internal/app.py",
    "_internal/src/",
    "_internal/src/api/server.py",
    "_internal/src/config/",
    "_internal/src/config/llm_config.py",
    "_internal/src/config/secret_manager.py",
    "_internal/src/config/onboarding.py",
    "_internal/web/",
    "_internal/web/app_v3.py",
    "_internal/web/settings_tab.py",
    "_internal/web/onboarding_page.py",
    "_internal/web/demo_dashboard.py",
    "_internal/web/competition_demo.py",
    "_internal/web/architecture_overview.py",
    "_internal/knowledge_base/",
    "_internal/storage/a3.db",
    "_internal/demo/fixtures/",
    "_internal/demo/fixtures/sample_profile.json",
    "_internal/demo/fixtures/learning_trace.json",
    "_internal/demo/fixtures/generated_resources.json",
    "_internal/.streamlit/config.toml",
    "_internal/.env.example",
    "_internal/base_library.zip",
]

MAX_SIZE_MB = 300
MIN_SIZE_MB = 50
WARN_SIZE_MB = 250


# ── Checks ─────────────────────────────────

def check_file(path: str) -> tuple[bool, str]:
    """Check if a required file/dir exists."""
    if path.endswith("/"):
        if os.path.isdir(path):
            return True, "ok"
        return False, "missing directory"
    else:
        if os.path.exists(path):
            return True, "ok"
        # Try alternate (Windows .exe)
        alt = path.replace("A3-Agent", "A3-Agent.exe")
        if os.path.exists(alt):
            return True, "ok (.exe variant)"
        return False, "missing file"


def check_size(path: str) -> tuple[bool, str]:
    """Check bundle size is within expected range."""
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    mb = total / (1024 * 1024)
    if mb > MAX_SIZE_MB:
        return False, f"{mb:.0f} MB — exceeds {MAX_SIZE_MB} MB max"
    elif mb < MIN_SIZE_MB:
        return False, f"{mb:.0f} MB — below {MIN_SIZE_MB} MB min"
    elif mb > WARN_SIZE_MB:
        return True, f"{mb:.0f} MB (warn: > {WARN_SIZE_MB} MB)"
    return True, f"{mb:.0f} MB"


def check_json_valid(path: str) -> tuple[bool, str]:
    """Check JSON file is valid and has expected keys."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return False, f"invalid JSON: {e}"

    checks = {
        "sample_profile.json": ["student_id", "profile"],
        "learning_trace.json": ["session_id", "trace"],
        "generated_resources.json": ["session_id", "resources"],
    }
    name = os.path.basename(path)
    expected = checks.get(name, [])
    missing = [k for k in expected if k not in data]
    if missing:
        return False, f"missing keys: {missing}"
    return True, f"valid ({len(json.dumps(data))} chars)"


def check_db(path: str) -> tuple[bool, str]:
    """Check SQLite database is valid and has expected tables."""
    import sqlite3
    try:
        conn = sqlite3.connect(path)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        conn.close()
        names = {t[0] for t in tables}
        expected = {"users", "learning_records", "chat_threads", "chat_messages", "resources", "sessions"}
        missing = expected - names
        if missing:
            return False, f"missing tables: {missing}"
        size_kb = os.path.getsize(path) / 1024
        return True, f"{len(names)} tables, {size_kb:.0f} KB"
    except Exception as e:
        return False, f"DB error: {e}"


def sha256(path: str) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Main ───────────────────────────────────

def main():
    dist = "dist/A3-Agent"
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg in ("--dist", "-d"):
            if i + 1 < len(args):
                dist = args[i + 1]
        elif arg.startswith("--dist="):
            dist = arg.split("=", 1)[1]

    if not os.path.isdir(dist):
        print(f"❌ Distribution directory not found: {dist}")
        print("   Run PyInstaller build first: desktop/build.bat")
        sys.exit(1)

    print("=" * 60)
    print(f"  A3-Agent v1.0.0 — Release Validation")
    print(f"  Target: {dist}")
    print("=" * 60)
    print()

    results = []

    # 1. Binary
    bin_name = "A3-Agent.exe" if os.path.exists(os.path.join(dist, "A3-Agent.exe")) else "A3-Agent"
    bin_path = os.path.join(dist, bin_name)
    results.append(("Binary", os.path.exists(bin_path), f"{bin_name}" if os.path.exists(bin_path) else "MISSING"))
    if os.path.exists(bin_path):
        results.append(("SHA256", True, sha256(bin_path)[:16] + "..."))

    # 2. Required files
    print("📁 Checking required files...")
    for path in REQUIRED_FILES:
        full = os.path.join(dist, path) if path.startswith("_internal") else os.path.join(dist, path)
        # Skip if it doesn't make sense (e.g. Windows file on Linux)
        if path == "A3-Agent.exe" and not os.path.exists(os.path.join(dist, "A3-Agent.exe")):
            continue
        if path == "A3-Agent" and os.path.exists(os.path.join(dist, "A3-Agent.exe")):
            continue
        ok, msg = check_file(full)
        icon = "✅" if ok else "❌"
        print(f"  {icon} {path}: {msg}")
        results.append((path, ok, msg))

    # 3. Size
    print()
    ok, msg = check_size(dist)
    icon = "✅" if ok else "❌"
    print(f"  {icon} Bundle size: {msg}")
    results.append(("Size", ok, msg))

    # 4. Demo fixtures
    print()
    print("📊 Checking demo fixtures...")
    for fixture in ["sample_profile.json", "learning_trace.json", "generated_resources.json"]:
        full = os.path.join(dist, "_internal", "demo", "fixtures", fixture)
        if os.path.exists(full):
            ok, msg = check_json_valid(full)
            icon = "✅" if ok else "❌"
            print(f"  {icon} {fixture}: {msg}")
            results.append((fixture, ok, msg))

    # 5. Database
    print()
    db_path = os.path.join(dist, "_internal", "storage", "a3.db")
    if os.path.exists(db_path):
        ok, msg = check_db(db_path)
        icon = "✅" if ok else "❌"
        print(f"  {icon} a3.db: {msg}")
        results.append(("Database", ok, msg))

    # ── Summary ─────────────────────────────
    print()
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = total - passed

    print("=" * 60)
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        print()
        print("❌ VALIDATION FAILED")
        sys.exit(1)
    else:
        print()
        print("✅ VALIDATION PASSED — Ready for release")


if __name__ == "__main__":
    main()
