"""
Phase 9.0 — User Workspace Manager

Per-user learning workspace with isolated storage.

Structure:
  workspace/
    {student_id}/
      courses/
      artifacts/
        materials/   (.md)
        ppt/         (.pptx)
        images/      (.svg)
        videos/      (.md, .srt, .json)
      memory/
      history/

Architecture: does NOT modify Veritas-Core or src/core/
"""

from __future__ import annotations
import json
import os
import shutil
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ── Default workspace root ────────────────────

DEFAULT_WORKSPACE_ROOT = os.path.expanduser("~/.a3-agent/workspace")


@dataclass
class WorkspaceInfo:
    """Metadata about a user workspace."""
    student_id: str
    root_path: str
    created_at: str = ""
    course_count: int = 0
    artifact_counts: Dict[str, int] = field(default_factory=dict)
    total_size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "root_path": self.root_path,
            "created_at": self.created_at,
            "course_count": self.course_count,
            "artifact_counts": self.artifact_counts,
            "total_size_bytes": self.total_size_bytes,
        }


class WorkspaceManager:
    """
    Per-user workspace manager.

    Each student gets an isolated workspace directory with:
      - courses/    (teaching materials as .md)
      - artifacts/  (generated PPTs, images, videos)
      - memory/     (learning memory files)
      - history/    (session history)

    Usage:
        wm = WorkspaceManager()
        wm.create_workspace("student_001")
        wm.save_artifact("student_001", "materials", "lesson1.md", content)
    """

    def __init__(self, root: str = ""):
        self._root = root or DEFAULT_WORKSPACE_ROOT

    # ── Workspace lifecycle ──────────

    def create_workspace(self, student_id: str) -> str:
        """Create workspace directories for a student. Returns root path."""
        ws_path = self._ws_path(student_id)
        for subdir in ["courses", "artifacts/materials", "artifacts/ppt",
                        "artifacts/images", "artifacts/videos", "memory", "history"]:
            os.makedirs(os.path.join(ws_path, subdir), exist_ok=True)
        return ws_path

    def delete_workspace(self, student_id: str) -> bool:
        """Delete entire workspace for a student."""
        ws_path = self._ws_path(student_id)
        if os.path.isdir(ws_path):
            shutil.rmtree(ws_path)
            return True
        return False

    def workspace_exists(self, student_id: str) -> bool:
        """Check if workspace exists."""
        return os.path.isdir(self._ws_path(student_id))

    def get_workspace_info(self, student_id: str) -> WorkspaceInfo:
        """Get workspace metadata."""
        ws_path = self._ws_path(student_id)
        info = WorkspaceInfo(
            student_id=student_id,
            root_path=ws_path,
            created_at="",
        )

        if not os.path.isdir(ws_path):
            return info

        # Count courses
        courses_dir = os.path.join(ws_path, "courses")
        if os.path.isdir(courses_dir):
            info.course_count = len([
                f for f in os.listdir(courses_dir) if f.endswith(".md")
            ])

        # Count artifacts by type
        artifacts_dir = os.path.join(ws_path, "artifacts")
        for atype in ["materials", "ppt", "images", "videos"]:
            adir = os.path.join(artifacts_dir, atype)
            if os.path.isdir(adir):
                info.artifact_counts[atype] = len(os.listdir(adir))
            else:
                info.artifact_counts[atype] = 0

        # Total size
        total = 0
        for dirpath, dirnames, filenames in os.walk(ws_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
        info.total_size_bytes = total

        # Created time from oldest file
        try:
            info.created_at = datetime.fromtimestamp(
                os.path.getctime(ws_path), tz=timezone.utc
            ).isoformat()
        except OSError:
            pass

        return info

    # ── Artifact operations ───────────

    def save_artifact(
        self,
        student_id: str,
        category: str,
        filename: str,
        content: str,
    ) -> str:
        """
        Save an artifact to the user's workspace.

        Args:
            student_id: Student identifier
            category: Artifact type (materials, ppt, images, videos)
            filename: File name
            content: File content (string)

        Returns:
            Absolute path to saved file
        """
        self.create_workspace(student_id)
        file_path = os.path.join(
            self._ws_path(student_id), "artifacts", category, filename
        )
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def save_artifact_bytes(
        self,
        student_id: str,
        category: str,
        filename: str,
        content: bytes,
    ) -> str:
        """Save binary artifact (e.g. .pptx)."""
        self.create_workspace(student_id)
        file_path = os.path.join(
            self._ws_path(student_id), "artifacts", category, filename
        )
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(content)
        return file_path

    def load_artifact(
        self,
        student_id: str,
        category: str,
        filename: str,
    ) -> Optional[str]:
        """Load artifact content as string."""
        file_path = os.path.join(
            self._ws_path(student_id), "artifacts", category, filename
        )
        if not os.path.isfile(file_path):
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def list_artifacts(
        self,
        student_id: str,
        category: str = "",
    ) -> List[str]:
        """
        List artifacts for a student.

        Args:
            student_id: Student identifier
            category: Optional filter (materials, ppt, images, videos)

        Returns:
            List of file paths
        """
        if category:
            base = os.path.join(self._ws_path(student_id), "artifacts", category)
        else:
            base = os.path.join(self._ws_path(student_id), "artifacts")

        if not os.path.isdir(base):
            return []

        results = []
        for dirpath, dirnames, filenames in os.walk(base):
            for f in filenames:
                results.append(os.path.join(dirpath, f))
        return sorted(results)

    def delete_artifact(
        self,
        student_id: str,
        category: str,
        filename: str,
    ) -> bool:
        """Delete a single artifact."""
        file_path = os.path.join(
            self._ws_path(student_id), "artifacts", category, filename
        )
        if os.path.isfile(file_path):
            os.remove(file_path)
            return True
        return False

    def artifact_exists(
        self,
        student_id: str,
        category: str,
        filename: str,
    ) -> bool:
        """Check if an artifact exists."""
        return os.path.isfile(
            os.path.join(self._ws_path(student_id), "artifacts", category, filename)
        )

    # ── Course operations ──────────────

    def save_course(
        self,
        student_id: str,
        filename: str,
        content: str,
    ) -> str:
        """Save a course/teaching material as markdown."""
        self.create_workspace(student_id)
        file_path = os.path.join(self._ws_path(student_id), "courses", filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def load_course(self, student_id: str, filename: str) -> Optional[str]:
        """Load a course by filename."""
        file_path = os.path.join(self._ws_path(student_id), "courses", filename)
        if not os.path.isfile(file_path):
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def list_courses(self, student_id: str) -> List[str]:
        """List all courses for a student."""
        courses_dir = os.path.join(self._ws_path(student_id), "courses")
        if not os.path.isdir(courses_dir):
            return []
        return sorted([
            f for f in os.listdir(courses_dir) if f.endswith(".md")
        ])

    # ── History ────────────────────────

    def append_history(
        self,
        student_id: str,
        entry: Dict[str, Any],
    ) -> str:
        """Append a history entry."""
        self.create_workspace(student_id)
        history_path = os.path.join(self._ws_path(student_id), "history", "history.jsonl")
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        with open(history_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return history_path

    # ── Multi-User Workspace (Phase 9.5-B) ──

    def get_user_path(self, user_id: str) -> str:
        """Get workspace root path for a user."""
        return self._ws_path(user_id)

    def list_workspace_users(self) -> List[str]:
        """List all user IDs with workspaces."""
        if not os.path.isdir(self._root):
            return []
        return sorted([
            d for d in os.listdir(self._root)
            if os.path.isdir(os.path.join(self._root, d))
            and not d.startswith(".")
        ])

    def get_workspace_paths(self, user_id: str) -> Dict[str, str]:
        """Get all sub-paths for a user workspace.

        Returns:
            { "root": "...", "sessions": "...", "artifacts": "...",
              "memory": "...", "history": "...", "usage": "..." }
        """
        base = self._ws_path(user_id)
        return {
            "root": base,
            "sessions": os.path.join(base, "history", "sessions"),
            "artifacts": os.path.join(base, "artifacts"),
            "memory": os.path.join(base, "memory"),
            "history": os.path.join(base, "history"),
            "usage": os.path.join(base, "usage"),
        }

    # ── Usage tracking (Phase 9.5-B) ───

    def append_usage(
        self,
        user_id: str,
        entry: Dict[str, Any],
    ) -> str:
        """Append a usage record for the user."""
        self.create_workspace(user_id)
        usage_path = os.path.join(self._ws_path(user_id), "usage", "usage.jsonl")
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        os.makedirs(os.path.dirname(usage_path), exist_ok=True)
        with open(usage_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return usage_path

    def get_usage_records(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get recent usage records for a user."""
        usage_path = os.path.join(self._ws_path(user_id), "usage", "usage.jsonl")
        if not os.path.isfile(usage_path):
            return []
        records = []
        with open(usage_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return records[-limit:]

    # ── Helpers ────────────────────────

    def _ws_path(self, student_id: str) -> str:
        return os.path.join(self._root, student_id)

    def get_root(self) -> str:
        return self._root
