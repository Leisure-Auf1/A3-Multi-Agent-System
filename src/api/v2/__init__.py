"""Phase 9.4 — v2 API Package"""
from .chat import router as chat_router
from .profile import router as profile_router
from .learning import router as learning_v2_router
from .resources import router as resources_router
from .evaluation import router as evaluation_router

# Phase 4.0 — User LLM settings
from .settings import router as settings_router

# Phase 9.5-B — Multi-User Platform
from .users import router as users_router

# Phase 10.2 — Unified Learning Pipeline
from .pipeline import router as pipeline_router

__all__ = [
    "chat_router", "profile_router", "learning_v2_router",
    "resources_router", "evaluation_router", "settings_router",
    "users_router", "pipeline_router",
]
