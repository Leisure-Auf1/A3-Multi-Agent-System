"""Phase 4.2.5 — API Routes package"""
from .learning import router as learning_router
from .runtime import router as runtime_router  # Phase 5.0
from .auth import router as auth_router  # Phase 9.1

__all__ = ["learning_router", "runtime_router", "auth_router"]
