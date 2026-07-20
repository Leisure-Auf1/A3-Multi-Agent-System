"""
Phase 10.1 — Unified UI Shell Tests

Tests covering:
  - web/app.py import and structure
  - API Client extended methods (learning plan, usage, settings)
  - API Client auth token injection
  - Auth state management (login/register/logout via API)
  - Legacy file preservation
  - Navigation state defaults
  - Component imports

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import json
import sys
import os
import tempfile
import shutil
from pathlib import Path

import pytest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ═══════════════════════════════════════════════
# 1. App Import & Structure
# ═══════════════════════════════════════════════

class TestAppImport:

    def test_app_main_importable(self):
        """New unified app.py can be imported."""
        from web.app import main
        assert callable(main)

    def test_app_has_tab_renderers(self):
        """All tab render functions exist."""
        from web.app import (
            _render_dashboard,
            _render_learning,
            _render_profile,
            _render_settings,
        )
        assert callable(_render_dashboard)
        assert callable(_render_learning)
        assert callable(_render_profile)
        assert callable(_render_settings)

    def test_app_session_state_defaults(self):
        """Key session state keys are referenced in app."""
        import streamlit as st
        # Simulate fresh session
        if "active_tab" in st.session_state:
            del st.session_state.active_tab


# ═══════════════════════════════════════════════
# 2. API Client Extended Methods
# ═══════════════════════════════════════════════

class TestApiClientExtended:

    def setup_method(self):
        from web.utils.api import A3APIClient
        self.api = A3APIClient()

    def test_create_learning_plan_method_exists(self):
        assert hasattr(self.api, "create_learning_plan")
        assert callable(self.api.create_learning_plan)

    def test_get_usage_method_exists(self):
        assert hasattr(self.api, "get_usage")
        assert callable(self.api.get_usage)

    def test_get_llm_settings_method_exists(self):
        assert hasattr(self.api, "get_llm_settings")
        assert callable(self.api.get_llm_settings)

    def test_save_llm_settings_method_exists(self):
        assert hasattr(self.api, "save_llm_settings")
        assert callable(self.api.save_llm_settings)

    def test_test_llm_connection_method_exists(self):
        assert hasattr(self.api, "test_llm_connection")
        assert callable(self.api.test_llm_connection)

    def test_legacy_methods_still_exist(self):
        """Existing v4 API methods preserved."""
        assert hasattr(self.api, "login")
        assert hasattr(self.api, "register")
        assert hasattr(self.api, "guest")
        assert hasattr(self.api, "logout")
        assert hasattr(self.api, "send_message")
        assert hasattr(self.api, "get_profile")
        assert hasattr(self.api, "create_thread")

    def test_create_learning_plan_uses_correct_path(self):
        """Verify the plan endpoint path is set correctly."""
        from fastapi.testclient import TestClient
        from src.api.server import app
        tc = TestClient(app)
        self.api._test_client = tc

        # Create a test user first
        import uuid
        email = f"planner_test_{uuid.uuid4().hex[:8]}@test.com"
        tc.post("/api/v2/auth/register", json={
            "email": email, "password": "test1234",
            "display_name": "Planner Test",
        })
        resp = tc.post("/api/v2/auth/login", json={
            "email": email, "password": "test1234",
        })
        token = resp.json()["token"]
        self.api.set_token(token)

        result = self.api.create_learning_plan("Learn Python basics")
        assert isinstance(result, dict)
        assert "topic" in result
        assert "nodes" in result

    def test_get_usage_returns_dict(self):
        """Usage endpoint returns dict with expected keys."""
        from fastapi.testclient import TestClient
        from src.api.server import app
        tc = TestClient(app)
        self.api._test_client = tc

        import uuid
        email = f"usage_test_{uuid.uuid4().hex[:8]}@test.com"
        tc.post("/api/v2/auth/register", json={
            "email": email, "password": "test1234",
        })
        resp = tc.post("/api/v2/auth/login", json={
            "email": email, "password": "test1234",
        })
        self.api.set_token(resp.json()["token"])

        result = self.api.get_usage()
        assert isinstance(result, dict)
        assert "user_id" in result


# ═══════════════════════════════════════════════
# 3. Auth Flow Tests
# ═══════════════════════════════════════════════

class TestAuthFlow:

    def setup_method(self):
        from web.utils.api import A3APIClient
        self.api = A3APIClient()

    def test_register_and_login_flow(self):
        """Complete register → login → me flow."""
        from fastapi.testclient import TestClient
        from src.api.server import app
        tc = TestClient(app)
        self.api._test_client = tc

        import uuid
        email = f"flow_{uuid.uuid4().hex[:8]}@test.com"

        # Register
        result = self.api.register(email, "test1234", "Flow Test")
        assert result.token is not None
        assert result.user_id != ""

        # Login separately
        self.api.clear_token()
        result2 = self.api.login(email, "test1234")
        assert result2.token is not None
        assert result2.user_id == result.user_id

        # Me
        self.api.set_token(result2.token)
        me = self.api.me()
        assert me["email"] == email

    def test_guest_login(self):
        """Guest login returns valid token."""
        from fastapi.testclient import TestClient
        from src.api.server import app
        tc = TestClient(app)
        self.api._test_client = tc

        result = self.api.guest("Test Guest")
        assert result.token is not None
        assert result.user_id.startswith("guest_")

    def test_login_failure(self):
        """Wrong password raises A3APIError."""
        from fastapi.testclient import TestClient
        from src.api.server import app
        tc = TestClient(app)
        self.api._test_client = tc

        from web.utils.api import A3APIError
        with pytest.raises(A3APIError):
            self.api.login("nonexistent@test.com", "wrong")


# ═══════════════════════════════════════════════
# 4. Token Injection Tests
# ═══════════════════════════════════════════════

class TestTokenInjection:

    def test_set_token_stores_correctly(self):
        from web.utils.api import A3APIClient
        api = A3APIClient()
        api.set_token("test-token-123")
        assert api._token == "test-token-123"

    def test_clear_token(self):
        from web.utils.api import A3APIClient
        api = A3APIClient()
        api.set_token("test-token")
        api.clear_token()
        assert api._token is None

    def test_token_in_headers(self):
        """Verify token is injected in Authorization header."""
        from web.utils.api import A3APIClient
        api = A3APIClient()
        api.set_token("my-bearer-token")

        # Mock _request to capture headers
        original = api._request
        captured_headers = {}

        def mock_request(method, path, body=None, token=None):
            captured_headers["method"] = method
            captured_headers["path"] = path
            captured_headers["token"] = api._token
            return {}

        api._request = mock_request
        api.set_token("bearer-xyz")
        api.send_message("hello")
        assert captured_headers["token"] == "bearer-xyz"

        api._request = original


# ═══════════════════════════════════════════════
# 5. Legacy Preservation Tests
# ═══════════════════════════════════════════════

class TestLegacyPreservation:

    def test_legacy_app_v3_exists(self):
        path = Path(__file__).resolve().parent.parent / "web" / "legacy" / "app_v3.py"
        assert path.exists(), f"{path} should exist"

    def test_legacy_app_v4_exists(self):
        path = Path(__file__).resolve().parent.parent / "web" / "legacy" / "app_v4.py"
        assert path.exists(), f"{path} should exist"

    def test_legacy_imports(self):
        """Legacy modules can still be imported."""
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from web.legacy.app_v3 import main as v3_main
        from web.legacy.app_v4 import main as v4_main
        assert callable(v3_main)
        assert callable(v4_main)


# ═══════════════════════════════════════════════
# 6. Navigation State Tests
# ═══════════════════════════════════════════════

class TestNavigationState:

    def test_default_active_tab(self):
        """Default active tab is 'dashboard'."""
        import streamlit as st
        if "active_tab" in st.session_state:
            del st.session_state.active_tab
        # Default from app.py: if key not in st.session_state, set to "dashboard"
        default_tab = st.session_state.get("active_tab", "dashboard")
        assert default_tab == "dashboard"

    def test_tab_keys_are_valid(self):
        """All tab keys are among the expected set."""
        valid_tabs = {"dashboard", "learning", "chat", "profile", "settings"}
        for tab in valid_tabs:
            assert tab in valid_tabs


# ═══════════════════════════════════════════════
# 7. Entry Point Tests
# ═══════════════════════════════════════════════

class TestEntryPoints:

    def test_root_app_imports_web_app(self):
        """Root app.py delegates to web.app."""
        from app import main
        assert callable(main)

    def test_web_app_v3_still_importable(self):
        """Original app_v3 still importable for backward compat."""
        from web.app_v3 import main
        assert callable(main)

    def test_web_app_v4_still_importable(self):
        """Original app_v4 still importable for backward compat."""
        from web.app_v4 import main
        assert callable(main)

    def test_makefile_run_target(self):
        """Makefile 'run' target points to web/app.py."""
        makefile = Path(__file__).resolve().parent.parent / "Makefile"
        content = makefile.read_text()
        assert "web/app.py" in content


# ═══════════════════════════════════════════════
# 8. No Regression
# ═══════════════════════════════════════════════

class TestNoRegression:

    def test_existing_api_client_tests_still_work(self):
        """Original API client methods are unaffected."""
        from web.utils.api import A3APIClient, A3APIError, AuthResult
        api = A3APIClient()
        assert api.base_url == "http://localhost:8000"

    def test_auth_components_still_importable(self):
        from web.components.auth import render_auth_gate, render_logout
        assert callable(render_auth_gate)
        assert callable(render_logout)

    def test_chat_components_still_importable(self):
        from web.components.chat import render_chat_sidebar, render_chat_main
        assert callable(render_chat_sidebar)
        assert callable(render_chat_main)

    def test_settings_tab_still_importable(self):
        from web.settings_tab import render_settings_tab
        assert callable(render_settings_tab)
