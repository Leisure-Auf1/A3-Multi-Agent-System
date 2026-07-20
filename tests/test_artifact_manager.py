"""
Phase 9.0 — Artifact Manager Tests

Covers:
- MaterialArtifact save/load
- PPTArtifact save
- ImageArtifactRecord save
- VideoArtifactRecord save
- ArtifactManager export_manifest
- ArtifactManager list/delete
- Edge cases: missing files, empty artifacts
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from workspace.manager import WorkspaceManager
from artifacts.manager import (
    ArtifactManager,
    MaterialArtifact,
    PPTArtifact,
    ImageArtifactRecord,
    VideoArtifactRecord,
)


# ──────────────────────────────────────────────
# 1. Material Artifact
# ──────────────────────────────────────────────

class TestMaterialArtifact:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="a3_test_am_")
        self.wm = WorkspaceManager(root=self.tmpdir)
        self.am = ArtifactManager(workspace=self.wm)

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_material(self):
        artifact = MaterialArtifact(
            artifact_id="mat_001",
            title="Python Basics",
            content="## Variables\n\nVariables store data.",
        )
        path = self.am.save_material("student_001", artifact)
        assert os.path.isfile(path)
        assert path.endswith("mat_001.md")

    def test_load_material(self):
        artifact = MaterialArtifact(
            artifact_id="mat_002",
            title="Advanced Python",
            content="## Decorators\n\n...",
        )
        self.am.save_material("student_001", artifact)
        content = self.am.load_material("student_001", "mat_002")
        assert content is not None
        assert "Advanced Python" in content
        assert "Decorators" in content

    def test_load_nonexistent_material(self):
        content = self.am.load_material("student_001", "nonexistent")
        assert content is None

    def test_material_to_dict(self):
        artifact = MaterialArtifact(
            artifact_id="mat_003",
            title="Test",
            content="content",
            metadata={"chapter_count": 3},
        )
        d = artifact.to_dict()
        assert d["artifact_id"] == "mat_003"
        assert d["metadata"]["chapter_count"] == 3


# ──────────────────────────────────────────────
# 2. PPT Artifact
# ──────────────────────────────────────────────

class TestPPTArtifact:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="a3_test_am_")
        self.wm = WorkspaceManager(root=self.tmpdir)
        self.am = ArtifactManager(workspace=self.wm)

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_ppt(self):
        # Create a mock pptx file
        src = os.path.join(self.tmpdir, "source.pptx")
        with open(src, "wb") as f:
            f.write(b"PPTX_MOCK_CONTENT" * 50)

        artifact = PPTArtifact(
            artifact_id="ppt_001",
            title="Python Slides",
            file_path=src,
        )
        dest = self.am.save_ppt("student_001", artifact)
        assert os.path.isfile(dest)

    def test_ppt_to_dict(self):
        artifact = PPTArtifact(
            artifact_id="ppt_002",
            title="Lesson Slides",
            file_path="/tmp/test.pptx",
        )
        d = artifact.to_dict()
        assert d["title"] == "Lesson Slides"


# ──────────────────────────────────────────────
# 3. Image Artifact
# ──────────────────────────────────────────────

class TestImageArtifact:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="a3_test_am_")
        self.wm = WorkspaceManager(root=self.tmpdir)
        self.am = ArtifactManager(workspace=self.wm)

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_image(self):
        # Create a mock SVG
        svg_path = os.path.join(self.tmpdir, "test.svg")
        with open(svg_path, "w") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg"><text>Test</text></svg>')

        artifact = ImageArtifactRecord(
            artifact_id="img_001",
            title="Concept Diagram",
            file_path=svg_path,
        )
        path = self.am.save_image("student_001", artifact)
        assert os.path.isfile(path)
        with open(path, "r") as f:
            content = f.read()
        assert "<svg" in content

    def test_save_image_missing_file(self):
        artifact = ImageArtifactRecord(
            artifact_id="img_002",
            title="Missing",
            file_path="/nonexistent/file.svg",
        )
        path = self.am.save_image("student_001", artifact)
        assert path == ""


# ──────────────────────────────────────────────
# 4. Video Artifact
# ──────────────────────────────────────────────

class TestVideoArtifact:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="a3_test_am_")
        self.wm = WorkspaceManager(root=self.tmpdir)
        self.am = ArtifactManager(workspace=self.wm)

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_video(self):
        # Create mock files
        md_path = os.path.join(self.tmpdir, "script.md")
        srt_path = os.path.join(self.tmpdir, "subtitle.srt")
        json_path = os.path.join(self.tmpdir, "storyboard.json")

        with open(md_path, "w") as f: f.write("# Script")
        with open(srt_path, "w") as f: f.write("1\n00:00:00,000 --> 00:00:10,000\nHello")
        with open(json_path, "w") as f: json.dump({"scenes": []}, f)

        artifact = VideoArtifactRecord(
            artifact_id="vid_001",
            title="Python Tutorial",
            markdown_path=md_path,
            srt_path=srt_path,
            json_path=json_path,
        )
        paths = self.am.save_video("student_001", artifact)
        assert "markdown" in paths
        assert "srt" in paths
        assert "json" in paths
        for p in paths.values():
            assert os.path.isfile(p)

    def test_save_video_missing_files(self):
        artifact = VideoArtifactRecord(
            artifact_id="vid_002",
            title="Empty",
        )
        paths = self.am.save_video("student_001", artifact)
        assert len(paths) == 0

    def test_video_to_dict(self):
        artifact = VideoArtifactRecord(
            artifact_id="vid_003",
            title="Tutorial",
            markdown_path="/tmp/script.md",
        )
        d = artifact.to_dict()
        assert d["title"] == "Tutorial"


# ──────────────────────────────────────────────
# 5. Export / List / Delete
# ──────────────────────────────────────────────

class TestExportListDelete:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="a3_test_am_")
        self.wm = WorkspaceManager(root=self.tmpdir)
        self.am = ArtifactManager(workspace=self.wm)

    def teardown_method(self):
        import shutil
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_export_manifest(self):
        self.am.save_material("student_001",
            MaterialArtifact(artifact_id="m1", title="T1", content="c"))
        self.am.save_material("student_001",
            MaterialArtifact(artifact_id="m2", title="T2", content="c"))
        manifest = self.am.export_manifest("student_001")
        assert manifest["student_id"] == "student_001"
        assert manifest["materials"] == 2
        assert "total" in manifest

    def test_export_manifest_empty(self):
        manifest = self.am.export_manifest("new_student")
        assert manifest["student_id"] == "new_student"
        assert manifest["total"] == 0

    def test_list_artifacts(self):
        self.am.save_material("student_001",
            MaterialArtifact(artifact_id="m1", title="T1", content="c"))
        artifacts = self.am.list_artifacts("student_001", "materials")
        assert len(artifacts) == 1
        assert "m1.md" in artifacts[0]

    def test_list_all_artifacts(self):
        self.am.save_material("student_001",
            MaterialArtifact(artifact_id="m1", title="T1", content="c"))
        artifacts = self.am.list_artifacts("student_001")
        assert len(artifacts) >= 1

    def test_delete_artifact(self):
        self.am.save_material("student_001",
            MaterialArtifact(artifact_id="to_del", title="T", content="c"))
        assert self.am.load_material("student_001", "to_del") is not None
        self.am.delete_artifact("student_001", "materials", "to_del.md")
        assert self.am.load_material("student_001", "to_del") is None

    def test_delete_nonexistent_artifact(self):
        result = self.am.delete_artifact("student_001", "materials", "missing.md")
        assert result is False


# ──────────────────────────────────────────────
# 6. Artifact Data Model Tests
# ──────────────────────────────────────────────

class TestArtifactDataModels:

    def test_material_defaults(self):
        a = MaterialArtifact(artifact_id="m1", title="T")
        assert a.format == "markdown"
        assert a.created_at != ""

    def test_ppt_defaults(self):
        a = PPTArtifact(artifact_id="p1", title="T")
        assert a.file_path == ""

    def test_image_defaults(self):
        a = ImageArtifactRecord(artifact_id="i1", title="T")
        assert a.file_path == ""

    def test_video_defaults(self):
        a = VideoArtifactRecord(artifact_id="v1", title="T")
        assert a.markdown_path == ""
        assert a.srt_path == ""
