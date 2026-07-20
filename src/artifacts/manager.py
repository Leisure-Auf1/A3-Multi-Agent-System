"""
Phase 9.0 — Artifact Manager

Unified artifact management for all generated content types:
  - MaterialArtifact (.md teaching materials)
  - PPTArtifact (.pptx presentations)
  - ImageArtifact (.svg images)
  - VideoArtifact (.md scripts, .srt subtitles, .json storyboards)

Unified interface:
  save() / load() / export() / list()

Architecture: does NOT modify Veritas-Core or src/core/
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.workspace.manager import WorkspaceManager


# ── Artifact Types ────────────────────────────

@dataclass
class MaterialArtifact:
    """Teaching material artifact."""
    artifact_id: str
    title: str
    content: str = ""                    # Markdown content
    format: str = "markdown"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "title": self.title,
            "format": self.format,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class PPTArtifact:
    """PPT presentation artifact."""
    artifact_id: str
    title: str
    file_path: str = ""                  # Path to .pptx file
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "title": self.title,
            "file_path": self.file_path,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class ImageArtifactRecord:
    """Image artifact record for storage."""
    artifact_id: str
    title: str
    file_path: str = ""                  # Path to .svg file
    data_uri: str = ""                   # Base64 data URI
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "title": self.title,
            "file_path": self.file_path,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class VideoArtifactRecord:
    """Video artifact record for storage."""
    artifact_id: str
    title: str
    markdown_path: str = ""              # Path to .md script
    srt_path: str = ""                   # Path to .srt subtitle
    json_path: str = ""                  # Path to .json storyboard
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "title": self.title,
            "markdown_path": self.markdown_path,
            "srt_path": self.srt_path,
            "json_path": self.json_path,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


# ── Artifact Manager ──────────────────────────

class ArtifactManager:
    """
    Unified artifact manager for all generated content.

    Persists artifacts to the user's workspace via WorkspaceManager.

    Usage:
        am = ArtifactManager(workspace_manager)
        am.save_material("student_001", material_artifact)
        artifacts = am.list_artifacts("student_001", "materials")
    """

    def __init__(self, workspace: Optional[WorkspaceManager] = None):
        self._workspace = workspace or WorkspaceManager()

    # ── Material ─────────────────────────

    def save_material(
        self,
        student_id: str,
        artifact: MaterialArtifact,
    ) -> str:
        """Save teaching material to workspace. Returns file path."""
        filename = f"{artifact.artifact_id}.md"
        content = f"# {artifact.title}\n\n{artifact.content}\n\n"
        content += f"*Generated: {artifact.created_at}*"
        return self._workspace.save_artifact(student_id, "materials", filename, content)

    def load_material(
        self,
        student_id: str,
        artifact_id: str,
    ) -> Optional[str]:
        """Load teaching material content."""
        return self._workspace.load_artifact(student_id, "materials", f"{artifact_id}.md")

    # ── PPT ──────────────────────────────

    def save_ppt(
        self,
        student_id: str,
        artifact: PPTArtifact,
    ) -> str:
        """Save PPT to workspace. Returns destination path."""
        # Copy the .pptx file to workspace
        filename = f"{artifact.artifact_id}.pptx"
        dest = os.path.join(
            self._workspace._ws_path(student_id), "artifacts", "ppt", filename
        )
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        if os.path.isfile(artifact.file_path):
            with open(artifact.file_path, "rb") as src:
                with open(dest, "wb") as dst:
                    dst.write(src.read())

        # Save metadata
        meta_filename = f"{artifact.artifact_id}.json"
        self._workspace.save_artifact(
            student_id, "ppt", meta_filename,
            json.dumps(artifact.to_dict(), ensure_ascii=False, indent=2),
        )
        return dest

    # ── Image ────────────────────────────

    def save_image(
        self,
        student_id: str,
        artifact: ImageArtifactRecord,
    ) -> str:
        """Save image SVG to workspace. Returns path."""
        # Save SVG content
        filename = f"{artifact.artifact_id}.svg"
        if os.path.isfile(artifact.file_path):
            with open(artifact.file_path, "r", encoding="utf-8") as src:
                svg_content = src.read()
            return self._workspace.save_artifact(
                student_id, "images", filename, svg_content
            )
        return ""

    # ── Video ────────────────────────────

    def save_video(
        self,
        student_id: str,
        artifact: VideoArtifactRecord,
    ) -> Dict[str, str]:
        """Save video script files to workspace. Returns path dict."""
        paths = {}

        # Copy scripts
        for key, src_path in [
            ("markdown", artifact.markdown_path),
            ("srt", artifact.srt_path),
            ("json", artifact.json_path),
        ]:
            if src_path and os.path.isfile(src_path):
                basename = os.path.basename(src_path)
                with open(src_path, "r", encoding="utf-8") as src:
                    content = src.read()
                paths[key] = self._workspace.save_artifact(
                    student_id, "videos", basename, content
                )

        return paths

    # ── List / Export ────────────────────

    def list_artifacts(
        self,
        student_id: str,
        category: str = "",
    ) -> List[str]:
        """List all artifacts for a student, optionally filtered by category."""
        return self._workspace.list_artifacts(student_id, category)

    def export_manifest(
        self,
        student_id: str,
    ) -> Dict[str, Any]:
        """
        Export a manifest of all artifacts for a student.

        Returns:
            {
                "student_id": str,
                "materials": int,
                "ppt": int,
                "images": int,
                "videos": int,
                "total": int,
            }
        """
        info = self._workspace.get_workspace_info(student_id)
        counts = info.artifact_counts
        return {
            "student_id": student_id,
            **counts,
            "total": sum(counts.values()),
        }

    def delete_artifact(
        self,
        student_id: str,
        category: str,
        filename: str,
    ) -> bool:
        """Delete a single artifact."""
        return self._workspace.delete_artifact(student_id, category, filename)
