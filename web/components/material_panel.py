"""
Phase 8.3-B1 — Material Panel (AI教材展示)

Renders ContentGeneratorAgent output (TeachingMaterial) in Streamlit:
  - Title & learning objectives
  - Chapter list with expandable sections
  - Concepts, explanations, examples, exercises per chapter
  - Markdown export/download button
  - Empty-state placeholder

Session state keys used:
  - _material_show_answers : list[int] — indices of exercises with answers revealed
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import streamlit as st

# ── Session state keys ───────────────

_MATERIAL_SHOW_ANSWERS = "_material_show_answers"


def _init_session() -> None:
    """Initialize material panel session state."""
    if _MATERIAL_SHOW_ANSWERS not in st.session_state:
        st.session_state[_MATERIAL_SHOW_ANSWERS] = set()


# ── Markdown exporter ────────────────


def _to_markdown(content: Dict[str, Any]) -> str:
    """Convert TeachingMaterial dict to Markdown string for download."""

    md = f"# {content.get('title', 'AI 教材')}\n\n"

    # Metadata
    md += f"> 画像: {content.get('target_profile', '')}\n"
    md += f"> 生成方式: {content.get('generation_source', 'rule')}\n"
    md += f"> 预计总时长: {content.get('total_estimated_minutes', 0)} 分钟\n\n"

    # Learning objectives
    objectives = content.get("learning_objectives", [])
    if objectives:
        md += "## 学习目标\n\n"
        for obj in objectives:
            md += f"- {obj}\n"
        md += "\n"

    # Chapters
    chapters = content.get("chapters", [])
    for ch in chapters:
        md += f"## {ch.get('title', '章节')}\n\n"

        # Explanation
        explanation = ch.get("explanation", "")
        if explanation:
            md += f"{explanation}\n\n"

        # Concepts
        concepts = ch.get("concepts", [])
        if concepts:
            md += "### 核心概念\n\n"
            for c in concepts:
                name = c.get("name", "")
                desc = c.get("description", "")
                diff = c.get("difficulty", "beginner")
                related = c.get("related", [])
                rel_text = f" (关联: {', '.join(related)})" if related else ""
                md += f"- **{name}** [{diff}]: {desc}{rel_text}\n"
            md += "\n"

        # Examples
        examples = ch.get("examples", [])
        if examples:
            md += "### 示例\n\n"
            for ex in examples:
                ex_title = ex.get("title", "示例")
                ex_code = ex.get("code", "")
                ex_expl = ex.get("explanation", "")
                ex_output = ex.get("expected_output", "")

                md += f"#### {ex_title}\n\n"
                if ex_code:
                    lang = "python" if "def " in ex_code or "import " in ex_code else ""
                    md += f"```{lang}\n{ex_code}\n```\n\n"
                if ex_expl:
                    md += f"{ex_expl}\n\n"
                if ex_output:
                    md += f"> 预期输出: {ex_output}\n\n"

        # Exercises
        exercises = ch.get("exercises", [])
        if exercises:
            md += "### 练习\n\n"
            for i, ex in enumerate(exercises):
                md += f"{i + 1}. **{ex.get('question', '')}**\n"
                md += f"   - 类型: {ex.get('type', 'open')}\n"
                if ex.get("hint"):
                    md += f"   - 提示: {ex.get('hint', '')}\n"
                if ex.get("answer"):
                    md += f"   - 答案: {ex.get('answer', '')}\n"
                md += "\n"

        # Summary
        summary = ch.get("summary", "")
        if summary:
            md += f"> 💡 {summary}\n\n"

        md += "---\n\n"

    # Overall summary
    overall = content.get("overall_summary", "")
    if overall:
        md += "## 总结\n\n"
        md += f"{overall}\n"

    return md


# ── CSS ──────────────────────────────


_MATERIAL_CSS = """
<style>
.material-container {
    border: 2px solid #E3F2FD;
    border-radius: 16px;
    padding: 24px;
    background: linear-gradient(135deg, #FAFAFA, #FFFFFF);
    margin: 12px 0;
}
.material-title {
    font-size: 1.8em;
    font-weight: 800;
    color: #1565C0;
    margin-bottom: 4px;
}
.material-meta {
    font-size: 0.85em;
    color: #78909C;
    margin-bottom: 16px;
}
.material-objective {
    padding: 6px 12px;
    background: #E3F2FD;
    border-radius: 8px;
    margin: 4px 0;
    font-size: 0.9em;
}
.chapter-card {
    border: 1px solid #E0E0E0;
    border-radius: 12px;
    padding: 16px;
    margin: 8px 0;
    background: #FFF;
    transition: box-shadow 0.15s;
}
.chapter-card:hover {
    box-shadow: 0 2px 12px rgba(33,150,243,0.1);
}
.concept-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 0.85em;
    margin: 2px 4px;
    font-weight: 600;
}
.concept-badge.beginner { background: #E8F5E9; color: #2E7D32; }
.concept-badge.intermediate { background: #FFF3E0; color: #EF6C00; }
.concept-badge.advanced { background: #FCE4EC; color: #C62828; }
.exercise-box {
    border-left: 3px solid #2196F3;
    padding: 12px 16px;
    margin: 8px 0;
    background: #F5F5F5;
    border-radius: 0 8px 8px 0;
}
.exercise-type {
    font-size: 0.75em;
    color: #78909C;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.answer-reveal {
    margin-top: 8px;
    padding: 8px 12px;
    background: #E8F5E9;
    border-radius: 6px;
    font-size: 0.9em;
    border-left: 3px solid #4CAF50;
}
</style>
"""

# ── Main renderer ─────────────────────


def render_material_panel(content: Optional[Dict[str, Any]]) -> None:
    """
    Render the AI teaching material panel.

    Args:
        content: TeachingMaterial.to_dict() from WorkflowResult.content,
                 or None if not available.
    """
    _init_session()

    st.markdown(_MATERIAL_CSS, unsafe_allow_html=True)

    if not content:
        _render_empty()
        return

    chapters = content.get("chapters", [])
    if not chapters:
        _render_empty()
        return

    # ── Header ──
    st.markdown("---")
    st.markdown(
        f'<div class="material-container">'
        f'<div class="material-title">📚 {content.get("title", "我的AI教材")}</div>'
        f'<div class="material-meta">'
        f'画像: {content.get("target_profile", "")} · '
        f'生成: {content.get("generation_source", "rule")} · '
        f'{content.get("total_estimated_minutes", 0)} 分钟 | '
        f'{len(chapters)} 章节'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Learning objectives ──
    objectives = content.get("learning_objectives", [])
    if objectives:
        st.markdown("##### 🎯 学习目标")
        for obj in objectives:
            st.markdown(
                f'<div class="material-objective">✅ {obj}</div>',
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Chapters ──
    for i, ch in enumerate(chapters):
        ch_id = ch.get("chapter_id", f"ch{i}")
        ch_title = ch.get("title", f"第{i + 1} 章")
        est = ch.get("estimated_minutes", 20)
        summary = ch.get("summary", "")

        with st.expander(f"📖 第{i + 1} 章: {ch_title} ({est}分钟)", expanded=(i == 0)):
            # Explanation
            explanation = ch.get("explanation", "")
            if explanation:
                st.markdown(explanation)

            # Concepts
            concepts = ch.get("concepts", [])
            if concepts:
                st.markdown("##### 🏷️ 核心概念")
                concept_html = ""
                for c in concepts:
                    name = c.get("name", "")
                    desc = c.get("description", "")[:80]
                    diff = c.get("difficulty", "beginner")
                    concept_html += (
                        f'<span class="concept-badge {diff}" '
                        f'title="{desc}">{name} [{diff}]</span> '
                    )
                st.markdown(concept_html, unsafe_allow_html=True)

            # Examples
            examples = ch.get("examples", [])
            if examples:
                st.markdown("##### 💡 示例")
                for ex in examples:
                    ex_title = ex.get("title", "示例")
                    ex_code = ex.get("code", "")
                    ex_expl = ex.get("explanation", "")
                    ex_output = ex.get("expected_output", "")

                    st.markdown(f"**{ex_title}**")
                    if ex_expl:
                        st.caption(ex_expl)
                    if ex_code:
                        st.code(ex_code, language="python")
                    if ex_output:
                        st.caption(f"预期输出: {ex_output}")

            # Exercises
            exercises = ch.get("exercises", [])
            if exercises:
                st.markdown("##### ✏️ 练习")
                for j, ex in enumerate(exercises):
                    q = ex.get("question", "")
                    q_type = ex.get("type", "open")
                    hint = ex.get("hint", "")
                    answer = ex.get("answer", "")

                    type_labels = {
                        "open": "开放题",
                        "multiple_choice": "选择题",
                        "fill_blank": "填空题",
                        "coding": "编程题",
                    }
                    type_label = type_labels.get(q_type, q_type)

                    st.markdown(
                        f'<div class="exercise-box">'
                        f'<div class="exercise-type">{type_label}</div>'
                        f'<div>{q}</div>',
                        unsafe_allow_html=True,
                    )

                    if hint:
                        with st.expander("💡 提示"):
                            st.info(hint)

                    ans_key = f"answer_{ch_id}_{j}"
                    if st.button(f"🔍 查看答案 #{j + 1}", key=ans_key):
                        st.markdown(
                            f'<div class="answer-reveal">✅ {answer}</div>',
                            unsafe_allow_html=True,
                        )

                    st.markdown("</div>", unsafe_allow_html=True)

            # Chapter summary
            if summary:
                st.info(f"💡 {summary}")

    # ── Overall summary ──
    overall = content.get("overall_summary", "")
    if overall:
        st.markdown("---")
        st.markdown("#### 📝 总结")
        st.markdown(overall)

    # ── Export button ──
    md_text = _to_markdown(content)
    # Sanitize filename
    title_raw = content.get("title", "AI教材")
    filename = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff\-_]", "_", title_raw)[:40]

    st.download_button(
        label="📥 下载教材 (Markdown)",
        data=md_text,
        file_name=f"{filename}.md",
        mime="text/markdown",
        use_container_width=True,
        key="download_material_md",
    )


def _render_empty() -> None:
    """Render empty state when no content is available."""
    st.info(
        "📚 暂无AI教材内容。\n\n"
        "请在 **学习助手** 页面输入学习目标并点击 **「开始分析」**，\n"
        "AI 将为你生成个性化教材。"
    )


def get_material_markdown(content: Optional[Dict[str, Any]]) -> str:
    """
    Get the Markdown representation of the material (for testing/programmatic use).

    Args:
        content: TeachingMaterial.to_dict() or None

    Returns:
        Markdown string or empty string
    """
    if not content:
        return ""
    return _to_markdown(content)
