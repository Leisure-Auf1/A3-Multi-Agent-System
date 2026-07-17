"""Phase 9.4 — v2 API Package"""
from .chat import router as chat_router
from .profile import router as profile_router
from .learning import router as learning_v2_router
from .resources import router as resources_router
from .evaluation import router as evaluation_router

__all__ = [
    "chat_router", "profile_router", "learning_v2_router",
    "resources_router", "evaluation_router",
]
