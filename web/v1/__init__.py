"""V1 Dashboard — A3 个性化教学平台

Extracted from web/app.py (refactor — no behavior changes).

Architecture:
    pipeline.py   → Agent initialization + pipeline execution
    components.py → 5 panel Streamlit renderers
"""

from .pipeline import get_agents, run_pipeline
from .components import (
    render_profile_completeness,
    render_dynamic_profile,
    render_learning_path,
    render_resource_cards,
    render_agent_trace,
)

__all__ = [
    "get_agents",
    "run_pipeline",
    "render_profile_completeness",
    "render_dynamic_profile",
    "render_learning_path",
    "render_resource_cards",
    "render_agent_trace",
]
