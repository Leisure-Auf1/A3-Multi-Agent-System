"""
Phase 9.4 — Streaming Chat API

SSE streaming endpoint for TutorAgent.
POST /api/v2/chat/stream
POST /api/v2/chat/message
GET  /api/v2/chat/threads
POST /api/v2/chat/threads
GET  /api/v2/chat/threads/{id}/messages
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json
import uuid

from src.auth.middleware import require_auth, optional_auth
from src.auth.models import AuthUser
from src.agents.tutor_agent import TutorAgent, TutorContext, TutorResponse
from src.api.dependencies import get_llm_provider
from src.data.thread_store import (
    new_thread, list_threads, add_message, get_messages, rename_thread,
    get_thread_by_id,
)
from src.data.learning_records import record_agent_action
from src.tools import ToolRegistry, WebSearchTool

router = APIRouter(prefix="/api/v2/chat", tags=["chat"])


# ── Schemas ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    thread_id: Optional[str] = None
    topic: str = ""
    learning_goal: str = ""
    student_profile: Dict[str, Any] = Field(default_factory=dict)
    knowledge_gaps: List[str] = Field(default_factory=list)


class ThreadCreate(BaseModel):
    title: str = "New Chat"


class ThreadRename(BaseModel):
    title: str


class MessageResponse(BaseModel):
    id: str
    thread_id: str
    role: str
    content: str
    created_at: str


class ThreadResponse(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str


# ── Helpers ────────────────────────────────────────────────

_tutor_cache: Dict[str, TutorAgent] = {}
_tool_registry: Optional[ToolRegistry] = None


def _get_tool_registry() -> ToolRegistry:
    """Get or create the shared tool registry."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
        _tool_registry.register(WebSearchTool())
    return _tool_registry


def _get_tutor(provider=None) -> TutorAgent:
    """Get or create a tutor agent instance with optional LLM provider and tools."""
    key = "llm" if provider is not None else "default"
    if key not in _tutor_cache:
        registry = _get_tool_registry() if provider is not None else None
        _tutor_cache[key] = TutorAgent(llm_provider=provider, tool_registry=registry)
    return _tutor_cache[key]


# ── Routes ─────────────────────────────────────────────────

@router.post("/message", response_model=Dict[str, Any])
def chat_message(
    req: ChatRequest,
    user: AuthUser = Depends(require_auth),
):
    """Non-streaming chat message. Returns full response."""
    import time
    start = time.time()

    tutor = _get_tutor(provider=get_llm_provider())
    ctx = TutorContext(
        student_profile=req.student_profile,
        learning_goal=req.learning_goal,
        current_topic=req.topic,
        knowledge_gaps=req.knowledge_gaps,
    )

    resp = tutor.explain(req.message, ctx)

    # Create thread if needed
    thread_id = req.thread_id
    if not thread_id:
        t = new_thread(user.id, req.message[:50])
        thread_id = t["id"]

    # Save messages
    add_message(thread_id, "user", req.message)
    add_message(thread_id, "assistant", resp.content)

    # Record learning event
    record_agent_action(
        user_id=user.id,
        agent="tutor",
        action="chat",
        course_id=req.topic,
        duration_ms=int((time.time() - start) * 1000),
    )

    return {
        "thread_id": thread_id,
        "content": resp.content,
        "follow_up_questions": resp.follow_up_questions,
        "teaching_style": resp.teaching_style,
        "tool_calls_made": resp.tool_calls_made,
    }


@router.post("/stream")
def chat_stream(
    req: ChatRequest,
    user: AuthUser = Depends(require_auth),
):
    """Streaming SSE chat endpoint. Yields tokens as they arrive."""

    def generate():
        tutor = _get_tutor(provider=get_llm_provider())
        ctx = TutorContext(
            student_profile=req.student_profile,
            learning_goal=req.learning_goal,
            current_topic=req.topic,
            knowledge_gaps=req.knowledge_gaps,
        )

        thread_id = req.thread_id
        if not thread_id:
            t = new_thread(user.id, req.message[:50])
            thread_id = t["id"]

        # Save user message
        add_message(thread_id, "user", req.message)

        full_response = []
        try:
            for chunk in tutor.explain_stream(req.message, ctx):
                full_response.append(chunk)
                yield f"data: {json.dumps({'token': chunk, 'thread_id': thread_id})}\n\n"

            # Save assistant message
            add_message(thread_id, "assistant", "".join(full_response))

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/threads", response_model=List[ThreadResponse])
def get_threads(user: AuthUser = Depends(require_auth)):
    """List user's chat threads."""
    return list_threads(user.id)


@router.post("/threads", response_model=ThreadResponse, status_code=201)
def create_thread(req: ThreadCreate, user: AuthUser = Depends(require_auth)):
    """Create a new chat thread."""
    return new_thread(user.id, req.title)


@router.patch("/threads/{thread_id}")
def rename_thread_endpoint(
    thread_id: str, req: ThreadRename,
    user: AuthUser = Depends(require_auth),
):
    """Rename a chat thread."""
    try:
        rename_thread(thread_id, user.id, req.title)
    except PermissionError:
        raise HTTPException(404, "Thread not found")
    return {"success": True}


@router.get("/threads/{thread_id}/messages", response_model=List[MessageResponse])
def get_thread_messages_endpoint(
    thread_id: str,
    user: AuthUser = Depends(require_auth),
):
    """Get messages in a thread. Ownership-isolated via user_id + thread_id gate."""
    messages = get_messages(thread_id, user.id)
    if not messages and get_thread_by_id(thread_id, user.id) is None:
        raise HTTPException(404, "Thread not found")
    return messages
