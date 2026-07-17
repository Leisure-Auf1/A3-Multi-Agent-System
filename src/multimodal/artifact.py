"""
Phase 9.5 — Resource Artifact

Immutable resource artifact with state machine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid
import json


class ArtifactStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    VALIDATING = "validating"
    ACTIVE = "active"
    FAILED = "failed"


class ResourceType(str, Enum):
    DOCUMENT = "document"          # Markdown course notes
    MINDMAP = "mindmap"            # Mermaid JSON
    EXERCISE = "exercise"          # Quiz/exercise JSON
    CODE_LAB = "code_lab"          # Python code experiment
    SLIDES = "slides"              # PPT slides
    ILLUSTRATION = "illustration"  # Concept image
    VIDEO_SCRIPT = "video_script"  # Video narration script


@dataclass
class ResourceArtifact:
    """Immutable resource artifact with full lifecycle tracking."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    student_id: str = ""
    resource_type: ResourceType = ResourceType.DOCUMENT
    title: str = ""
    topic: str = ""
    content: str = ""                    # Main content (Markdown/JSON/Base64)
    content_format: str = "markdown"     # markdown | json | base64 | python
    provider: str = "rule"               # Which provider generated this
    status: ArtifactStatus = ArtifactStatus.PENDING
    file_path: str = ""                  # Path to generated file (.pptx, .py, etc.)
    media_urls: List[str] = field(default_factory=list)
    tokens_used: int = 0
    cost_usd: float = 0.0
    validation_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "resource_type": self.resource_type.value,
            "title": self.title,
            "topic": self.topic,
            "content": self.content[:500] + "..." if len(self.content) > 500 else self.content,
            "content_format": self.content_format,
            "provider": self.provider,
            "status": self.status.value,
            "file_path": self.file_path,
            "media_urls": self.media_urls,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "validation_errors": self.validation_errors,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def mark_active(self):
        self.status = ArtifactStatus.ACTIVE
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def mark_failed(self, error: str = ""):
        self.status = ArtifactStatus.FAILED
        if error:
            self.validation_errors.append(error)
        self.completed_at = datetime.now(timezone.utc).isoformat()


# ── Status transition map ────────────────────────────────

VALID_TRANSITIONS = {
    ArtifactStatus.PENDING:    [ArtifactStatus.GENERATING, ArtifactStatus.FAILED],
    ArtifactStatus.GENERATING: [ArtifactStatus.VALIDATING, ArtifactStatus.FAILED],
    ArtifactStatus.VALIDATING: [ArtifactStatus.ACTIVE, ArtifactStatus.FAILED],
    ArtifactStatus.ACTIVE:     [],       # Terminal
    ArtifactStatus.FAILED:     [ArtifactStatus.PENDING],  # Retry
}


def can_transition(from_status: ArtifactStatus, to_status: ArtifactStatus) -> bool:
    return to_status in VALID_TRANSITIONS.get(from_status, [])
