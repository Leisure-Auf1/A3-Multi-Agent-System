"""Dashboard V2 — 比赛展示版 Demo

6-panel dashboard for visualizing the A3 multi-agent system.

Architecture:
    data_providers.py  → Data access & transformation (queries src/)
    components.py      → Pure Streamlit rendering (6 panel functions)

Usage:
    from web.dashboard import (
        data_providers, components,
        get_system_overview, get_student_intelligence,
        get_execution_timeline, get_explainability_data,
        get_evaluation_data, get_improvement_timeline,
        get_demo_all,
        render_system_overview, render_student_intelligence,
        render_execution_timeline, render_explainability_panel,
        render_evaluation_dashboard, render_improvement_timeline,
    )
"""

from .data_providers import (
    get_system_overview,
    get_student_intelligence,
    get_execution_timeline,
    get_explainability_data,
    get_evaluation_data,
    get_improvement_timeline,
    get_trust_safety_data,
    get_demo_all,
)

from .components import (
    render_system_overview,
    render_student_intelligence,
    render_execution_timeline,
    render_explainability_panel,
    render_evaluation_dashboard,
    render_improvement_timeline,
    render_trust_safety_panel,
)

__all__ = [
    # Data providers
    "get_system_overview",
    "get_student_intelligence",
    "get_execution_timeline",
    "get_explainability_data",
    "get_evaluation_data",
    "get_improvement_timeline",
    "get_trust_safety_data",
    "get_demo_all",
    # Rendering components
    "render_system_overview",
    "render_student_intelligence",
    "render_execution_timeline",
    "render_explainability_panel",
    "render_evaluation_dashboard",
    "render_improvement_timeline",
    "render_trust_safety_panel",
]
