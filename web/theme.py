"""
A3 Theme System — Phase 10.4-D

Provides consistent visual styling for Streamlit UI.
Desktop-optimized with responsive widths.
"""

from __future__ import annotations


# ═══════════════════════════════════════════════
# Color Palette
# ═══════════════════════════════════════════════

COLORS = {
    "primary": "#58a6ff",
    "success": "#3fb950",
    "warning": "#d29922",
    "error": "#f85149",
    "info": "#79c0ff",
    "bg_dark": "#0d1117",
    "bg_card": "#161b22",
    "bg_input": "#0d1117",
    "border": "#30363d",
    "border_hover": "#58a6ff",
    "text_primary": "#c9d1d9",
    "text_secondary": "#8b949e",
    "text_dim": "#484f58",
    "agent_done": "#3fb950",
    "agent_running": "#58a6ff",
    "agent_waiting": "#484f58",
    "agent_error": "#f85149",
}


# ═══════════════════════════════════════════════
# CSS Theme (built with string replace to avoid format collisions)
# ═══════════════════════════════════════════════

def get_theme_css() -> str:
    """Return the full theme CSS with colors injected."""
    css = """<style>
    .stApp { background: $bg_dark; }
    .stMetric { background: $bg_card; border-radius: 8px; padding: 12px; border: 1px solid $border; }
    .stMetric label { color: $text_secondary !important; font-size: 0.8rem; }
    .stMetric div[data-testid="stMetricValue"] { color: $primary; font-size: 1.4rem; }
    .stButton > button { border-radius: 8px; font-weight: 500; transition: all 0.2s; }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(88,166,255,0.3); }
    .stTextArea textarea { border-radius: 8px; border: 1px solid $border; background: $bg_input; color: $text_primary; }
    .stExpander { border: 1px solid $border; border-radius: 8px; }
    .stProgress > div > div { background: linear-gradient(90deg, $primary, $success); }
    .card { background: $bg_card; border: 1px solid $border; border-radius: 12px; padding: 20px; margin: 8px 0; }
    .card:hover { border-color: $border_hover; }
    [data-testid="stSidebar"] { background: $bg_card; }
    @media (min-width: 1200px) { .block-container { max-width: 1200px; padding: 2rem 3rem; } }
</style>"""
    for key, val in COLORS.items():
        css = css.replace(f"${key}", val)
    return css


def get_color(name: str, default: str = "#ffffff") -> str:
    return COLORS.get(name, default)


def agent_status_icon(status: str) -> str:
    return {"success": "✅", "running": "🔄", "waiting": "⏳", "error": "❌"}.get(status, "❓")


def card_html(title: str, content: str, icon: str = "") -> str:
    color = COLORS["text_secondary"]
    return f'<div class="card"><div style="font-size:1.5em">{icon}</div><div style="font-weight:bold">{title}</div><div style="color:{color};font-size:0.9em">{content}</div></div>'


__all__ = ["COLORS", "get_theme_css", "get_color", "agent_status_icon", "card_html"]
