"""
Phase 9.0 — Artifacts Package
"""

from .manager import (
    ArtifactManager,
    MaterialArtifact, PPTArtifact,
    ImageArtifactRecord, VideoArtifactRecord,
)

__all__ = [
    "ArtifactManager",
    "MaterialArtifact", "PPTArtifact",
    "ImageArtifactRecord", "VideoArtifactRecord",
]
