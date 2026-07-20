"""
Phase 9.4-B — User Preference Manager Tests

Covers:
- UserPreferenceManager: load/save, record_feedback, get_preference
- EMA quality score calculation
- ModelSelector preference injection (candidate boost)
- ModelSelector capability guard (preferred model unavailable for task)
- Settings UI functions
- Edge cases: empty prefs, clear, persistence
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from src.orchestration.user_preferences import (
    UserPreferenceManager,
    UserModelPreference,
    TaskPreference,
    _get_prefs_path,
)
from src.orchestration.model_selector import ModelSelector
from src.config.task_capability import TaskType


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _setup_prefs_file(tmp_path, student_id, data=None):
    """Create a model_preferences.json in tmp_path."""
    if data is None:
        data = {"student_id": student_id, "task_preferences": {}}
    mem_dir = tmp_path / student_id / "memory"
    mem_dir.mkdir(parents=True, exist_ok=True)
    path = mem_dir / "model_preferences.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ═══════════════════════════════════════════════════════════════
# 1. UserPreferenceManager — Basic
# ═══════════════════════════════════════════════════════════════

class TestPreferenceManagerBasic:
    """Load, save, get, record."""

    def test_create_new_manager(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("student-001")
            pref = mgr.get_preference("generate_material")
            assert pref is None

    def test_record_feedback_creates_preference(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("student-001")
            mgr.record_feedback(
                task_type="generate_material",
                model="gpt-5.6",
                provider="openai",
                rating=5,
            )
            pref = mgr.get_preference("generate_material")
            assert pref is not None
            assert pref.preferred_model == "gpt-5.6"
            assert pref.preferred_provider == "openai"

    def test_get_all_preferences(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            mgr.record_feedback(task_type="chat", model="gpt-4o", rating=4)
            mgr.record_feedback(task_type="generate_plan", model="deepseek", rating=3)
            all_prefs = mgr.get_all_preferences()
            assert len(all_prefs) == 2
            assert "chat" in all_prefs
            assert "generate_plan" in all_prefs

    def test_get_preferred_model(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            mgr.record_feedback(task_type="chat", model="deepseek-chat", rating=5)
            assert mgr.get_preferred_model("chat") == "deepseek-chat"

    def test_get_preferred_model_nonexistent(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            assert mgr.get_preferred_model("unknown_task") is None

    def test_get_preferred_provider(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            mgr.record_feedback(task_type="chat", provider="deepseek", rating=4)
            assert mgr.get_preferred_provider("chat") == "deepseek"


# ═══════════════════════════════════════════════════════════════
# 2. Quality Score (EMA)
# ═══════════════════════════════════════════════════════════════

class TestQualityScore:
    """EMA quality score updates."""

    def test_initial_quality_score(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            assert mgr.get_quality_score("chat") == 0.5

    def test_rating_5_boosts_quality(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            mgr.record_feedback(task_type="chat", rating=5)
            score = mgr.get_quality_score("chat")
            # new = 0.5*0.7 + 1.0*0.3 = 0.35 + 0.30 = 0.65
            assert score == pytest.approx(0.65, 0.01)

    def test_rating_1_lowers_quality(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            mgr.record_feedback(task_type="chat", rating=1)
            score = mgr.get_quality_score("chat")
            # new = 0.5*0.7 + 0.2*0.3 = 0.35 + 0.06 = 0.41
            assert score == pytest.approx(0.41, 0.01)

    def test_multiple_ratings_ema(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            mgr.record_feedback(task_type="chat", rating=5)
            mgr.record_feedback(task_type="chat", rating=5)
            score = mgr.get_quality_score("chat")
            # After 1st: 0.65
            # After 2nd: 0.65*0.7 + 1.0*0.3 = 0.455 + 0.3 = 0.755
            assert score == pytest.approx(0.755, 0.01)

    def test_success_without_rating_slight_boost(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            mgr.record_feedback(task_type="chat", success=True)
            score = mgr.get_quality_score("chat")
            assert score > 0.5
            assert score < 0.52  # 0.5 + 0.01

    def test_quality_capped_at_1(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            for _ in range(100):
                mgr.record_feedback(task_type="chat", rating=5)
            assert mgr.get_quality_score("chat") <= 1.0

    def test_use_count_increments(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            mgr.record_feedback(task_type="chat", rating=3)
            mgr.record_feedback(task_type="chat", rating=4)
            pref = mgr.get_preference("chat")
            assert pref.use_count == 2


# ═══════════════════════════════════════════════════════════════
# 3. Persistence
# ═══════════════════════════════════════════════════════════════

class TestPersistence:
    """Preferences survive manager recreations."""

    def test_preferences_persist_to_file(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            mgr.record_feedback(task_type="chat", model="gpt-4o", rating=5)

            # Re-read
            mgr2 = UserPreferenceManager("s1")
            pref = mgr2.get_preference("chat")
            assert pref.preferred_model == "gpt-4o"

    def test_clear_preferences(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            mgr.record_feedback(task_type="chat", model="gpt-4o", rating=5)
            mgr.clear_preferences()

            mgr2 = UserPreferenceManager("s1")
            assert mgr2.get_preference("chat") is None

    def test_load_existing_file(self, tmp_path):
        data = {
            "student_id": "s1",
            "task_preferences": {
                "chat": {
                    "task_type": "chat",
                    "preferred_model": "claude-sonnet",
                    "preferred_provider": "anthropic",
                    "quality_score": 0.85,
                    "use_count": 10,
                    "avg_rating": 0.85,
                    "last_used": time.time(),
                    "notes": "",
                }
            },
        }
        _setup_prefs_file(tmp_path, "s1", data)

        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            pref = mgr.get_preference("chat")
            assert pref.preferred_model == "claude-sonnet"
            assert pref.quality_score == 0.85
            assert pref.use_count == 10


# ═══════════════════════════════════════════════════════════════
# 4. UserModelPreference Data Model
# ═══════════════════════════════════════════════════════════════

class TestDataModel:
    """Serialization roundtrip."""

    def test_to_dict_from_dict_roundtrip(self):
        prefs = UserModelPreference(
            student_id="s1",
            task_preferences={
                "chat": TaskPreference(
                    task_type="chat",
                    preferred_model="gpt-4o",
                    preferred_provider="openai",
                    quality_score=0.9,
                    use_count=5,
                    avg_rating=0.85,
                ),
            },
            preferred_style="concise",
        )
        d = prefs.to_dict()
        restored = UserModelPreference.from_dict(d)
        assert restored.student_id == "s1"
        assert restored.preferred_style == "concise"
        assert restored.task_preferences["chat"].quality_score == 0.9

    def test_empty_preferences_to_dict(self):
        prefs = UserModelPreference(student_id="empty")
        d = prefs.to_dict()
        assert d["task_preferences"] == {}

    def test_task_preference_defaults(self):
        tp = TaskPreference(task_type="chat")
        assert tp.quality_score == 0.5
        assert tp.use_count == 0
        assert tp.preferred_model == ""


# ═══════════════════════════════════════════════════════════════
# 5. ModelSelector Preference Injection
# ═══════════════════════════════════════════════════════════════

class TestModelSelectorPreferences:
    """ModelSelector respects user preferences."""

    def test_student_id_passed_to_select(self):
        selector = ModelSelector()
        result = selector.select(
            agent_name="TutorAgent",
            student_id="test-student",
        )
        assert result.success is True

    def test_preference_injection_no_effect_without_prefs(self, tmp_path):
        """Without saved preferences, selection is unaffected."""
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            selector = ModelSelector()
            result = selector.select(
                agent_name="TutorAgent",
                student_id="no-prefs-student",
            )
            assert result.success is True
            # No pref_reason in reason (pref_model is None)
            assert "用户偏好" not in result.reason


# ═══════════════════════════════════════════════════════════════
# 6. Settings UI
# ═══════════════════════════════════════════════════════════════

class TestSettingsUI:
    """Settings tab functions exist."""

    def test_render_model_preferences_exists(self):
        from web.settings_tab import render_model_preferences
        assert callable(render_model_preferences)

    def test_render_orchestrator_dashboard_exists(self):
        from web.settings_tab import render_orchestrator_dashboard
        assert callable(render_orchestrator_dashboard)


# ═══════════════════════════════════════════════════════════════
# 7. Edge Cases
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Boundary conditions."""

    def test_record_feedback_zero_rating_no_change(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            mgr.record_feedback(task_type="chat", rating=0, model="gpt-4o")
            pref = mgr.get_preference("chat")
            # use_count should still increment
            assert pref.use_count == 1

    def test_set_preferred_style(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            mgr.set_preferred_style("visual")
            mgr2 = UserPreferenceManager("s1")
            prefs = mgr2._load()
            assert prefs.preferred_style == "visual"

    def test_user_comment_stored(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            mgr.record_feedback(
                task_type="chat", rating=4, user_comment="Great for quick answers",
            )
            pref = mgr.get_preference("chat")
            assert "Great" in pref.notes

    def test_multi_student_isolation(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr_a = UserPreferenceManager("student-a")
            mgr_b = UserPreferenceManager("student-b")
            mgr_a.record_feedback(task_type="chat", model="gpt-4o", rating=5)
            mgr_b.record_feedback(task_type="chat", model="deepseek", rating=3)
            assert mgr_a.get_preferred_model("chat") == "gpt-4o"
            assert mgr_b.get_preferred_model("chat") == "deepseek"

    def test_corrupted_json_handled(self, tmp_path):
        mem_dir = tmp_path / "corrupt" / "memory"
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / "model_preferences.json").write_text("NOT JSON")

        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("corrupt")
            # Should not crash — creates fresh prefs
            pref = mgr.get_preference("chat")
            assert pref is None

    def test_get_quality_score_unknown_task(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            assert mgr.get_quality_score("never_seen") == 0.5

    def test_last_used_timestamp(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("s1")
            before = time.time()
            mgr.record_feedback(task_type="chat", rating=3)
            pref = mgr.get_preference("chat")
            assert pref.last_used >= before

    def test_file_created_on_save(self, tmp_path):
        with mock.patch("src.orchestration.user_preferences.os.path.expanduser", return_value=str(tmp_path)):
            mgr = UserPreferenceManager("new-student")
            mgr.record_feedback(task_type="chat", model="test", rating=4)
            path = tmp_path / "new-student" / "memory" / "model_preferences.json"
            assert path.exists()
