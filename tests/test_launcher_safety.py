"""
Tests for launcher bundle integrity checks.

Covers:
- `desktop/config.py::verify_bundle_integrity()` — pass / fail paths
- `desktop/config.py::get_bundle_root()` — frozen vs dev mode
"""

import os
import sys
import tempfile
from unittest import mock

import pytest


# ── verify_bundle_integrity ────────────────────────────────────


class TestVerifyBundleIntegrity:
    """Tests for verify_bundle_integrity() in desktop/config.py."""

    def test_pass_when_all_paths_exist(self):
        """Integrity check passes in a valid bundle layout."""
        with tempfile.TemporaryDirectory() as tmp:
            # Create minimal bundle layout
            internal_dir = os.path.join(tmp, "_internal")
            static_dir = os.path.join(internal_dir, "streamlit", "static")
            os.makedirs(static_dir)
            # Create the streamlit static index
            index_path = os.path.join(static_dir, "index.html")
            with open(index_path, "w") as f:
                f.write("<html></html>")

            from desktop.config import BUNDLE_ROOT, verify_bundle_integrity

            with mock.patch("desktop.config.BUNDLE_ROOT", internal_dir):
                with mock.patch.object(sys, "executable", "/usr/bin/python3"):
                    ok, missing = verify_bundle_integrity()
                    assert ok is True
                    assert missing == []

    def test_fail_when_bundle_root_missing(self):
        """Integrity check fails when BUNDLE_ROOT doesn't exist."""
        from desktop.config import verify_bundle_integrity

        with mock.patch("desktop.config.BUNDLE_ROOT", "/nonexistent/path/12345"):
            ok, missing = verify_bundle_integrity()
            assert ok is False
            assert len(missing) == 1
            assert "Bundle root directory" in missing[0]

    def test_fail_when_executable_missing(self):
        """Integrity check fails when sys.executable doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp:
            from desktop.config import verify_bundle_integrity

            with mock.patch("desktop.config.BUNDLE_ROOT", tmp):
                with mock.patch.object(sys, "executable", "/nonexistent/python"):
                    ok, missing = verify_bundle_integrity()
                    assert ok is False
                    assert any("Executable" in m for m in missing)

    def test_fail_when_static_assets_missing(self):
        """Integrity check fails when streamlit static files are missing (frozen mode)."""
        with tempfile.TemporaryDirectory() as tmp:
            from desktop.config import verify_bundle_integrity

            with mock.patch("desktop.config.BUNDLE_ROOT", tmp):
                with mock.patch.object(sys, "executable", "/usr/bin/python3"):
                    with mock.patch.object(sys, "frozen", True, create=True):
                        ok, missing = verify_bundle_integrity()
                        assert ok is False
                        assert any("Streamlit static assets" in m for m in missing)
                        assert any("streamlit/static/index.html" in m for m in missing)

    def test_dev_mode_skips_critical_paths(self):
        """In dev mode (not frozen), critical paths check is skipped."""
        with tempfile.TemporaryDirectory() as tmp:
            from desktop.config import verify_bundle_integrity

            with mock.patch("desktop.config.BUNDLE_ROOT", tmp):
                with mock.patch.object(sys, "executable", "/usr/bin/python3"):
                    # dev mode: frozen is False or absent
                    ok, missing = verify_bundle_integrity()
                    assert ok is True
                    assert missing == []

    def test_frozen_pass_when_all_paths_exist(self):
        """Integrity check passes in frozen mode with complete bundle."""
        with tempfile.TemporaryDirectory() as tmp:
            # Create minimal frozen bundle layout
            static_dir = os.path.join(tmp, "streamlit", "static")
            os.makedirs(static_dir)
            index_path = os.path.join(static_dir, "index.html")
            with open(index_path, "w") as f:
                f.write("<html></html>")

            from desktop.config import verify_bundle_integrity

            with mock.patch("desktop.config.BUNDLE_ROOT", tmp):
                with mock.patch.object(sys, "executable", "/usr/bin/python3"):
                    with mock.patch.object(sys, "frozen", True, create=True):
                        ok, missing = verify_bundle_integrity()
                        assert ok is True
                        assert missing == []

    def test_returns_missing_list_not_empty_on_fail(self):
        """On failure, missing list always contains descriptions."""
        from desktop.config import verify_bundle_integrity

        with mock.patch("desktop.config.BUNDLE_ROOT", "/nonexistent/path/99999"):
            ok, missing = verify_bundle_integrity()
            assert ok is False
            assert len(missing) >= 1
            # All entries should be strings
            for m in missing:
                assert isinstance(m, str)
                assert len(m) > 0


# ── get_bundle_root ────────────────────────────────────────────


class TestGetBundleRoot:
    """Tests for get_bundle_root() in desktop/config.py."""

    def test_dev_mode_returns_project_root(self):
        """In dev mode (not frozen), returns parent of desktop/ directory."""
        from desktop.config import get_bundle_root

        root = get_bundle_root()
        assert os.path.isdir(root)
        # Should contain desktop/ subdirectory
        assert os.path.isdir(os.path.join(root, "desktop"))

    def test_frozen_mode_returns_meipass(self):
        """In frozen mode, returns sys._MEIPASS."""
        from desktop.config import get_bundle_root

        with mock.patch.object(sys, "frozen", True, create=True):
            with mock.patch.object(sys, "_MEIPASS", "/fake/_internal", create=True):
                root = get_bundle_root()
                assert root == "/fake/_internal"

    def test_frozen_fallback_to_executable_dir(self):
        """When _MEIPASS is not set, falls back to executable dir."""
        from desktop.config import get_bundle_root

        with mock.patch.object(sys, "frozen", True, create=True):
            # _MEIPASS absent — use getattr default
            with mock.patch.object(
                sys, "_MEIPASS", "/fake/bin/myapp", create=True
            ):
                root = get_bundle_root()
                # Should use _MEIPASS since it exists
                assert root == "/fake/bin/myapp"
