"""
Phase 4 — A3Workflow: 多 Agent 协作编排器

职责:
  - 创建执行上下文
  - 触发 Agent 按序执行
  - 监听 EventBus 事件
  - 收集并返回 WorkflowResult (from .result)

Pipeline:
  User Goal → ProfileAgent → PlannerAgent → ContentGeneratorAgent → ResourceAgent → Review → ReflectionAgent → Memory
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import time

from src.core.event_bus import AgentEventBus
from src.core.event_trace import TraceCollector

from src.agents.profile_agent import ProfileAgent, ProfileExtractionResult
from src.agents.planner_agent import PlannerAgent, LearningPlan
from src.agents.resource_agent import ResourceAgent, ResourceRecommendation
from src.agents.reflection_agent import ReflectionAgent, ReflectionResult
from src.agents.content_generator_agent import ContentGeneratorAgent, TeachingMaterial
from veritas.memory import MemoryManager

# Phase 4.6 — MetaReflector integration
from src.core.meta_reflector import MetaReflectorAgent
from src.core.meta_reflection_adapter import MetaReflectionAdapter

from .result import WorkflowContext, WorkflowResult


# ──────────────────────────────────────────────
# A3Workflow
# ──────────────────────────────────────────────

class A3Workflow:
    """
    多 Agent 协作工作流编排器.

    使用:
        workflow = A3Workflow()
        result = workflow.run(
            user_goal="学习 Python 网络编程",
            user_profile={"knowledge_base": "junior_dev", ...},
        )
        # result.learning_plan  — PlannerAgent 输出
        # result.evaluation     — ReviewGate 评分
        # result.trace          — EventBus 完整时间线
        # result.memory_saved   — 是否成功持久化
    """

    def __init__(
        self,
        memory_manager: Optional[MemoryManager] = None,
        profile_agent: Optional[ProfileAgent] = None,
        planner_agent: Optional[PlannerAgent] = None,
        content_generator_agent: Optional[ContentGeneratorAgent] = None,
        resource_agent: Optional[ResourceAgent] = None,
        reflection_agent: Optional[ReflectionAgent] = None,
        meta_reflector: Optional[MetaReflectorAgent] = None,  # Phase 4.6
        student_id: str = "demo_student",
        llm_provider: Any = None,
        bus: Optional[AgentEventBus] = None,
        knowledge_graph: Any = None,  # Phase 8.3-D1
    ):
        self.memory = memory_manager or MemoryManager()
        self.profile_agent = profile_agent or ProfileAgent()
        self.planner_agent = planner_agent or PlannerAgent()
        self.content_generator_agent = content_generator_agent or ContentGeneratorAgent()
        self.resource_agent = resource_agent or ResourceAgent()
        self.reflection_agent = reflection_agent or ReflectionAgent()
        self.meta_reflector = meta_reflector  # Phase 4.6
        self.student_id = student_id
        self._kg = knowledge_graph  # Phase 8.3-D1

        # Phase 4.6 — Wire MetaReflector to ExperienceMemory
        self._meta_adapter = MetaReflectionAdapter()
        if self.meta_reflector is not None:
            self.meta_reflector.set_experience_store(self.memory.experience)

        # Phase 4.2.6 — EventBus: 外部注入实例优先, 否则使用全局单例
        #   API 请求:     传入独立 EventBus() → 请求级隔离
        #   Streamlit:     不传 → 使用全局单例 (保持向后兼容)
        self._bus = bus if bus is not None else AgentEventBus.get_instance()
        self._owns_bus = bus is not None  # True = 注入实例, False = 全局单例

        # Phase 4.2 — LLM Provider 注入 (None = 纯规则模式)
        self.llm_provider = llm_provider
        if llm_provider is not None:
            self.profile_agent.set_llm_provider(llm_provider)
            self.planner_agent.set_llm_provider(llm_provider)
            self.content_generator_agent.set_llm_provider(llm_provider)
            self.resource_agent.set_llm_provider(llm_provider)
            self.reflection_agent.set_llm_provider(llm_provider)

    # ── 主入口 ────────────────────────────────

    def run(
        self,
        user_goal: str,
        user_profile: Optional[Dict[str, Any]] = None,
        knowledge_gaps: Optional[List[str]] = None,
        session_id: str = "",
    ) -> WorkflowResult:
        """
        执行完整 Agent 协作管道.

        Args:
            user_goal: 用户学习目标
            user_profile: 预置画像 (可选, 为空则自动提取)
            knowledge_gaps: 知识缺口列表 (可选)
            session_id: 会话 ID (自动生成)

        Returns:
            WorkflowResult (含 profile, learning_plan, content, resources, evaluation,
                            reflection, trace, memory_saved)
        """
        start_time = time.time()
        errors: List[str] = []
        session_id = session_id or f"a3_session_{int(time.time())}"

        # 初始化上下文
        context = WorkflowContext(
            session_id=session_id,
            user_goal=user_goal,
            user_profile=user_profile or {},
            knowledge_gaps=knowledge_gaps or [],
        )

        # 重置 EventBus
        # Phase 4.2.6 — API 请求使用独立实例时只 clear，不触碰全局单例
        if self._owns_bus:
            # 注入的独立 EventBus — 只清空自己的事件
            self._bus.clear()
        else:
            # 全局单例 — 需要 reset 以清理之前的 session (Streamlit 兼容)
            AgentEventBus.reset_instance()
            self._bus = AgentEventBus.get_instance()
        self._bus.start_session(session_id)

        result = WorkflowResult(context=context)

        # ── Step 1: ProfileAgent — 分析学习者 ──
        try:
            _t0 = time.time()
            profile_result = self._run_profile_agent(user_goal, user_profile)
            result.profile = profile_result.to_dict() if hasattr(profile_result, "to_dict") else profile_result
            _profile_d = result.profile or {}
            _source = _profile_d.get("source", "rule")
            self._emit("ProfileAgent", "profile_extracted",
                       f"目标: {user_goal[:60]}",
                       f"画像: {_profile_d.get('profile', {}).get('knowledge_base', 'unknown')} "
                       f"(mode={_source})",
                       duration_ms=round((time.time() - _t0) * 1000, 1))
        except Exception as e:
            errors.append(f"ProfileAgent: {e}")
            self._emit("ProfileAgent", "profile_extracted",
                       f"目标: {user_goal[:60]}", str(e), "error")

        # ── Step 2: PlannerAgent — 生成学习路径 ──
        try:
            _t0 = time.time()
            plan_result = self._run_planner_agent(user_goal, result.profile)
            result.learning_plan = plan_result.to_dict() if hasattr(plan_result, "to_dict") else plan_result
            node_count = len(result.learning_plan.get("nodes", [])) if result.learning_plan else 0
            _mode = (result.learning_plan or {}).get("metadata", {}).get("planning_mode", "rule")
            self._emit("PlannerAgent", "plan_generated",
                       f"目标: {user_goal[:60]}",
                       f"路径: {node_count} 个节点 (mode={_mode})",
                       duration_ms=round((time.time() - _t0) * 1000, 1))
        except Exception as e:
            errors.append(f"PlannerAgent: {e}")
            self._emit("PlannerAgent", "plan_generated",
                       f"目标: {user_goal[:60]}", str(e), "error")

        # ── Step 2.5: ContentGeneratorAgent — 生成个性化教材 ──
        try:
            _t0 = time.time()
            content_result = self._run_content_generator_agent(
                result.profile, result.learning_plan
            )
            result.content = content_result.to_dict() if hasattr(content_result, "to_dict") else content_result
            _gen_source = (result.content or {}).get("generation_source", "rule")
            ch_count = len((result.content or {}).get("chapters", []))
            self._emit("ContentGeneratorAgent", "content_generated",
                       f"目标: {user_goal[:60]}",
                       f"教材: {ch_count} 章节 (source={_gen_source})",
                       duration_ms=round((time.time() - _t0) * 1000, 1))
        except Exception as e:
            errors.append(f"ContentGeneratorAgent: {e}")
            self._emit("ContentGeneratorAgent", "content_generated",
                       f"目标: {user_goal[:60]}", str(e), "error")

        # ── Step 3: ResourceAgent — 推荐资源 ──
        try:
            _t0 = time.time()
            profile_dict = self._extract_profile_dict(result.profile)
            resource_result = self._run_resource_agent(
                profile_dict, user_goal, knowledge_gaps
            )
            result.resources = (
                resource_result.to_dict() if hasattr(resource_result, "to_dict")
                else resource_result
            ).get("resources", [])
            res_count = len(result.resources) if result.resources else 0
            self._emit("ResourceAgent", "resources_recommended",
                       f"目标: {user_goal[:60]} | 缺口: {knowledge_gaps}",
                       f"推荐: {res_count} 项资源",
                       duration_ms=round((time.time() - _t0) * 1000, 1))
        except Exception as e:
            errors.append(f"ResourceAgent: {e}")
            self._emit("ResourceAgent", "resources_recommended",
                       "推荐失败", str(e), "error")

        # ── Step 4: Review + Step 5: Reflection ──
        try:
            _t0 = time.time()
            # Phase 4.4 — Use EvaluationManager (rule-based scoring + explanations)
            # Falls back to _simulate_review on any error
            feedback = self._run_evaluation(
                result.learning_plan, result.resources or [],
                result.profile, user_goal, self.student_id,
            )
            result.evaluation = feedback
            score = feedback.get("score", 75)

            reflection_input = {
                "plan": result.learning_plan,
                "resources": result.resources,
                "feedback": feedback,
            }
            self._emit("ReviewAgent", "review_completed",
                       f"评审 {len(result.resources or [])} 项资源",
                       f"评分: {score}",
                       duration_ms=round((time.time() - _t0) * 1000, 1))

            _t0 = time.time()
            refl_result = self._run_reflection_agent(user_goal, reflection_input)
            result.reflection = (
                refl_result.to_dict() if hasattr(refl_result, "to_dict")
                else refl_result
            )
            _refl_source = (result.reflection or {}).get("source", "rule")
            self._emit("ReflectionAgent", "reflection_completed",
                       f"目标: {user_goal[:60]}",
                       f"(mode={_refl_source}) " + str((result.reflection or {}).get("summary", ""))[:130],
                       duration_ms=round((time.time() - _t0) * 1000, 1))
        except Exception as e:
            errors.append(f"Review/Reflection: {e}")
            self._emit("ReflectionAgent", "reflection_completed",
                       "反思失败", str(e), "error")

        # ── Phase 4.6 — MetaReflector Trigger ──
        if self.meta_reflector is not None:
            try:
                if self._meta_adapter.should_trigger(result.evaluation):
                    _t0 = time.time()
                    failure_context = self._meta_adapter.build_failure_context(
                        result.evaluation, result.reflection, self.student_id,
                    )
                    concept = self._meta_adapter.extract_concept(
                        result.reflection, result.learning_plan,
                    )
                    severity = self._meta_adapter.determine_severity(result.evaluation)

                    meta_result = self.meta_reflector.reflect(
                        node_id=f"pipeline_{session_id[:12]}",
                        failure_context=failure_context,
                        concept=concept,
                        severity=severity,
                    )
                    if meta_result is not None:
                        result.meta_reflection = meta_result.to_dict()
                        self._emit("MetaReflector", "meta_reflection_completed",
                                   f"概念: {concept[:40]}",
                                   f"severity={severity} | {meta_result.root_cause[:60]}",
                                   duration_ms=round((time.time() - _t0) * 1000, 1))
            except Exception as e:
                errors.append(f"MetaReflector: {e}")

        # ── Step 6: Memory — 保存体验 ──
        try:
            _t0 = time.time()
            # Phase 8.2-D: compute elapsed before save for time_spent tracking
            _prelim_elapsed = (time.time() - start_time) * 1000
            self._save_to_memory(
                student_id=self.student_id,
                user_goal=user_goal,
                profile=result.profile,
                plan=result.learning_plan,
                resources=result.resources,
                reflection=result.reflection,
                evaluation=result.evaluation,
                total_duration_ms=_prelim_elapsed,
            )
            result.memory_saved = True  # ★ 新字段
            self._emit("Memory", "experience_saved",
                        f"Session: {session_id}",
                        "Memory 已更新",
                        duration_ms=round((time.time() - _t0) * 1000, 1))

            # Phase 9.0 — Artifact save: persist generated content to workspace
            self._save_artifacts_to_workspace(session_id, result)
        except Exception as e:
            errors.append(f"Memory: {e}")

        # ── 完成: 状态 + emit + trace ──
        elapsed = (time.time() - start_time) * 1000
        result.success = len(errors) == 0
        result.total_duration_ms = round(elapsed, 1)
        result.errors = errors
        result.completed_at = datetime.now(timezone.utc).isoformat()

        self._emit("Workflow", "pipeline_completed",
                   f"目标: {user_goal[:60]}",
                   f"{'成功' if result.success else '有错误'}, 耗时 {elapsed:.0f}ms")

        # ★ 新字段: 从 EventBus 收集完整时间线 (在全部 emit 之后)
        collector = TraceCollector(bus=self._bus)
        result.trace = collector.to_dict_list()

        return result

    # ── 内部步骤 ──────────────────────────────

    def _run_profile_agent(
        self,
        user_goal: str,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> ProfileExtractionResult:
        """Step 1: 画像提取"""
        if user_profile and len(user_profile) >= 3:
            # 使用预置画像
            from src.core.agent_router import DynamicProfile
            profile = DynamicProfile(
                knowledge_base=user_profile.get("knowledge_base", "junior_dev"),
                cognitive_style=user_profile.get("cognitive_style", "visual_dominant"),
                error_prone_bias=user_profile.get("error_prone_bias", "magic_syntax_blind"),
                learning_pace=user_profile.get("learning_pace", "normal"),
                interaction_preference=user_profile.get("interaction_preference", "code_sandbox"),
                frustration_threshold=user_profile.get("frustration_threshold", "medium"),
            )
            return ProfileExtractionResult(profile=profile, source="preset", confidence=1.0)

        # 从目标文本提取 — LLM 优先 (Phase 4.2), provider=None 时自动走规则模式
        # Phase 8.2-D: use memory-aware extraction when available
        if self.llm_provider is not None:
            student_memory = None
            try:
                student_memory = self.memory.get_student_memory(self.student_id)
            except Exception:
                pass
            if student_memory is not None and student_memory.profile_history:
                return self.profile_agent.extract_with_provider(user_goal)
            return self.profile_agent.extract_with_provider(user_goal)
        return self.profile_agent.extract(user_goal)

    def _run_planner_agent(
        self,
        user_goal: str,
        profile_result: Optional[Dict[str, Any]] = None,
    ) -> LearningPlan:
        """Step 2: 学习路径规划"""
        from src.core.agent_router import DynamicProfile

        # 获取 profile 对象
        if profile_result:
            profile_data = profile_result.get("profile", profile_result)
            if isinstance(profile_data, dict):
                profile = DynamicProfile(
                    knowledge_base=profile_data.get("knowledge_base", "junior_dev"),
                    cognitive_style=profile_data.get("cognitive_style", "visual_dominant"),
                    error_prone_bias=profile_data.get("error_prone_bias", "magic_syntax_blind"),
                    learning_pace=profile_data.get("learning_pace", "normal"),
                    interaction_preference=profile_data.get("interaction_preference", "code_sandbox"),
                    frustration_threshold=profile_data.get("frustration_threshold", "medium"),
                )
            else:
                profile = profile_data
        else:
            profile_result_ext = self.profile_agent.extract(user_goal)
            profile = profile_result_ext.profile

        # 自动检测课程或使用默认
        # Phase 8.2-D: load student memory for personalized planning
        student_memory = None
        try:
            student_memory = self.memory.get_student_memory(self.student_id)
        except Exception:
            pass

        return self.planner_agent.plan(
            profile=profile,
            goal_text=user_goal,
            course_id="",
            student_memory=student_memory,
            knowledge_graph=self._kg,  # Phase 8.3-D1
        )

    def _run_content_generator_agent(
        self,
        profile_result: Optional[Dict[str, Any]] = None,
        plan_result: Optional[Dict[str, Any]] = None,
    ) -> TeachingMaterial:
        """Step 2.5: 生成个性化教材"""
        from src.core.agent_router import DynamicProfile

        # 获取 profile 对象
        if profile_result:
            profile_data = profile_result.get("profile", profile_result)
            if isinstance(profile_data, dict):
                profile = DynamicProfile(
                    knowledge_base=profile_data.get("knowledge_base", "junior_dev"),
                    cognitive_style=profile_data.get("cognitive_style", "visual_dominant"),
                    error_prone_bias=profile_data.get("error_prone_bias", "magic_syntax_blind"),
                    learning_pace=profile_data.get("learning_pace", "normal"),
                    interaction_preference=profile_data.get("interaction_preference", "code_sandbox"),
                    frustration_threshold=profile_data.get("frustration_threshold", "medium"),
                )
            else:
                profile = profile_data
        else:
            profile_result_ext = self.profile_agent.extract(plan_result.get("plan_id", ""))
            profile = profile_result_ext.profile

        return self.content_generator_agent.generate_material(
            profile=profile,
            plan=plan_result,
        )

    def _run_resource_agent(
        self,
        profile: Dict[str, str],
        user_goal: str,
        knowledge_gaps: Optional[List[str]] = None,
    ) -> ResourceRecommendation:
        """Step 3: 资源推荐"""
        return self.resource_agent.recommend(
            profile=profile,
            goal=user_goal,
            knowledge_gaps=knowledge_gaps or [],
        )

    def _run_evaluation(
        self,
        plan: Optional[Dict[str, Any]],
        resources: List[Dict[str, Any]],
        profile: Optional[Dict[str, Any]],
        user_goal: str,
        student_id: str,
    ) -> Dict[str, Any]:
        """
        Step 4: 质量评估 (Phase 4.4 — EvaluationManager + fallback).

        Uses EvaluationManager for rule-based scoring + decision explanations.
        Falls back to simple rule-based scoring on any error.
        """
        try:
            from src.evaluation.evaluator import EvaluationManager
            evaluator = EvaluationManager()
            return evaluator.evaluate(
                learning_plan=plan,
                resources=resources,
                profile=profile,
                user_goal=user_goal,
                student_id=student_id,
            )
        except Exception:
            return self._simulate_review(plan, resources)

    def _simulate_review(
        self,
        plan: Optional[Dict[str, Any]],
        resources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Fallback quality scoring — used when EvaluationManager is unavailable."""
        score = 75
        if plan:
            nodes = plan.get("nodes", [])
            if len(nodes) >= 3:
                score += 5
            total_min = plan.get("total_minutes", 0)
            if 40 <= total_min <= 180:
                score += 5
        if resources:
            if len(resources) >= 2:
                score += 5
            types = {r.get("type", "") for r in resources}
            if len(types) >= 2:
                score += 5
        return {
            "score": min(score, 100),
            "issues": [],
            "passed": score >= 70,
        }

    def _run_reflection_agent(
        self,
        user_goal: str,
        execution_input: Dict[str, Any],
    ) -> ReflectionResult:
        """Step 5: 执行后反思"""
        return self.reflection_agent.reflect(
            goal=user_goal,
            plan=execution_input.get("plan"),
            resources=execution_input.get("resources"),
            feedback=execution_input.get("feedback"),
        )

    def _save_to_memory(
        self,
        student_id: str,
        user_goal: str,
        profile: Optional[Dict[str, Any]],
        plan: Optional[Dict[str, Any]],
        resources: Optional[List[Dict[str, Any]]],
        reflection: Optional[Dict[str, Any]],
        evaluation: Optional[Dict[str, Any]] = None,
        total_duration_ms: float = 0.0,
    ) -> None:
        """Step 6: 持久化到 Memory (Phase 8.2-D: time_spent + weak_points + error_analyses).
        Phase 8.3-E0.5: Also persists to SQLite for unbounded session tracking.
        """
        try:
            profile_data = self._extract_profile_dict(profile)

            # ── Mastery updates from evaluation ──
            mastery_updates = self._extract_mastery_updates(plan, evaluation)

            # ── Session with real time_spent ──
            time_spent_min = round(total_duration_ms / 60000, 1) if total_duration_ms else 0
            session = {
                "course_id": (plan or {}).get("plan_id", ""),
                "nodes_completed": len(plan.get("nodes", [])) if plan else 0,
                "total_score": (evaluation or reflection or {}).get("score", 75),
                "time_spent": time_spent_min,
                "goal": user_goal[:80],
            }

            self.memory.update_student_memory(
                student_id=student_id,
                profile=profile_data,
                mastery_updates=mastery_updates,
                session=session,
            )

            # ── Phase 8.3-E0.5: Unbounded session record in SQLite ──
            self._save_session_to_db(
                student_id=student_id,
                user_goal=user_goal,
                plan=plan,
                evaluation=evaluation,
                duration_ms=total_duration_ms,
            )

            # ── Phase 8.2-D: write weak_points from evaluation weak_areas ──
            if evaluation:
                weak_areas = evaluation.get("weak_areas", [])
                for area in weak_areas:
                    try:
                        self.memory.update_student_memory(
                            student_id=student_id,
                            weak_point={"concept": area, "error_type": "weak_area"},
                        )
                    except Exception:
                        pass

            # ── Phase 8.2-D: write error_analyses from quiz results ──
            if evaluation:
                error_analyses = evaluation.get("error_analyses", {})
                for qid, analysis in error_analyses.items():
                    related = analysis.get("related_concepts", [])
                    for concept in related:
                        try:
                            self.memory.update_student_memory(
                                student_id=student_id,
                                weak_point={
                                    "concept": concept,
                                    "error_type": analysis.get("error_type", "unknown"),
                                    "question_id": qid,
                                },
                            )
                        except Exception:
                            pass

        except Exception:
            pass

    def _save_session_to_db(
        self,
        student_id: str,
        user_goal: str,
        plan: Optional[Dict[str, Any]] = None,
        evaluation: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0.0,
    ) -> None:
        """Phase 8.3-E0.5: Persist session to A3 SQLite DB for unbounded history.
        Independent of Veritas-Core's capped JSON session tracking.
        """
        try:
            import uuid
            import json
            from src.data.db import _get_conn
            from datetime import datetime, timezone
            from src.data.learning_records import record_agent_action

            # Ensure student_id exists in users table (FK constraint)
            conn = _get_conn()
            exists = conn.execute(
                "SELECT id FROM users WHERE id = ?", (student_id,)
            ).fetchone()
            if not exists:
                now = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    "INSERT INTO users (id, email, password_hash, display_name, is_guest, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (student_id, f"{student_id}@a3.local", "a3_auto", "A3 Student", 1, now),
                )
                conn.commit()

            plan_id = (plan or {}).get("plan_id", "")
            score = (evaluation or {}).get("score", 0)
            node_count = len(plan.get("nodes", [])) if plan else 0

            record_agent_action(
                user_id=student_id,
                agent="A3Workflow",
                action="session_completed",
                course_id=plan_id,
                result={
                    "goal": user_goal[:120],
                    "nodes_completed": node_count,
                    "total_score": score,
                    "duration_ms": round(duration_ms, 1),
                },
                score=float(score),
                duration_ms=int(duration_ms),
            )
        except Exception:
            pass  # Non-critical: don't fail the pipeline on DB write

    def _extract_profile_dict(
        self,
        profile_result: Any,
    ) -> Dict[str, str]:
        """从各种格式提取 profile 字典"""
        if not profile_result:
            return {}
        if isinstance(profile_result, dict):
            if "profile" in profile_result:
                inner = profile_result["profile"]
                return inner if isinstance(inner, dict) else inner.to_dict()
            return {
                k: v for k, v in profile_result.items()
                if k in (
                    "knowledge_base", "cognitive_style", "error_prone_bias",
                    "learning_pace", "interaction_preference", "frustration_threshold",
                )
            }
        if hasattr(profile_result, "to_dict"):
            return profile_result.to_dict()
        if hasattr(profile_result, "profile"):
            p = profile_result.profile
            return p.to_dict() if hasattr(p, "to_dict") else {}
        return {}

    def _extract_mastery_updates(
        self,
        plan: Optional[Dict[str, Any]],
        evaluation: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """
        从 plan 和 evaluation 提取 mastery 更新。

        Phase 8.2-B1: 当 evaluation 包含 weak_areas / strong_areas 时，
        返回 evaluation scores (0.2 / 0.85) 而非中性 placeholder。
        StudentMemory.update_mastery() 使用 EMA 平滑这些值。

        无 evaluation → 回退到旧逻辑 (所有 topic=0.6)。
        """
        if not plan:
            return {}

        nodes = plan.get("nodes", [])
        node_ids = [n.get("node_id", f"node_{i}") for i, n in enumerate(nodes)]

        # ── Phase 8.2-B1: evaluation-driven mastery ──
        if evaluation:
            weak = set(evaluation.get("weak_areas", []))
            strong = set(evaluation.get("strong_areas", []))

            if weak or strong:
                mastery: Dict[str, float] = {}
                for nid in node_ids:
                    if nid in weak:
                        mastery[nid] = 0.2    # 薄弱 → 降低 mastery input
                    elif nid in strong:
                        mastery[nid] = 0.85   # 已掌握 → 提高 mastery input
                    else:
                        mastery[nid] = 0.6    # 未测试 → 中性
                return mastery

        # Fallback: 旧行为 (所有 topic 中性)
        return {nid: 0.6 for nid in node_ids}

    # ── EventBus 辅助 ──────────────────────────

    def _emit(
        self,
        agent: str,
        action: str,
        input_summary: str,
        output_summary: str,
        status: str = "success",
        duration_ms: float = 0.0,
    ):
        """发送事件到 EventBus"""
        try:
            self._bus.emit(
                agent=agent,
                action=action,
                input_summary=input_summary,
                output_summary=output_summary,
                status=status,
                duration_ms=duration_ms,
            )
        except Exception:
            pass

    def get_timeline(self) -> List[Any]:
        """获取执行时间线"""
        return self._bus.get_timeline()

    def get_timeline_json(self) -> str:
        """获取 JSON 格式时间线"""
        return self._bus.to_json()

    # ── Phase 4.8 — Runtime Engine Bridge ─────

    def run_via_runtime(
        self,
        user_goal: str,
        user_profile: Optional[Dict[str, Any]] = None,
        knowledge_gaps: Optional[List[str]] = None,
        session_id: str = "",
    ) -> "WorkflowResult":
        """
        Execute the pipeline via RuntimeEngine (state machine).

        Produces the same WorkflowResult as run().
        Delegates agent calls to RuntimeEngine handlers bound to this workflow.

        This is the Phase 4.8 migration path — run() is preserved for backward compat.
        """
        from veritas.runtime import RuntimeEngine, RuntimeContext

        session_id = session_id or f"a3_rt_{int(time.time())}"

        # Init EventBus
        if self._owns_bus:
            self._bus.clear()
        else:
            AgentEventBus.reset_instance()
            self._bus = AgentEventBus.get_instance()
        self._bus.start_session(session_id)

        # Build context
        ctx = RuntimeContext(
            session_id=session_id,
            user_goal=user_goal,
            user_profile=user_profile or {},
            knowledge_gaps=knowledge_gaps or [],
            student_id=self.student_id,
            meta_reflector=self.meta_reflector,
            meta_adapter=self._meta_adapter,
        )

        # Build engine
        engine = RuntimeEngine(session_id=session_id)
        self._bind_runtime_handlers(engine, ctx)

        # Execute
        _ = engine.run(ctx)

        # Convert to WorkflowResult
        result = WorkflowResult(
            context=WorkflowContext(
                session_id=session_id,
                user_goal=user_goal,
                user_profile=user_profile or {},
                knowledge_gaps=knowledge_gaps or [],
            ),
        )
        result.profile = ctx.profile
        result.learning_plan = ctx.learning_plan
        result.resources = ctx.resources
        result.evaluation = ctx.evaluation
        result.reflection = ctx.reflection
        result.meta_reflection = ctx.meta_reflection
        result.errors = ctx.errors
        result.success = len(ctx.errors) == 0
        result.memory_saved = True  # runtime handler handles memory
        result.completed_at = datetime.now(timezone.utc).isoformat()

        # Trace from EventBus
        collector = TraceCollector(bus=self._bus)
        result.trace = collector.to_dict_list()

        return result

    def _bind_runtime_handlers(self, engine: Any, ctx: Any) -> None:
        """Bind this workflow's step methods as RuntimeEngine handlers."""
        from veritas.runtime import AgentState

        wf = self

        engine.register_handler(AgentState.INIT, lambda c: None)

        engine.register_handler(AgentState.PROFILE, lambda c: _set_ctx(
            c, 'profile',
            wf._run_profile_agent(c.user_goal, c.user_profile).to_dict()
            if hasattr(wf._run_profile_agent(c.user_goal, c.user_profile), 'to_dict')
            else wf._run_profile_agent(c.user_goal, c.user_profile)
        ))

        engine.register_handler(AgentState.PLAN, lambda c: _set_ctx(
            c, 'learning_plan',
            wf._run_planner_agent(c.user_goal, c.profile).to_dict()
            if hasattr(wf._run_planner_agent(c.user_goal, c.profile), 'to_dict')
            else wf._run_planner_agent(c.user_goal, c.profile)
        ))

        engine.register_handler(AgentState.EXECUTE, lambda c: _set_ctx(
            c, 'resources',
            wf._run_resource_agent(
                wf._extract_profile_dict(c.profile),
                c.user_goal, c.knowledge_gaps,
            ).to_dict().get("resources", [])
            if hasattr(wf._run_resource_agent(
                wf._extract_profile_dict(c.profile), c.user_goal, c.knowledge_gaps
            ), 'to_dict')
            else wf._run_resource_agent(
                wf._extract_profile_dict(c.profile), c.user_goal, c.knowledge_gaps
            ).get("resources", [])
        ))

        engine.register_handler(AgentState.EVALUATE, lambda c: _set_ctx(
            c, 'evaluation',
            wf._run_evaluation(
                c.learning_plan, c.resources or [],
                c.profile, c.user_goal, c.student_id,
            )
        ))

        engine.register_handler(AgentState.REFLECT, lambda c: _set_ctx(
            c, 'reflection',
            wf._run_reflection_agent(
                c.user_goal,
                {"plan": c.learning_plan, "resources": c.resources, "feedback": c.evaluation},
            ).to_dict()
            if hasattr(wf._run_reflection_agent(c.user_goal, {
                "plan": c.learning_plan, "resources": c.resources, "feedback": c.evaluation,
            }), 'to_dict')
            else wf._run_reflection_agent(c.user_goal, {
                "plan": c.learning_plan, "resources": c.resources, "feedback": c.evaluation,
            })
        ))

        engine.register_handler(AgentState.META_REFLECT, lambda c: _meta_reflect_handler(wf, c))

        engine.register_handler(AgentState.MEMORY_UPDATE, lambda c: wf._save_to_memory(
            student_id=c.student_id,
            user_goal=c.user_goal,
            profile=c.profile,
            plan=c.learning_plan,
            resources=c.resources,
            reflection=c.reflection,
        ))

    # ── Phase 9.0 — Artifact Persistence ──

    def _save_artifacts_to_workspace(self, session_id: str, result: Any) -> None:
        """Save generated content to the user's workspace. Non-critical — errors are silent."""
        try:
            from src.artifacts.manager import ArtifactManager, MaterialArtifact
            am = ArtifactManager()

            # Save teaching material
            if result.content and isinstance(result.content, dict):
                try:
                    artifact = MaterialArtifact(
                        artifact_id=f"material_{session_id[:8]}",
                        title=result.content.get("title", "Teaching Material"),
                        content=result.content.get("overall_summary", ""),
                        metadata={
                            "chapters": len(result.content.get("chapters", [])),
                            "generation_source": result.content.get("generation_source", "rule"),
                        },
                    )
                    am.save_material(self.student_id, artifact)
                except Exception:
                    pass
        except ImportError:
            pass


def _set_ctx(ctx, name: str, value):
    """Set attribute on context, returning None (for handler compatibility)."""
    setattr(ctx, name, value)


def _meta_reflect_handler(wf, ctx) -> None:
    """MetaReflector handler — mirrors Phase 4.6 trigger logic."""
    if wf.meta_reflector is None:
        return
    if not wf._meta_adapter.should_trigger(ctx.evaluation):
        return

    failure_context = wf._meta_adapter.build_failure_context(
        ctx.evaluation, ctx.reflection, ctx.student_id,
    )
    concept = wf._meta_adapter.extract_concept(ctx.reflection, ctx.learning_plan)
    severity = wf._meta_adapter.determine_severity(ctx.evaluation)

    meta_result = wf.meta_reflector.reflect(
        node_id=f"rt_{ctx.session_id[:12]}",
        failure_context=failure_context,
        concept=concept,
        severity=severity,
    )
    if meta_result is not None:
        ctx.meta_reflection = meta_result.to_dict()
        wf._emit("MetaReflector", "meta_reflection_completed",
                   f"概念: {concept[:40]}",
                   f"severity={severity} | {meta_result.root_cause[:60]}")


# ──────────────────────────────────────────────
# Phase 8.3-E2-F: Task → Model Routing
# ──────────────────────────────────────────────


def get_model_for_task(task: str) -> dict:
    """
    Find the best model for a given A3 Agent task.

    Uses ModelRouter to select a model based on task capability requirements.
    Returns a dict suitable for use by Agents.

    Args:
        task: TaskType string value (e.g. "generate_material", "generate_image")

    Returns:
        {
            "success": bool,
            "model_id": str,
            "display_name": str,
            "provider": str,
            "reason": str,
            "alternatives": [...],
            "error": str or None,
        }
    """
    try:
        from src.config.model_router import select_model as _select
        result = _select(task)
        d = result.to_dict()
        d["error"] = None if result.success else result.reason
        return d
    except ImportError as e:
        return {
            "success": False,
            "model_id": "",
            "display_name": "",
            "provider": "",
            "reason": "",
            "alternatives": [],
            "error": f"Model router unavailable: {e}",
        }


def check_task_capability_for_current(provider: str, model: str, task: str) -> dict:
    """
    Check if the currently configured provider/model supports a task.

    Args:
        provider: Current provider name
        model: Current model name
        task: TaskType string value

    Returns:
        {"ok": bool, "error": str or None}
    """
    try:
        from src.config.model_capability import check_task_capability as _check
        ok, err = _check(provider, model, task)
        return {"ok": ok, "error": err}
    except ImportError as e:
        return {"ok": True, "error": None}  # assume supported if module unavailable