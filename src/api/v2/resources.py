"""
Phase 9.5 — Resource API (Gateway-enabled)

POST   /api/v2/resources/generate       — Gateway generation
POST   /api/v2/resources/generate/{type} — Single type
GET    /api/v2/resources/courses         — Course listing
GET    /api/v2/resources/search          — Search courses
GET    /api/v2/resources/{id}            — Get artifact status
GET    /api/v2/resources/student/{id}    — Student history
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json
from datetime import datetime, timezone

from src.auth.middleware import require_auth
from src.auth.models import AuthUser
from src.multimodal.gateway import MultimodalGateway, GenerateRequest
from src.multimodal.artifact import ResourceArtifact, ResourceType
from src.data.kb_manager import list_courses, get_course_meta, search_courses
from src.data.db import _get_conn

router = APIRouter(prefix="/api/v2/resources", tags=["resources"])


class GenerateBody(BaseModel):
    topic: str = Field(..., min_length=1)
    concepts: List[str] = Field(default_factory=list)
    resource_types: List[str] = Field(default=["document", "mindmap", "exercise"])
    student_level: str = "beginner"
    title: str = ""
    use_gateway: bool = True


class ArtifactResponse(BaseModel):
    id: str
    resource_type: str
    title: str
    topic: str
    status: str
    provider: str
    content_preview: str
    created_at: str
    completed_at: Optional[str] = None


def _save_artifact(artifact: ResourceArtifact, student_id: str):
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO resources (id, student_id, resource_type, title, topic, "
        "status, artifact_path, content_preview, provider, tokens_used, "
        "cost_usd, metadata_json, created_at, completed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (artifact.id, student_id, artifact.resource_type.value,
         artifact.title, artifact.topic, artifact.status.value,
         artifact.file_path, artifact.content[:500],
         artifact.provider, artifact.tokens_used, artifact.cost_usd,
         json.dumps(artifact.metadata, ensure_ascii=False),
         artifact.created_at, artifact.completed_at))
    conn.commit()


def _get_student_artifacts(student_id: str, limit: int = 50) -> List[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM resources WHERE student_id = ? "
        "ORDER BY created_at DESC LIMIT ?", (student_id, limit)).fetchall()
    return [dict(r) for r in rows]


# ── Static routes first (before parameterized) ────────────

@router.get("/courses")
def get_courses():
    courses = []
    for c in list_courses():
        meta = get_course_meta(c)
        courses.append({
            "id": c, "name": meta.get("course_name", c),
            "learning_paths": list(meta.get("learning_paths", {}).keys()),
        })
    return courses


@router.get("/search")
def search(q: str = ""):
    if not q:
        return []
    return search_courses(q)


# ── Generation routes ─────────────────────────────────────

@router.post("/generate")
def generate_resources_v2(
    req: GenerateBody,
    user: AuthUser = Depends(require_auth),
):
    gateway = MultimodalGateway()
    results = []
    for rtype in req.resource_types:
        try:
            valid = [e.value for e in ResourceType]
            if rtype not in valid:
                continue
            rt = ResourceType(rtype)
            artifact = gateway.generate(GenerateRequest(
                student_id=user.id, resource_type=rt,
                topic=req.topic, title=req.title or req.topic,
                concepts=req.concepts, student_level=req.student_level))
            _save_artifact(artifact, user.id)
            results.append(artifact.to_dict())
        except Exception:
            pass
    return {"topic": req.topic, "artifacts": results, "count": len(results)}


@router.post("/generate/{resource_type}")
def generate_single_v2(resource_type: str, req: GenerateBody,
                        user: AuthUser = Depends(require_auth)):
    valid = [e.value for e in ResourceType]
    if resource_type not in valid:
        raise HTTPException(400, f"Unknown type: {resource_type}. Valid: {valid}")
    gateway = MultimodalGateway()
    artifact = gateway.generate(GenerateRequest(
        student_id=user.id, resource_type=ResourceType(resource_type),
        topic=req.topic, title=req.title or req.topic,
        concepts=req.concepts, student_level=req.student_level))
    _save_artifact(artifact, user.id)
    return artifact.to_dict()


# ── Status / Query routes ─────────────────────────────────

@router.get("/student/{student_id}")
def get_student_resources(
    student_id: str,
    limit: int = 50,
    user: AuthUser = Depends(require_auth),
):
    """Get a student's learning resources. Own resources only."""
    if user.id != student_id:
        raise HTTPException(403, "Access denied")
    return _get_student_artifacts(student_id, limit)


@router.get("/{artifact_id}", response_model=ArtifactResponse)
def get_artifact_status(artifact_id: str):
    conn = _get_conn()
    row = conn.execute("SELECT * FROM resources WHERE id = ?",
                       (artifact_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Artifact not found")
    return ArtifactResponse(
        id=row["id"], resource_type=row["resource_type"],
        title=row["title"], topic=row["topic"],
        status=row["status"], provider=row["provider"],
        content_preview=row["content_preview"] or "",
        created_at=row["created_at"], completed_at=row["completed_at"])
