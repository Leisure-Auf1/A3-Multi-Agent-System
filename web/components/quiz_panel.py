"""
Phase 8.2-B2 — Interactive Quiz Panel
Phase 8.2-C — Wrong Answer Error Analysis

Renders a quiz after pipeline completion:
  1. Generate quiz questions via EvaluationAgent
  2. Render questions with answer options
  3. Collect user answers -> score via EvaluationAgent
  4. For wrong answers: LLM-powered error analysis (Phase 8.2-C)
  5. Display score, weak_areas, strong_areas, per-question AI analysis
  6. Write error analyses to StudentMemory (weak_point + feedback + mastery)
  7. Inject results into workflow evaluation for mastery updates (Phase 8.2-B1)

Questions and correct answers are stored in session_state -- never sent to client.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import streamlit as st

from src.agents.evaluation_agent import (
    EvaluationAgent,
    QuizQuestion,
    StudentAnswer,
    QuizResult,
    ErrorAnalysis,
)


# Session state keys

_QUIZ_QUESTIONS = "quiz_questions"         # List[QuizQuestion]
_QUIZ_RESULT = "quiz_result"               # QuizResult | None
_QUIZ_EVAL_DICT = "quiz_evaluation_dict"   # dict with weak_areas/strong_areas
_QUIZ_SUBMITTED = "quiz_submitted"         # bool
_ERROR_ANALYSES = "quiz_error_analyses"     # Dict[str, ErrorAnalysis] per wrong question


def _init_session() -> None:
    """Initialize quiz session state keys if not present."""
    for key, default in [
        (_QUIZ_QUESTIONS, None),
        (_QUIZ_RESULT, None),
        (_QUIZ_EVAL_DICT, None),
        (_QUIZ_SUBMITTED, False),
        (_ERROR_ANALYSES, None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default


def render_quiz_panel(provider: Any, topic: str = "") -> Optional[Dict[str, Any]]:
    """
    Render the interactive quiz panel.

    Args:
        provider: LLM provider instance (e.g., DeepSeekProvider).
                  Pass None to skip quiz entirely.
        topic: The learning goal/topic for quiz generation.

    Returns:
        Evaluation dict with weak_areas/strong_areas if quiz completed,
        None otherwise (for injection into workflow result).
    """
    _init_session()

    if provider is None:
        st.caption("Connect LLM provider to enable smart quizzes")
        return None

    agent = EvaluationAgent(llm_provider=provider)

    # Already submitted -> show results
    if st.session_state[_QUIZ_SUBMITTED] and st.session_state[_QUIZ_RESULT] is not None:
        _render_results(agent)
        return st.session_state[_QUIZ_EVAL_DICT]

    # Generate quiz (first time)
    if st.session_state[_QUIZ_QUESTIONS] is None:
        if st.button("Verify Learning", type="primary", use_container_width=True):
            with st.spinner("Generating personalized quiz..."):
                questions = agent.generate_quiz(
                    topic=topic,
                    student_level="beginner",
                    num_questions=3,
                    difficulty="auto",
                )
                if questions:
                    st.session_state[_QUIZ_QUESTIONS] = questions
                    st.rerun()
                else:
                    st.warning("Could not generate quiz questions, please try later")
        return None

    # Render quiz questions
    questions: List[QuizQuestion] = st.session_state[_QUIZ_QUESTIONS]

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
    st.markdown("### Verify Learning")
    st.caption(f"{len(questions)} questions - dynamically generated from your learning content")

    # Collect answers
    answers: List[StudentAnswer] = []
    question_texts: Dict[str, str] = {}  # qid -> question text
    correct_answers: Dict[str, str] = {}  # qid -> correct answer text

    for q in questions:
        key = f"quiz_answer_{q.id}"
        if key not in st.session_state:
            st.session_state[key] = 0  # default: first option

        selected = st.radio(
            f"**{q.id}.** {q.question}",
            options=list(range(len(q.options))),
            format_func=lambda i, opts=q.options: f"{chr(65+i)}) {opts[i]}",
            key=key,
        )
        question_texts[q.id] = q.question
        correct_answers[q.id] = q.options[q.correct_index] if q.correct_index < len(q.options) else ""
        answers.append(StudentAnswer(
            question_id=q.id,
            selected_index=selected,
            text_answer=q.options[selected] if selected < len(q.options) else "",
        ))

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)

    # Submit button
    if st.button("Submit Answers", type="primary", use_container_width=True):
        with st.spinner("Grading..."):
            result: QuizResult = agent.score_quiz(questions, answers)

            # Phase 8.2-C: Error analysis for wrong answers
            error_analyses: Dict[str, Dict[str, Any]] = {}
            if provider is not None:
                for q in questions:
                    ans = next((a for a in answers if a.question_id == q.id), None)
                    if ans is None or ans.is_correct:
                        continue  # skip correct answers

                    try:
                        analysis: ErrorAnalysis = agent.analyze_wrong_answer(
                            question=question_texts.get(q.id, ""),
                            student_answer=ans.text_answer,
                            correct_answer=correct_answers.get(q.id, ""),
                            question_id=q.id,
                        )
                        error_analyses[q.id] = analysis.to_dict()
                    except Exception:
                        pass  # don't block scoring on analysis failure

                result.error_analyses = error_analyses

            # Build evaluation dict for Phase 8.2-B1 mastery updates
            eval_dict = {
                "score": result.score_percent,
                "weak_areas": result.weak_areas,
                "strong_areas": result.strong_areas,
                "recommendations": result.recommendations,
                "error_analyses": error_analyses,
                "passed": result.score_percent >= 70,
            }

            st.session_state[_QUIZ_RESULT] = result
            st.session_state[_QUIZ_EVAL_DICT] = eval_dict
            st.session_state[_ERROR_ANALYSES] = error_analyses
            st.session_state[_QUIZ_SUBMITTED] = True
            st.rerun()

    return None


def _render_results(agent: EvaluationAgent = None) -> None:
    """Display quiz results with per-question error analysis."""
    result: QuizResult = st.session_state[_QUIZ_RESULT]
    error_analyses: dict = st.session_state.get(_ERROR_ANALYSES) or result.error_analyses
    if result is None:
        return

    st.markdown('<div class="divider-custom"></div>', unsafe_allow_html=True)
    st.markdown("### Quiz Results")

    # Score card
    score = result.score_percent
    emoji = "PASS" if score >= 80 else ("OK" if score >= 60 else "STUDY")
    st.metric(
        f"{emoji} Score",
        f"{score:.0f}%",
        f"{result.correct_count}/{result.total_questions} correct",
    )

    # Weak / Strong areas
    col1, col2 = st.columns(2)
    with col1:
        if result.weak_areas:
            st.error("**Weak Areas**")
            for area in result.weak_areas:
                st.write(f"- {area}")
        else:
            st.success("**No Weak Areas**")

    with col2:
        if result.strong_areas:
            st.success("**Mastered**")
            for area in result.strong_areas:
                st.write(f"- {area}")

    # Phase 8.2-C: Per-question error analysis
    questions: list = st.session_state[_QUIZ_QUESTIONS] or []
    q_map = {q.id: q for q in questions}

    for ans in result.answers:
        if ans.is_correct:
            continue
        qid = ans.question_id
        q = q_map.get(qid)
        if q is None:
            continue

        selected_text = q.options[ans.selected_index] if ans.selected_index < len(q.options) else "(none)"
        correct_text = q.options[q.correct_index] if q.correct_index < len(q.options) else ""

        # Per-question error card
        with st.expander(f"WRONG {qid}. {q.question[:60]}..."):
            st.markdown(f"**Your Answer:** {selected_text}")
            st.markdown(f"**Correct Answer:** {correct_text}")

            # AI Analysis
            analysis = error_analyses.get(qid, {})
            if analysis:
                st.markdown("---")
                st.markdown("#### AI Analysis")

                error_type = analysis.get("error_type", "unknown")
                error_labels = {
                    "concept_misunderstanding": "Concept Misunderstanding",
                    "syntax": "Syntax Error",
                    "logic": "Logic Error",
                    "incomplete": "Incomplete Answer",
                    "unknown": "Unknown Error",
                }
                st.caption(f"Error Type: {error_labels.get(error_type, error_type)}")

                # Why wrong
                explanation = analysis.get("explanation", "")
                if explanation:
                    st.info(f"**Why it was wrong:**\n\n{explanation}")

                # Correct reasoning
                correct_reasoning = analysis.get("correct_reasoning", "")
                if correct_reasoning:
                    st.success(f"**Correct Reasoning:**\n\n{correct_reasoning}")

                # Related concepts (knowledge gaps)
                related = analysis.get("related_concepts", [])
                if related:
                    st.markdown("**Knowledge Gaps:**")
                    for rc in related:
                        st.markdown(f"- {rc}")

                # Recovery plan
                recovery = analysis.get("recovery_plan", "")
                if recovery:
                    st.warning(f"**Recovery Plan:**\n\n{recovery}")

                # Next exercise
                next_ex = analysis.get("next_exercise", "")
                if next_ex:
                    st.info(f"**Recommended Exercise:**\n\n{next_ex}")

                # Generation source
                source = analysis.get("generation_source", "rule")
                if source == "llm":
                    st.caption("AI-generated analysis")
                else:
                    st.caption("Rule-based analysis")

            # Original question explanation
            if q.explanation:
                with st.expander("Question Explanation"):
                    st.write(q.explanation)

    # Summary of errors analyzed
    if error_analyses:
        llm_count = sum(1 for a in error_analyses.values() if a.get("generation_source") == "llm")
        st.caption(f"{len(error_analyses)} wrong answers analyzed ({llm_count} AI-analyzed)")

    # Recommendations
    if result.recommendations:
        with st.expander("Study Recommendations"):
            for rec in result.recommendations:
                st.write(f"- {rec}")

    # Phase 8.2-C: Write to StudentMemory
    _write_error_to_memory(result, error_analyses)

    # Reset button
    if st.button("Retake Quiz", use_container_width=True):
        st.session_state[_QUIZ_QUESTIONS] = None
        st.session_state[_QUIZ_RESULT] = None
        st.session_state[_QUIZ_EVAL_DICT] = None
        st.session_state[_ERROR_ANALYSES] = None
        st.session_state[_QUIZ_SUBMITTED] = False
        st.rerun()


def _write_error_to_memory(result: QuizResult, error_analyses: dict) -> None:
    """
    Write wrong-answer analyses to StudentMemory.

    For each wrong answer, writes:
      - weak_point: the specific concept/error analysis
      - feedback: contextual feedback about this quiz session
    """
    if not error_analyses:
        return

    try:
        from veritas.memory import MemoryManager
        mm = MemoryManager()
    except Exception:
        return  # Memory unavailable

    student_id = f"quiz_{result.quiz_id or 'unknown'}"

    for qid, analysis in error_analyses.items():
        related = analysis.get("related_concepts", [])
        error_type = analysis.get("error_type", "unknown")

        # Write weak_point
        weak_point = {
            "concept": related[0] if related else qid,
            "error_type": error_type,
            "explanation": analysis.get("explanation", "")[:200],
            "recovery_plan": analysis.get("recovery_plan", "")[:200],
            "timestamp": result.completed_at,
        }

        try:
            mm.update_student_memory(
                student_id=student_id,
                weak_point=weak_point,
            )
        except Exception:
            pass

    # Write overall feedback
    feedback = {
        "quiz_id": result.quiz_id,
        "score": result.score_percent,
        "correct": result.correct_count,
        "total": result.total_questions,
        "weak_areas": result.weak_areas,
        "strong_areas": result.strong_areas,
        "errors_analyzed": len(error_analyses),
        "error_types": list(set(a.get("error_type", "") for a in error_analyses.values())),
        "timestamp": result.completed_at,
    }

    try:
        mm.update_student_memory(
            student_id=student_id,
            feedback=feedback,
        )
    except Exception:
        pass


def get_quiz_evaluation_dict() -> Optional[Dict[str, Any]]:
    """Retrieve the quiz evaluation dict for injection into workflow result."""
    return st.session_state.get(_QUIZ_EVAL_DICT)
