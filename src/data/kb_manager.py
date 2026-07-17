"""
Phase 9.1 — Knowledge Base Manager

Loads and queries course knowledge bases.
"""
from __future__ import annotations

import json
import os
from typing import Optional, List, Dict, Any

KB_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "knowledge_base")


def list_courses() -> List[str]:
    """List available courses."""
    if not os.path.isdir(KB_ROOT):
        return []
    return sorted([
        d for d in os.listdir(KB_ROOT)
        if os.path.isdir(os.path.join(KB_ROOT, d))
    ])


def _load_json(course_name: str, filename: str) -> dict:
    """Load a JSON file from a course directory."""
    path = os.path.join(KB_ROOT, course_name, filename)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_course_meta(course_name: str) -> Dict[str, Any]:
    """Get course metadata (id, name, learning paths)."""
    data = _load_json(course_name, "resources.json")
    return {
        "course_id": data.get("course_id", ""),
        "course_name": data.get("course_name", course_name),
        "learning_paths": data.get("learning_paths", {}),
    }


def get_course_resources(course_name: str) -> Dict[str, Any]:
    """Get all resources for a course (lecture_notes, code_labs, etc.)."""
    data = _load_json(course_name, "resources.json")
    return data.get("resources", {})


def get_course_exercises(course_name: str) -> Dict[str, Any]:
    """Get all exercises for a course."""
    data = _load_json(course_name, "exercises.json")
    return data.get("exercises", {})


def search_courses(query: str) -> List[Dict[str, Any]]:
    """Simple case-insensitive search across course resources."""
    results = []
    q = query.lower()
    for course in list_courses():
        data = _load_json(course, "resources.json")
        resources = data.get("resources", {})
        # Search in lecture notes
        for category, items in resources.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = (item.get("title", "") or str(item.get("topic", "")) or "").lower()
                chapter = item.get("chapter", "")
                if q in title:
                    results.append({
                        "course": course,
                        "category": category,
                        "title": item.get("title") or item.get("topic", ""),
                        "chapter": chapter,
                    })

        # Search in course name
        course_name = data.get("course_name", "")
        if q in course_name.lower():
            results.append({
                "course": course,
                "category": "course",
                "title": course_name,
            })
    return results[:20]
