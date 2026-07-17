"""
Phase 9.4 — Resource API

POST   /api/v2/resources/generate
POST   /api/v2/resources/generate/{type}
GET    /api/v2/resources/courses
GET    /api/v2/resources/search
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from src.auth.middleware import require_auth
from src.auth.models import AuthUser
from src.agents.resource_generation_agent import ResourceGenerationAgent
from src.data.kb_manager import (
    list_courses, get_course_meta, get_course_resources,
    get_course_exercises, search_courses,
)

router = APIRouter(prefix="/api/v2/resources", tags=["resources"])


class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    concepts: List[str] = Field(default_factory=list)
    resource_types: List[str] = Field(default=["document", "mindmap", "exercise"])
    student_level: str = "beginner"
    title: str = ""


class ResourceResponse(BaseModel):
    resource_type: str
    title: str
    data: Dict[str, Any] = Field(default_factory=dict)
    markdown: str = ""
    summary: str = ""


_RESOURCE_TYPES = {
    "document": "generate_course_notes",
    "mindmap": "generate_mind_map",
    "exercise": "generate_exercises",
    "code": "generate_code_lab",
    "video": "generate_video_script",
    "reading": "generate_extended_reading",
}


@router.post("/generate", response_model=List[ResourceResponse])
def generate_resources(
    req: GenerateRequest,
    user: AuthUser = Depends(require_auth),
):
    """Generate learning resources for a topic."""
    agent = ResourceGenerationAgent()
    results = []
    title = req.title or req.topic

    for rtype in req.resource_types:
        method_name = _RESOURCE_TYPES.get(rtype)
        if method_name is None:
            continue
        try:
            method = getattr(agent, method_name)
            resource = method(
                title=title,
                topic=req.topic,
                concepts=req.concepts,
            )
            results.append(ResourceResponse(
                resource_type=rtype,
                title=title,
                data=resource if isinstance(resource, dict) else {},
                markdown=resource.to_markdown() if hasattr(resource, 'to_markdown') else str(resource),
                summary=getattr(resource, 'summary', '') or str(resource)[:200],
            ))
        except Exception:
            pass  # Skip failed resource types

    return results


@router.post("/generate/{resource_type}", response_model=ResourceResponse)
def generate_single_resource(
    resource_type: str,
    req: GenerateRequest,
    user: AuthUser = Depends(require_auth),
):
    """Generate a single resource type."""
    method_name = _RESOURCE_TYPES.get(resource_type)
    if method_name is None:
        raise HTTPException(400, f"Unknown resource type: {resource_type}")

    agent = ResourceGenerationAgent()
    title = req.title or req.topic
    method = getattr(agent, method_name)
    resource = method(title=title, topic=req.topic, concepts=req.concepts)

    return ResourceResponse(
        resource_type=resource_type,
        title=title,
        data=resource if isinstance(resource, dict) else {},
        markdown=resource.to_markdown() if hasattr(resource, 'to_markdown') else str(resource),
        summary=getattr(resource, 'summary', '') or str(resource)[:200],
    )


@router.get("/courses", response_model=List[Dict[str, Any]])
def get_courses():
    """List available courses."""
    courses = []
    for c in list_courses():
        meta = get_course_meta(c)
        courses.append({
            "id": c,
            "name": meta.get("course_name", c),
            "learning_paths": list(meta.get("learning_paths", {}).keys()),
        })
    return courses


@router.get("/search")
def search_resources(q: str = ""):
    """Search across course resources."""
    if not q:
        return []
    return search_courses(q)
