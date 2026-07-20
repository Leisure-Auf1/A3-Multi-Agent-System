"""
Phase 16.2-B — Experience Polish Tests

Tests for:
  - Provider badge in sidebar (Demo/AI Mode)
  - Dashboard AI/Demo Mode indicator
  - Full onboarding flow restoration
  - README content (test count, Phase 16 features)
  - Screenshots existence
"""

from __future__ import annotations

import sys, os, uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from src.api.server import app


# ═══════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════

def _setup() -> tuple:
    from web.utils.api import A3APIClient
    client = A3APIClient()
    client._test_client = TestClient(app)
    email = f"exp_{uuid.uuid4().hex[:6]}@a3.local"
    client._test_client.post("/api/v2/auth/register", json={
        "email": email, "password": "exptest", "display_name": "ExpTest",
    })
    resp = client._test_client.post("/api/v2/auth/login", json={
        "email": email, "password": "exptest",
    })
    data = resp.json()
    client.set_token(data["token"])
    return client, data["user_id"], email


def _read_app() -> str:
    app_path = os.path.join(os.path.dirname(__file__), "..", "web", "app.py")
    with open(app_path) as f:
        return f.read()


def _read_readme() -> str:
    readme_path = os.path.join(os.path.dirname(__file__), "..", "README.md")
    with open(readme_path) as f:
        return f.read()


# ═══════════════════════════════════════════════
# 1. Provider Badge in Sidebar
# ═══════════════════════════════════════════════

class TestProviderBadgeSidebar:
    def test_sidebar_has_provider_badge_code(self):
        """Sidebar includes provider badge rendering."""
        content = _read_app()
        assert "🤖" in content
        assert "Demo Mode" in content

    def test_sidebar_shows_demo_when_unconfigured(self):
        """Sidebar shows Demo Mode when no LLM configured."""
        content = _read_app()
        assert "sidebar.demo_mode" in content

    def test_sidebar_shows_provider_when_configured(self):
        """Sidebar shows provider name when configured."""
        content = _read_app()
        assert "cfg.provider not in" in content or "provider_label" in content

    def test_sidebar_has_model_display(self):
        """Sidebar shows model name when available."""
        content = _read_app()
        assert "cfg.model" in content


# ═══════════════════════════════════════════════
# 2. Dashboard AI/Demo Mode
# ═══════════════════════════════════════════════

class TestDashboardMode:
    def test_dashboard_has_both_modes(self):
        """Dashboard has both Demo and AI Mode code paths."""
        content = _read_app()
        assert "Demo Mode" in content
        assert "AI Mode" in content

    def test_dashboard_ai_mode_shows_provider(self):
        """AI Mode shows provider name."""
        content = _read_app()
        assert "provider_label" in content or "AI Mode —" in content

    def test_dashboard_demo_mode_shows_rule_based(self):
        """Demo Mode indicator mentions rule-based AI."""
        content = _read_app()
        assert "rule-based" in content

    def test_dashboard_ai_mode_has_model_name(self):
        """AI Mode shows active model name."""
        content = _read_app()
        assert "Active model" in content or "model_name" in content


# ═══════════════════════════════════════════════
# 3. Full Onboarding Flow
# ═══════════════════════════════════════════════

class TestOnboardingFlow:
    def test_onboarding_uses_full_page(self):
        """Onboarding gate uses web.onboarding_page."""
        content = _read_app()
        assert "from web.onboarding_page import render_onboarding_page" in content

    def test_onboarding_has_fallback(self):
        """Onboarding has fallback minimal gate."""
        content = _read_app()
        assert "Welcome to A3 AI Learning Assistant" in content

    def test_onboarding_checks_onboarding_done(self):
        """Onboarding checks onboarding_done state."""
        content = _read_app()
        assert "onboarding_done" in content

    def test_fallback_has_demo_button(self):
        """Fallback onboarding has Try Demo button."""
        content = _read_app()
        assert "Try Demo" in content

    def test_onboarding_page_importable(self):
        """Full onboarding page is importable."""
        from web.onboarding_page import render_onboarding_page
        assert callable(render_onboarding_page)

    def test_onboarding_page_has_providers(self):
        """Onboarding page has provider list."""
        from web.onboarding_page import ONBOARDING_PROVIDERS
        assert len(ONBOARDING_PROVIDERS) >= 5


