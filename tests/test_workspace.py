"""
Phase 9.0 — Workspace Tests

Covers:
- WorkspaceManager: create, delete, info
- User isolation: different students have separate files
- Artifact save/load/delete
- Course operations
- History append
- Edge cases: non-existent workspace, empty student IDs
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from workspace.manager import WorkspaceManager, WorkspaceInfo


# ──────────────────────────────────────────────
# 1. Workspace Lifecycle
# ──────────────────────────────────────────────

class TestWorkspaceLifecycle:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="a3_test_ws_")
        self.wm = WorkspaceManager(root=self.tmpdir)

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_workspace(self):
        path = self.wm.create_workspace("student_001")
        assert os.path.isdir(path)
        assert "student_001" in path

    def test_workspace_exists(self):
        assert self.wm.workspace_exists("student_001") is False
        self.wm.create_workspace("student_001")
        assert self.wm.workspace_exists("student_001") is True

    def test_delete_workspace(self):
        self.wm.create_workspace("student_001")
        assert self.wm.workspace_exists("student_001") is True
        self.wm.delete_workspace("student_001")
        assert self.wm.workspace_exists("student_001") is False

    def test_delete_nonexistent_workspace(self):
        result = self.wm.delete_workspace("nonexistent")
        assert result is False

    def test_get_workspace_info(self):
        self.wm.create_workspace("student_001")
        info = self.wm.get_workspace_info("student_001")
        assert info.student_id == "student_001"
        assert isinstance(info, WorkspaceInfo)

    def test_workspace_info_nonexistent(self):
        info = self.wm.get_workspace_info("nonexistent")
        assert info.course_count == 0
        assert info.artifact_counts == {}


# ──────────────────────────────────────────────
# 2. User Isolation
# ──────────────────────────────────────────────

class TestUserIsolation:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="a3_test_ws_")
        self.wm = WorkspaceManager(root=self.tmpdir)

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_different_users_have_separate_files(self):
        self.wm.save_artifact("user_a", "materials", "test.md", "content_a")
        self.wm.save_artifact("user_b", "materials", "test.md", "content_b")

        a = self.wm.load_artifact("user_a", "materials", "test.md")
        b = self.wm.load_artifact("user_b", "materials", "test.md")
        assert a == "content_a"
        assert b == "content_b"

    def test_user_a_cannot_see_user_b_artifacts(self):
        self.wm.save_artifact("user_a", "materials", "secret.md", "secret")
        # User b should not find this file
        artifacts = self.wm.list_artifacts("user_b")
        assert "secret.md" not in " ".join(artifacts)


# ──────────────────────────────────────────────
# 3. Artifact Operations
# ──────────────────────────────────────────────

class TestArtifactOperations:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="a3_test_ws_")
        self.wm = WorkspaceManager(root=self.tmpdir)

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_artifact(self):
        path = self.wm.save_artifact("student_001", "materials", "lesson1.md",
                                      "# Lesson 1\nContent")
        assert os.path.isfile(path)

    def test_load_artifact(self):
        self.wm.save_artifact("student_001", "materials", "lesson1.md", "content123")
        content = self.wm.load_artifact("student_001", "materials", "lesson1.md")
        assert content == "content123"

    def test_load_nonexistent_artifact(self):
        content = self.wm.load_artifact("student_001", "materials", "missing.md")
        assert content is None

    def test_list_artifacts(self):
        self.wm.save_artifact("student_001", "materials", "a.md", "a")
        self.wm.save_artifact("student_001", "materials", "b.md", "b")
        artifacts = self.wm.list_artifacts("student_001", "materials")
        assert len(artifacts) == 2

    def test_list_artifacts_empty(self):
        self.wm.create_workspace("student_001")
        artifacts = self.wm.list_artifacts("student_001", "materials")
        assert artifacts == []

    def test_delete_artifact(self):
        self.wm.save_artifact("student_001", "materials", "to_delete.md", "x")
        assert self.wm.artifact_exists("student_001", "materials", "to_delete.md")
        self.wm.delete_artifact("student_001", "materials", "to_delete.md")
        assert not self.wm.artifact_exists("student_001", "materials", "to_delete.md")

    def test_delete_nonexistent_artifact(self):
        result = self.wm.delete_artifact("student_001", "materials", "missing.md")
        assert result is False

    def test_artifact_exists(self):
        self.wm.save_artifact("student_001", "materials", "exists.md", "yes")
        assert self.wm.artifact_exists("student_001", "materials", "exists.md") is True
        assert self.wm.artifact_exists("student_001", "materials", "no.md") is False


# ──────────────────────────────────────────────
# 4. Course Operations
# ──────────────────────────────────────────────

class TestCourseOperations:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="a3_test_ws_")
        self.wm = WorkspaceManager(root=self.tmpdir)

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_and_load_course(self):
        self.wm.save_course("student_001", "python_basics.md", "# Python Basics\nContent")
        content = self.wm.load_course("student_001", "python_basics.md")
        assert "# Python Basics" in content

    def test_list_courses(self):
        self.wm.save_course("student_001", "course_a.md", "a")
        self.wm.save_course("student_001", "course_b.md", "b")
        courses = self.wm.list_courses("student_001")
        assert len(courses) == 2

    def test_list_courses_empty(self):
        self.wm.create_workspace("student_001")
        courses = self.wm.list_courses("student_001")
        assert courses == []

    def test_load_nonexistent_course(self):
        content = self.wm.load_course("student_001", "missing.md")
        assert content is None


# ──────────────────────────────────────────────
# 5. History
# ──────────────────────────────────────────────

class TestHistory:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="a3_test_ws_")
        self.wm = WorkspaceManager(root=self.tmpdir)

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_append_history(self):
        entry = {"action": "generate_ppt", "title": "Python Lesson"}
        path = self.wm.append_history("student_001", entry)
        assert os.path.isfile(path)

    def test_history_has_timestamp(self):
        # Read the history file and check
        self.wm.append_history("student_001", {"action": "test"})
        from workspace.manager import WorkspaceManager as WM
        history_path = os.path.join(self.tmpdir, "student_001", "history", "history.jsonl")
        assert os.path.isfile(history_path)
        with open(history_path, "r") as f:
            line = f.readline()
        data = json.loads(line)
        assert "timestamp" in data


# ──────────────────────────────────────────────
# 6. Workspace Info Tests
# ──────────────────────────────────────────────

class TestWorkspaceInfo:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="a3_test_ws_")
        self.wm = WorkspaceManager(root=self.tmpdir)

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_info_counts_courses(self):
        self.wm.save_course("student_001", "c1.md", "content")
        self.wm.save_course("student_001", "c2.md", "content")
        info = self.wm.get_workspace_info("student_001")
        assert info.course_count == 2

    def test_info_counts_artifacts_by_type(self):
        self.wm.save_artifact("student_001", "materials", "m1.md", "c")
        self.wm.save_artifact("student_001", "ppt", "p1.pptx", "c")
        self.wm.save_artifact("student_001", "images", "i1.svg", "c")
        info = self.wm.get_workspace_info("student_001")
        assert info.artifact_counts["materials"] == 1
        assert info.artifact_counts["ppt"] == 1
        assert info.artifact_counts["images"] == 1

    def test_info_total_size(self):
        self.wm.save_artifact("student_001", "materials", "big.md", "x" * 1000)
        info = self.wm.get_workspace_info("student_001")
        assert info.total_size_bytes >= 1000

    def test_info_to_dict(self):
        info = WorkspaceInfo(
            student_id="s1", root_path="/tmp/s1",
            created_at="2026-01-01T00:00:00",
            course_count=3,
            artifact_counts={"materials": 5},
        )
        d = info.to_dict()
        assert d["student_id"] == "s1"
        assert d["course_count"] == 3


# ──────────────────────────────────────────────
# 7. Edge Cases
# ──────────────────────────────────────────────

class TestEdgeCases:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="a3_test_ws_")
        self.wm = WorkspaceManager(root=self.tmpdir)

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_default_root(self):
        wm = WorkspaceManager()
        assert ".a3-agent" in wm.get_root()

    def test_save_creates_workspace_automatically(self):
        self.wm.save_artifact("new_user", "materials", "auto.md", "auto")
        assert self.wm.workspace_exists("new_user") is True

    def test_list_all_artifacts_across_categories(self):
        self.wm.save_artifact("student_001", "materials", "a.md", "a")
        self.wm.save_artifact("student_001", "ppt", "b.pptx", "b")
        all_artifacts = self.wm.list_artifacts("student_001")
        assert len(all_artifacts) >= 2

    def test_save_artifact_bytes(self):
        data = b'\x89PNG\r\n\x1a\n'  # PNG header-ish
        path = self.wm.save_artifact_bytes("student_001", "ppt", "test.pptx", data)
        assert os.path.isfile(path)
        with open(path, "rb") as f:
            assert f.read()[:4] == b'\x89PNG'
