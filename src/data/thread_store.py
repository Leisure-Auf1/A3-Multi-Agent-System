"""
Phase 9.1 — Thread Store

High-level API over the db.py chat_threads and chat_messages tables.
"""
from __future__ import annotations

import uuid
import json
from typing import Optional, List, Dict, Any

from .db import (
    ChatThread, ChatMessage,
    create_thread, get_user_threads, update_thread_title,
    create_message, get_thread_messages,
)


def new_thread(user_id: str, title: str = "New Chat") -> Dict[str, Any]:
    """Create a new chat thread."""
    thread = create_thread(uuid.uuid4().hex[:16], user_id, title)
    return thread.to_dict()


def list_threads(user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    """List user's threads, newest first."""
    return get_user_threads(user_id, limit)


def rename_thread(thread_id: str, title: str):
    """Rename a chat thread."""
    update_thread_title(thread_id, title)


def add_message(thread_id: str, role: str, content: str,
                metadata: Optional[dict] = None) -> Dict[str, Any]:
    """Add a message to a thread."""
    msg = ChatMessage(
        id=uuid.uuid4().hex[:16],
        thread_id=thread_id,
        role=role,
        content=content,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )
    saved = create_message(msg)
    return saved.to_dict()


def get_messages(thread_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get messages in a thread, oldest first."""
    return get_thread_messages(thread_id, limit)
