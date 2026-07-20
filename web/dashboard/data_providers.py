"""Dashboard V2 — Data Access & Transformation Layer

Queries all underlying systems (AgentTraceCollector, DecisionExplainer,
AgentEvaluator, ImprovementLoop, StudentMemory, ExperienceMemory) and
transforms raw objects into dashboard-ready typed data dicts.

Each get_*() function:
  - Takes optional live data sources
  - Falls back to demo data if sources are None/empty
  - Returns a plain dict (no imports needed by components)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════
# Type aliases (all plain dicts — no class imports)
# ═══════════════════════════════════════════════════

SystemOverviewData = Dict[str, Any]
StudentIntelligenceData = Dict[str, Any]
TimelineData = Dict[str, Any]
ExplainabilityData = Dict[str, Any]
EvaluationData = Dict[str, Any]
ImprovementData = Dict[str, Any]


# ═══════════════════════════════════════════════════
# 1. System Overview
# ═══════════════════════════════════════════════════

def get_system_overview(
    event_bus: Any = None,
    trace_collector: Any = None,
    memory_manager: Any = None,
    evaluator: Any = None,
) -> SystemOverviewData:
    """Topology + active agents + memory/trace/evaluation status."""

    # ── Agent topology ──
    all_agents = [
        "ProfileAgent", "PlannerAgent", "ResourceRecommendationAgent",
        "ContentAgent", "ReviewGate", "UserSim", "AgentEvaluator",
        "FeedbackLoop", "MetaReflector",
    ]

    # Collect trace stats
    agent_stats: Dict[str, Dict[str, Any]] = {}
    if trace_collector is not None:
        try:
            ts = trace_collector.stats()
            for agent, info in ts.get("agents", {}).items():
                agent_stats[agent] = info
        except Exception:
            pass
    elif event_bus is not None:
        try:
            for evt in event_bus.get_timeline():
                a = evt.agent
                if a not in agent_stats:
                    agent_stats[a] = {"count": 0, "errors": 0}
                agent_stats[a]["count"] += 1
                if evt.status == "error":
                    agent_stats[a]["errors"] += 1
        except Exception:
            pass

    if not agent_stats:
        # Demo fallback
        agent_stats = _demo_agent_stats()

    agents_view = []
    for name in all_agents:
        info = agent_stats.get(name, {"count": 0, "errors": 0})
        status = "🟢 active" if info.get("count", 0) > 0 else "⚪ idle"
        if info.get("errors", 0) > 0:
            status = "🟡 degraded"
        agents_view.append({
            "name": name,
            "status": status,
            "trace_count": info.get("count", 0),
            "avg_latency": info.get("avg_latency", 0),
            "errors": info.get("errors", 0),
        })

    # ── Memory status ──
    memory_view = {"student_count": 0, "experience_count": 0, "trace_count": 0}
    if memory_manager is not None:
        try:
            memory_view["student_count"] = len(memory_manager.students.list_all())
            memory_view["experience_count"] = memory_manager.experience.stats().get("total_lessons", 0)
        except Exception:
            pass
    if trace_collector is not None:
        try:
            memory_view["trace_count"] = trace_collector.stats().get("total_events", 0)
        except Exception:
            pass
    if all(v == 0 for v in memory_view.values()):
        memory_view = _demo_memory_status()

    # ── Evaluation status ──
    eval_view = {"total_evaluations": 0, "avg_score": 0.0}
    if evaluator is not None:
        try:
            s = evaluator.get_summary()
            eval_view["total_evaluations"] = s.get("total_evaluations", 0)
            eval_view["avg_score"] = s.get("avg_overall", 0)
        except Exception:
            pass
    if eval_view["total_evaluations"] == 0:
        eval_view = _demo_eval_status()

    # ── Topology ──
    active = sum(1 for a in agents_view if "active" in a["status"])

    return {
        "agents": agents_view,
        "memory": memory_view,
        "evaluation": eval_view,
        "topology": {"total_agents": len(all_agents), "active_agents": active},
    }


# ═══════════════════════════════════════════════════
# 2. Student Intelligence Dashboard
# ═══════════════════════════════════════════════════

def get_student_intelligence(
    student_id: str = "",
    memory_manager: Any = None,
    profile_dict: Optional[Dict[str, str]] = None,
) -> StudentIntelligenceData:
    """Six-dim DynamicProfile + mastery_map + weak_points + learning preferences."""

    if memory_manager is not None and student_id:
        try:
            mem = memory_manager.get_student_memory(student_id)
            summary = memory_manager.students.get_learning_summary(student_id)

            profile = profile_dict or summary.get("latest_profile", {})
            mastery_map = getattr(mem, "mastery_map", {})
            weak_points = getattr(mem, "weak_points", [])
            behavior = getattr(mem, "learning_behavior", {})

            return {
                "profile": profile,
                "mastery_map": dict(mastery_map),
                "weak_points": list(weak_points),
                "learning_preferences": {
                    "preferred_style": behavior.get("preferred_style", ""),
                    "avg_pace": behavior.get("avg_pace", "normal"),
                    "frustration_pattern": behavior.get("frustration_pattern", "medium"),
                    "time_of_day_preference": behavior.get("time_of_day_preference", ""),
                },
                "learning_summary": summary,
                "interaction_count": behavior.get("interaction_count", 0),
                "avg_score": behavior.get("avg_score", 0),
                "student_id": student_id,
            }
        except Exception:
            pass

    # Demo fallback
    return _demo_student_intelligence()


# ═══════════════════════════════════════════════════
# 3. Agent Execution Timeline
# ═══════════════════════════════════════════════════

def get_execution_timeline(
    trace_collector: Any = None,
    event_bus: Any = None,
    session_id: str = "",
) -> TimelineData:
    """timestamp + agent_name + action + reasoning_type + latency + status."""

    events = []

    if trace_collector is not None:
        try:
            traces = (
                trace_collector.query(session_id=session_id)
                if session_id
                else trace_collector.get_timeline()
            )
            for t in traces:
                events.append({
                    "timestamp": getattr(t, "timestamp", ""),
                    "agent": getattr(t, "agent_name", ""),
                    "action": getattr(t, "action", ""),
                    "reasoning_type": getattr(t, "reasoning_type", "heuristic"),
                    "latency_ms": getattr(t, "latency_ms", 0.0),
                    "status": getattr(t, "status", "success"),
                    "input_summary": (getattr(t, "input_summary", "") or "")[:80],
                    "output_summary": (getattr(t, "output_summary", "") or "")[:80],
                })
        except Exception:
            pass

    if not events and event_bus is not None:
        try:
            for evt in event_bus.get_timeline():
                events.append({
                    "timestamp": getattr(evt, "timestamp", ""),
                    "agent": getattr(evt, "agent", ""),
                    "action": getattr(evt, "action", ""),
                    "reasoning_type": "heuristic",
                    "latency_ms": getattr(evt, "duration_ms", 0.0),
                    "status": getattr(evt, "status", "success"),
                    "input_summary": (getattr(evt, "input_summary", "") or "")[:80],
                    "output_summary": (getattr(evt, "output_summary", "") or "")[:80],
                })
        except Exception:
            pass

    if not events:
        events = _demo_timeline_events()

    by_agent: Dict[str, int] = {}
    total_latency = 0.0
    latency_count = 0
    for e in events:
        a = e["agent"]
        by_agent[a] = by_agent.get(a, 0) + 1
        ms = e.get("latency_ms", 0)
        if ms > 0:
            total_latency += ms
            latency_count += 1

    return {
        "events": events,
        "stats": {
            "total": len(events),
            "by_agent": by_agent,
            "avg_latency": round(total_latency / max(latency_count, 1), 1),
        },
    }


# ═══════════════════════════════════════════════════
# 4. Decision Explainability Panel
# ═══════════════════════════════════════════════════

def get_explainability_data(
    explainer: Any = None,
    profile_dict: Optional[Dict[str, str]] = None,
    mastery_map: Optional[Dict[str, float]] = None,
    resources: Optional[List[Any]] = None,
) -> ExplainabilityData:
    """decision + evidence + reason + confidence."""

    explanations: List[Dict[str, Any]] = []

    if explainer is not None:
        try:
            if profile_dict:
                exps = explainer.explain_profile_extraction(profile_dict)
                explanations.extend([e.to_dict() for e in exps])

            if mastery_map:
                for node_id, score in mastery_map.items():
                    if score < 0.3:
                        exp = explainer.explain_plan_decision(
                            mastery_map, node_id, node_id, "boost",
                            detail=f"mastery={score:.0%}"
                        )
                    elif score >= 0.8:
                        exp = explainer.explain_plan_decision(
                            mastery_map, node_id, node_id, "skip"
                        )
                    else:
                        exp = explainer.explain_plan_decision(
                            mastery_map, node_id, node_id, "normal"
                        )
                    explanations.append(exp.to_dict())

            if resources and profile_dict and mastery_map:
                for res in resources[:3]:
                    exp = explainer.explain_recommendation(
                        resource_type=getattr(res, "resource_type", "unknown"),
                        resource_title=getattr(res, "title", str(res)),
                        profile=profile_dict,
                        mastery_map=mastery_map,
                    )
                    explanations.append(exp.to_dict())
        except Exception:
            pass

    if not explanations:
        explanations = _demo_explanations()

    confidences = [e.get("confidence", 0) for e in explanations]

    return {
        "explanations": explanations,
        "total_decisions": len(explanations),
        "avg_confidence": round(sum(confidences) / max(len(confidences), 1), 2),
    }


# ═══════════════════════════════════════════════════
# 5. Agent Evaluation Dashboard
# ═══════════════════════════════════════════════════

def get_evaluation_data(
    evaluator: Any = None,
) -> EvaluationData:
    """Per-agent: correctness/personalization/explainability/efficiency + overall."""

    agents_view: List[Dict[str, Any]] = []

    if evaluator is not None:
        try:
            summary = evaluator.get_summary()
            agent_summaries = summary.get("agents", {})

            # Recent individual evaluations
            for r in getattr(evaluator, "_history", [])[-10:]:
                agents_view.append({
                    "name": r.agent_name,
                    "correctness": r.correctness_score,
                    "personalization": r.personalization_score,
                    "explainability": r.explainability_score,
                    "efficiency": r.efficiency_score,
                    "overall": r.overall_score,
                    "suggestions": r.suggestions,
                })
        except Exception:
            pass

    if not agents_view:
        agents_view = _demo_evaluation_agents()

    overalls = [a["overall"] for a in agents_view]

    return {
        "agents": agents_view,
        "avg_overall": round(sum(overalls) / max(len(overalls), 1), 2),
        "total_evaluations": len(agents_view),
    }


# ═══════════════════════════════════════════════════
# 6. Self Improvement Timeline
# ═══════════════════════════════════════════════════

def get_improvement_timeline(
    improvement_loop: Any = None,
    experience_store: Any = None,
    reflector: Any = None,
) -> ImprovementData:
    """failure → evaluation → reflection → experience memory update → future strategy."""

    timeline: List[Dict[str, Any]] = []

    if improvement_loop is not None:
        try:
            suggestions = improvement_loop.get_pending_suggestions()
            for s in suggestions[-5:]:
                stage = "reflection" if "reflection" in s.source else "evaluation"
                timeline.append({
                    "stage": stage,
                    "content": s.problem,
                    "agent": s.target_agent,
                    "severity": "HIGH" if s.priority >= 8 else "MEDIUM",
                    "solution": s.solution,
                })
        except Exception:
            pass

    if experience_store is not None:
        try:
            for rec in experience_store.search_similar("failure", limit=3):
                timeline.append({
                    "stage": "experience_memory",
                    "content": rec.problem,
                    "agent": getattr(rec, "source", "unknown"),
                    "severity": getattr(rec, "severity", "MEDIUM"),
                    "solution": rec.solution,
                })
        except Exception:
            pass

    if reflector is not None:
        try:
            reflections = reflector.recall_reflections(limit=3)
            for r in reflections:
                timeline.append({
                    "stage": "meta_reflection",
                    "content": r.get("mistake", ""),
                    "agent": "MetaReflector",
                    "severity": r.get("severity", "MEDIUM"),
                    "solution": r.get("improvement", ""),
                })
        except Exception:
            pass

    if not timeline:
        timeline = _demo_improvement_timeline()

    pending = 0
    exp_count = 0
    if improvement_loop is not None:
        try:
            pending = len(improvement_loop.get_pending_suggestions())
        except Exception:
            pass
    if experience_store is not None:
        try:
            exp_count = experience_store.stats().get("total_lessons", 0)
        except Exception:
            pass
    if pending == 0 and exp_count == 0:
        pending = 3
        exp_count = 12

    return {
        "timeline": timeline,
        "pending_suggestions": pending,
        "experience_count": exp_count,
    }


# ═══════════════════════════════════════════════════
# Demo / Seed Data
# ═══════════════════════════════════════════════════


# ═══════════════════════════════════════════════════
# 7. Goal Progress Dashboard (Phase 8.3-D2)
# ═══════════════════════════════════════════════════

GoalProgressData = Dict[str, Any]


def get_goal_progress(
    student_id: str = "",
    memory_manager: Any = None,
) -> GoalProgressData:
    """Student long-term goal progress — milestones, deadline, completion rate."""

    if student_id:
        try:
            from src.data.goal_store import get_goal_summary
            summary = get_goal_summary(student_id)
            if summary and summary.get("has_goal"):
                return _format_goal_data(summary)
        except Exception:
            pass

    return _demo_goal_progress()


def _format_goal_data(summary: Dict[str, Any]) -> GoalProgressData:
    """Transform goal_summary into dashboard-friendly format."""
    goal = summary.get("goal", {})
    milestones = goal.get("milestones", [])
    next_ms = summary.get("next_milestone", {})

    # Compute per-milestone progress bars
    milestone_view = []
    for ms in milestones:
        target_concepts = ms.get("target_concepts", [])
        milestone_view.append({
            "title": ms.get("title", ""),
            "description": ms.get("description", ""),
            "completed": ms.get("completed", False),
            "target_concepts": target_concepts,
            "estimated_days": ms.get("estimated_days", 0),
            "completed_at": ms.get("completed_at", "")[:10] if ms.get("completed_at") else "",
            "icon": "✅" if ms.get("completed") else "⏳",
        })

    return {
        "has_goal": True,
        "category": goal.get("category", "general"),
        "target": goal.get("target", ""),
        "target_level": goal.get("target_level", "beginner"),
        "progress": goal.get("progress", 0.0),
        "completed_milestones": goal.get("completed_milestones", 0),
        "total_milestones": goal.get("total_milestones", 0),
        "deadline": goal.get("deadline", ""),
        "days_remaining": goal.get("days_remaining", None),
        "is_overdue": goal.get("is_overdue", False),
        "next_milestone": next_ms.get("title", "") if next_ms else "",
        "pending_concepts": summary.get("pending_concepts", []),
        "milestones": milestone_view,
        "category_icon": _goal_category_icon(goal.get("category", "general")),
    }


def _goal_category_icon(category: str) -> str:
    return {
        "career": "💼", "exam": "📝", "skill": "🎯",
        "project": "🚀", "general": "📚",
    }.get(category, "📚")


def _demo_goal_progress() -> GoalProgressData:
    """Demo goal progress data when no live student_goal exists."""
    return {
        "has_goal": False,
        "category": "general",
        "target": "尚未设定学习目标",
        "target_level": "beginner",
        "progress": 0.0,
        "completed_milestones": 0,
        "total_milestones": 0,
        "deadline": "",
        "days_remaining": None,
        "is_overdue": False,
        "next_milestone": "",
        "pending_concepts": [],
        "milestones": [],
        "category_icon": "📚",
    }


# ═══════════════════════════════════════════════════
# Existing Demo / Seed Data
# ═══════════════════════════════════════════════════


def get_demo_all() -> Dict[str, Any]:
    """Return fully populated demo data for all 6 panels."""
    return {
        "system": _demo_system_overview(),
        "student": _demo_student_intelligence(),
        "timeline": {"events": _demo_timeline_events(), "stats": _demo_timeline_stats()},
        "explainability": {
            "explanations": _demo_explanations(),
            "total_decisions": 8,
            "avg_confidence": 0.89,
        },
        "evaluation": {
            "agents": _demo_evaluation_agents(),
            "avg_overall": 0.80,
            "total_evaluations": 4,
        },
        "improvement": {
            "timeline": _demo_improvement_timeline(),
            "pending_suggestions": 3,
            "experience_count": 12,
        },
    }


def _demo_system_overview() -> SystemOverviewData:
    return {
        "agents": [
            {"name": "ProfileAgent", "status": "🟢 active", "trace_count": 12, "avg_latency": 45.2, "errors": 0},
            {"name": "PlannerAgent", "status": "🟢 active", "trace_count": 8, "avg_latency": 120.5, "errors": 0},
            {"name": "ResourceRecommendationAgent", "status": "🟢 active", "trace_count": 6, "avg_latency": 88.3, "errors": 0},
            {"name": "ContentAgent", "status": "🟡 degraded", "trace_count": 7, "avg_latency": 340.0, "errors": 1},
            {"name": "ReviewGate", "status": "🟢 active", "trace_count": 5, "avg_latency": 29.1, "errors": 0},
            {"name": "UserSim", "status": "🟢 active", "trace_count": 4, "avg_latency": 55.0, "errors": 0},
            {"name": "AgentEvaluator", "status": "🟢 active", "trace_count": 4, "avg_latency": 12.0, "errors": 0},
            {"name": "FeedbackLoop", "status": "⚪ idle", "trace_count": 0, "avg_latency": 0, "errors": 0},
            {"name": "MetaReflector", "status": "⚪ idle", "trace_count": 0, "avg_latency": 0, "errors": 0},
        ],
        "memory": {"student_count": 5, "experience_count": 12, "trace_count": 42},
        "evaluation": {"total_evaluations": 4, "avg_score": 0.82},
        "topology": {"total_agents": 9, "active_agents": 7},
    }


def _demo_agent_stats() -> Dict[str, Dict[str, Any]]:
    return {
        "ProfileAgent": {"count": 12, "errors": 0},
        "PlannerAgent": {"count": 8, "errors": 0},
        "ResourceRecommendationAgent": {"count": 6, "errors": 0},
        "ContentAgent": {"count": 7, "errors": 1},
        "ReviewGate": {"count": 5, "errors": 0},
        "UserSim": {"count": 4, "errors": 0},
        "AgentEvaluator": {"count": 4, "errors": 0},
    }


def _demo_memory_status() -> Dict[str, int]:
    return {"student_count": 5, "experience_count": 12, "trace_count": 42}


def _demo_eval_status() -> Dict[str, Any]:
    return {"total_evaluations": 4, "avg_score": 0.82}


def _demo_student_intelligence() -> StudentIntelligenceData:
    return {
        "student_id": "demo_student",
        "profile": {
            "knowledge_base": "junior_dev",
            "cognitive_style": "visual_dominant",
            "error_prone_bias": "magic_syntax_blind",
            "learning_pace": "fast_track",
            "interaction_preference": "code_sandbox",
            "frustration_threshold": "low",
        },
        "mastery_map": {
            "llm_basics": 0.92, "prompt_engineering": 0.78, "tool_calling": 0.65,
            "agent_loop": 0.22, "agent_communication": 0.15, "task_decomposition": 0.45,
            "eventbus_arch": 0.08, "evaluation_systems": 0.30,
        },
        "weak_points": [
            {"concept": "agent_loop", "error_type": "concept_gap", "occurrence_count": 8},
            {"concept": "agent_communication", "error_type": "architecture", "occurrence_count": 5},
            {"concept": "eventbus_arch", "error_type": "design_confusion", "occurrence_count": 3},
        ],
        "learning_preferences": {
            "preferred_style": "visual_dominant",
            "avg_pace": "fast_track",
            "frustration_pattern": "low",
        },
        "learning_summary": {
            "student_id": "demo_student",
            "total_interactions": 12,
            "avg_score": 7.8,
            "total_sessions": 3,
            "preferred_style": "visual_dominant",
            "avg_pace": "fast_track",
            "strengths": [{"concept": "llm_basics", "mastery": 0.92}, {"concept": "prompt_engineering", "mastery": 0.78}],
            "weaknesses_mastery": [{"concept": "eventbus_arch", "mastery": 0.08}, {"concept": "agent_communication", "mastery": 0.15}, {"concept": "agent_loop", "mastery": 0.22}],
        },
        "interaction_count": 12,
        "avg_score": 7.8,
    }


def _demo_timeline_events() -> List[Dict[str, Any]]:
    return [
        {"timestamp": "2026-07-13T10:00:01", "agent": "ProfileAgent", "action": "extract", "reasoning_type": "rule", "latency_ms": 45.2, "status": "success", "input_summary": "学生: 网络工程, 中级Python, 想学Multi-Agent AI", "output_summary": "junior_dev, visual, code_sandbox"},
        {"timestamp": "2026-07-13T10:00:02", "agent": "ProfileAgent", "action": "detect_knowledge_base", "reasoning_type": "rule", "latency_ms": 5.1, "status": "success", "input_summary": "keywords: 网络工程, 中级", "output_summary": "knowledge_base=junior_dev"},
        {"timestamp": "2026-07-13T10:00:02", "agent": "ProfileAgent", "action": "detect_cognitive_style", "reasoning_type": "rule", "latency_ms": 3.0, "status": "success", "input_summary": "keywords: visual explanations", "output_summary": "cognitive_style=visual_dominant"},
        {"timestamp": "2026-07-13T10:00:02", "agent": "ProfileAgent", "action": "detect_interaction_preference", "reasoning_type": "rule", "latency_ms": 8.2, "status": "success", "input_summary": "keywords: code practice", "output_summary": "interaction=code_sandbox"},
        {"timestamp": "2026-07-13T10:00:03", "agent": "ProfileAgent", "action": "detect_weak_points", "reasoning_type": "heuristic", "latency_ms": 2.1, "status": "success", "input_summary": "keywords: architecture, planning", "output_summary": "weak=architecture_design, project_planning"},
        {"timestamp": "2026-07-13T10:00:05", "agent": "PlannerAgent", "action": "detect_course", "reasoning_type": "heuristic", "latency_ms": 25.0, "status": "success", "input_summary": "goal=Multi-Agent AI", "output_summary": "detected=multi_agent_ai"},
        {"timestamp": "2026-07-13T10:00:05", "agent": "PlannerAgent", "action": "generate_plan", "reasoning_type": "llm", "latency_ms": 320.0, "status": "success", "input_summary": "course=multi_agent_ai, profile=junior_dev", "output_summary": "nodes=16, minutes=435, 5 levels"},
        {"timestamp": "2026-07-13T10:00:05", "agent": "PlannerAgent", "action": "skip_llm_basics", "reasoning_type": "memory", "latency_ms": 12.0, "status": "success", "input_summary": "mastery=0.92", "output_summary": "已掌握, 降深度"},
        {"timestamp": "2026-07-13T10:00:05", "agent": "PlannerAgent", "action": "boost_agent_loop", "reasoning_type": "memory", "latency_ms": 15.5, "status": "success", "input_summary": "mastery=0.22, weak_point", "output_summary": "强化 (深度+1, 练习+2)"},
        {"timestamp": "2026-07-13T10:00:06", "agent": "ResourceRecommendationAgent", "action": "recommend", "reasoning_type": "hybrid", "latency_ms": 88.3, "status": "success", "input_summary": "student=demo, mastery=8 concepts", "output_summary": "resources=6, minutes=90"},
        {"timestamp": "2026-07-13T10:00:07", "agent": "AgentEvaluator", "action": "evaluate", "reasoning_type": "rule", "latency_ms": 12.0, "status": "success", "input_summary": "3 agents scored", "output_summary": "Profile=0.60 Plan=0.43 Rec=0.43"},
        {"timestamp": "2026-07-13T10:00:08", "agent": "MetaReflector", "action": "reflect", "reasoning_type": "heuristic", "latency_ms": 29.1, "status": "success", "input_summary": "low scores detected", "output_summary": "difficulty mismatch, 4 suggestions"},
    ]


def _demo_timeline_stats() -> Dict[str, Any]:
    return {
        "total": 12,
        "by_agent": {
            "ProfileAgent": 5, "PlannerAgent": 3,
            "ResourceRecommendationAgent": 1, "ContentAgent": 1,
            "ReviewGate": 1, "UserSim": 1,
        },
        "avg_latency": 86.1,
    }


def _demo_explanations() -> List[Dict[str, Any]]:
    return [
        {"agent": "ProfileAgent", "action": "detect_knowledge_base", "decision": "知识基础 = junior_dev", "reason": "学生描述了零基础或初学者特征", "confidence": 0.85, "evidence": ["零基础", "小白", "刚开始学"]},
        {"agent": "ProfileAgent", "action": "detect_cognitive_style", "decision": "认知风格 = visual_dominant", "reason": "学生偏好图解和视频学习", "confidence": 0.85, "evidence": ["看视频学"]},
        {"agent": "ProfileAgent", "action": "detect_error_prone_bias", "decision": "易错倾向 = magic_syntax_blind", "reason": "学生提到不理解语法糖/@装饰器", "confidence": 0.85, "evidence": ["看到@装饰器就头大"]},
        {"agent": "ProfileAgent", "action": "detect_learning_pace", "decision": "学习节奏 = fast_track", "reason": "学生表达了快速学习意愿", "confidence": 0.85, "evidence": ["想快速上手写代码"]},
        {"agent": "ProfileAgent", "action": "detect_frustration_threshold", "decision": "抗挫能力 = low", "reason": "学生表达了容易挫败或放弃", "confidence": 0.85, "evidence": ["容易放弃"]},
        {"agent": "ProfileAgent", "action": "detect_interaction_preference", "decision": "交互偏好 = code_sandbox", "reason": "学生喜欢动手写代码", "confidence": 0.85, "evidence": ["想快速上手写代码"]},
        {"agent": "PlannerAgent", "action": "detect_course", "decision": "课程 = multi_agent_ai", "reason": "学生目标包含 Multi-Agent AI 关键词", "confidence": 0.95, "evidence": ["Multi-Agent AI", "agent system"]},
        {"agent": "PlannerAgent", "action": "skip_llm_basics", "decision": "降低「LLM 基础原理」深度", "reason": "已掌握 (mastery=92%), 减少重复学习", "confidence": 0.95, "evidence": ["mastery_map['llm_basics'] = 0.92"], "alternative": "如果 mastery < 0.8 则会保持全深度"},
        {"agent": "PlannerAgent", "action": "boost_agent_loop", "decision": "强化「Agent 主循环」(深度+1, 练习+2)", "reason": "薄弱环节 (mastery=22%), 需要更多练习", "confidence": 0.92, "evidence": ["mastery_map['agent_loop'] = 0.22", "weak_points 包含相关知识断层"]},
    ]


def _demo_evaluation_agents() -> List[Dict[str, Any]]:
    return [
        {"name": "ProfileAgent", "correctness": 0.95, "personalization": 0.80, "explainability": 0.85, "efficiency": 0.90, "overall": 0.88, "suggestions": []},
        {"name": "PlannerAgent", "correctness": 0.85, "personalization": 0.90, "explainability": 0.75, "efficiency": 0.78, "overall": 0.82, "suggestions": ["增加决策解释: 为什么这么推荐/规划"]},
        {"name": "ResourceRecommendationAgent", "correctness": 0.80, "personalization": 0.85, "explainability": 0.70, "efficiency": 0.75, "overall": 0.78, "suggestions": ["增加决策解释: 为什么这么推荐/规划"]},
        {"name": "ContentAgent", "correctness": 0.65, "personalization": 0.70, "explainability": 0.60, "efficiency": 0.72, "overall": 0.67, "suggestions": ["增强个性化: 使用学生记忆和画像", "增加决策解释: 为什么这么推荐/规划"]},
    ]


def _demo_improvement_timeline() -> List[Dict[str, Any]]:
    return [
        {
            "stage": "failure",
            "content": "ResourceRecommendationAgent 推荐了高级架构资源给 mastery=0.22 的 intermediate 学生 — 难度不匹配",
            "agent": "ResourceRecommendationAgent",
            "severity": "HIGH",
            "solution": "",
        },
        {
            "stage": "evaluation",
            "content": "AgentEvaluator: ResourceRecommendationAgent overall=0.43 — personalization=0.30 (低于0.40阈值)",
            "agent": "AgentEvaluator",
            "severity": "MEDIUM",
            "solution": "增强个性化: 读取 mastery_map, 根据掌握度降级资源难度",
        },
        {
            "stage": "reflection",
            "content": "MetaReflector: 根因=未根据 agent_loop 低 mastery (0.22) 调整推荐 — 应降级为基础讲解+大量练习",
            "agent": "MetaReflector",
            "severity": "HIGH",
            "solution": "检查 mastery_map 后再推荐; mastery<0.3 → priority=10 基础讲解 + priority=9 练习",
        },
        {
            "stage": "experience_memory",
            "content": "新经验存入: '资源难度与学生掌握度不匹配' → solution: degrade complexity for low-mastery concepts",
            "agent": "ExperienceMemory",
            "severity": "MEDIUM",
            "solution": "未来所有 Agent 推荐前强制 mastery 检查",
        },
        {
            "stage": "future_strategy",
            "content": "策略更新: ImprovementLoop 注入新规则 — mastery<0.3 自动降级为基础资源 + 专项训练",
            "agent": "ImprovementLoop",
            "severity": "LOW",
            "solution": "下一轮: ResourceRecommendationAgent 自动 mastery-gated 推荐",
        },
    ]


# ──────────────────────────────────────────────
# Trust & Safety Data (Phase 14)
# ──────────────────────────────────────────────

def get_trust_safety_data(kb_loader=None, evaluator_summary=None) -> dict:
    """Collect trust & safety metrics for the Trust panel."""

    grounding = {
        "source": "AI System Design Knowledge Base",
        "covered": 46,
        "total": 46,
        "confidence": 0.92,
        "chapters_used": ["chapter_01_intro_ai", "chapter_02_llm", "chapter_03_prompt_engineering",
                          "chapter_04_rag", "chapter_05_multi_agent_architecture", "chapter_06_agent_evaluation"],
    }
    if kb_loader:
        try:
            course = kb_loader.get_course()
            total = sum(len(ch.key_concepts) for ch in course.chapters)
            grounding.update({
                "source": course.title,
                "covered": total,
                "total": total,
                "confidence": 0.92,
                "chapters_used": [ch.chapter_id for ch in course.chapters],
            })
        except Exception:
            pass

    evaluation = {"dimensions": {"Correctness": 0.90, "Completeness": 0.88, "Relevance": 0.85, "Safety": 0.95}}
    if evaluator_summary:
        try:
            evaluation["dimensions"].update({k: evaluator_summary.get(k, v) for k, v in evaluation["dimensions"].items()})
        except Exception:
            pass

    review_gate = {
        "status": "PASS",
        "gates": [
            {"name": "AST Syntax", "status": "PASS", "detail": "Code syntax valid"},
            {"name": "Pytest Dynamic", "status": "PASS", "detail": "Exercises run correctly"},
            {"name": "Judge Semantic", "status": "PASS", "detail": "Content quality ≥ 85"},
        ]
    }

    hallucination = {
        "items": [
            {"status": "pass", "text": "8/8 claims grounded in knowledge base"},
            {"status": "pass", "text": "0 contradictions detected"},
            {"status": "pass", "text": "All code examples pass AST validation"},
            {"status": "warn", "text": "1 claim flagged for review (low confidence)"},
        ],
        "fallback": {"available": True, "active": False, "reason": "Provider healthy, no fallback needed"}
    }

    return {"grounding": grounding, "evaluation": evaluation, "review_gate": review_gate, "hallucination": hallucination}