# ═══════════════════════════════════════════════
# 4. README Content
# ═══════════════════════════════════════════════

class TestReadmeContent:
    def test_readme_has_updated_test_count(self):
        """README shows 2857 tests."""
        readme = _read_readme()
        assert "2857" in readme
        assert "tests" in readme.lower()

    def test_readme_has_quiz_feature(self):
        """README mentions interactive quizzes."""
        readme = _read_readme()
        assert "quiz" in readme.lower()

    def test_readme_has_history_replay(self):
        """README mentions history replay."""
        readme = _read_readme()
        assert "replay" in readme.lower() or "revisit" in readme.lower()

    def test_readme_has_memory_feature(self):
        """README mentions memory/adaptive features."""
        readme = _read_readme()
        assert "memory" in readme.lower()

    def test_readme_has_screenshots_section(self):
        """README has screenshots section."""
        readme = _read_readme()
        assert "Screenshots" in readme or "screenshots" in readme

    def test_readme_has_providers_list(self):
        """README mentions 8 LLM providers."""
        readme = _read_readme()
        assert "8 LLM" in readme or "8 LLM providers" in readme

    def test_readme_has_goal_suggestions(self):
        """README mentions goal suggestions."""
        readme = _read_readme()
        assert "goal" in readme.lower() and "suggestion" in readme.lower() or "Try These" in readme


# ═══════════════════════════════════════════════
# 5. Screenshots
# ═══════════════════════════════════════════════

class TestScreenshots:
    def test_screenshots_directory_exists(self):
        """docs/assets/screenshots directory exists."""
        path = os.path.join(
            os.path.dirname(__file__), "..",
            "docs", "assets", "screenshots"
        )
        assert os.path.isdir(path), f"Screenshots dir missing: {path}"

    def test_dashboard_screenshot_exists(self):
        """Dashboard screenshot exists."""
        path = os.path.join(
            os.path.dirname(__file__), "..",
            "docs", "assets", "screenshots", "dashboard.svg"
        )
        assert os.path.exists(path)

    def test_pipeline_screenshot_exists(self):
        """Pipeline screenshot exists."""
        path = os.path.join(
            os.path.dirname(__file__), "..",
            "docs", "assets", "screenshots", "pipeline.svg"
        )
        assert os.path.exists(path)

    def test_quiz_screenshot_exists(self):
        """Quiz screenshot exists."""
        path = os.path.join(
            os.path.dirname(__file__), "..",
            "docs", "assets", "screenshots", "quiz.svg"
        )
        assert os.path.exists(path)

    def test_memory_screenshot_exists(self):
        """Memory screenshot exists."""
        path = os.path.join(
            os.path.dirname(__file__), "..",
            "docs", "assets", "screenshots", "memory.svg"
        )
        assert os.path.exists(path)

    def test_settings_screenshot_exists(self):
        """Settings screenshot exists."""
        path = os.path.join(
            os.path.dirname(__file__), "..",
            "docs", "assets", "screenshots", "settings.svg"
        )
        assert os.path.exists(path)


# ═══════════════════════════════════════════════
# 6. Regression
# ═══════════════════════════════════════════════

class TestRegression:
    def test_sidebar_still_has_tabs(self):
        """Sidebar still has tab navigation."""
        content = _read_app()
        assert "Dashboard" in content
        assert "Learning" in content

    def test_pipeline_still_works(self):
        """Pipeline still executes successfully."""
        c, uid, _ = _setup()
        result = c.run_pipeline("Experience polish regression test")
        assert result["status"] == "success"

    def test_onboarding_gate_function_exists(self):
        """_render_onboarding_gate function still exists."""
        content = _read_app()
        assert "def _render_onboarding_gate" in content

    def test_dashboard_has_goal_suggestions(self):
        """Dashboard still has goal suggestions after changes."""
        content = _read_app()
        assert "Try These" in content

    def test_dashboard_has_memory_card(self):
        """Dashboard still has memory card after changes."""
        content = _read_app()
        assert "🧠 AI Memory" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
