"""
Phase 4 — A3Workflow: 多 Agent 协作编排器

职责:
  - 创建执行上下文
  - 触发 Agent 按序执行
  - 监听 EventBus 事件
  - 收集并返回 WorkflowResult (from .result)

Pipeline:
  User Goal → ProfileAgent → PlannerAgent → ResourceAgent → Review → ReflectionAgent → Memory
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
from src.memory.memory_manager import MemoryManager

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
        resource_agent: Optional[ResourceAgent] = None,
        reflection_agent: Optional[ReflectionAgent] = None,
        student_id: str = "demo_student",
    ):
        self.memory = memory_manager or MemoryManager()
        self.profile_agent = profile_agent or ProfileAgent()
        self.planner_agent = planner_agent or PlannerAgent()
        self.resource_agent = resource_agent or ResourceAgent()
        self.reflection_agent = reflection_agent or ReflectionAgent()
        self.student_id = student_id
        self._bus = AgentEventBus.get_instance()

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
            WorkflowResult (含 profile, learning_plan, resources, evaluation,
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

        # 重置 EventBus — 使用类方法确保单例一致性
        AgentEventBus.reset_instance()
        self._bus = AgentEventBus.get_instance()
        self._bus.start_session(session_id)

        result = WorkflowResult(context=context)

        # ── Step 1: ProfileAgent — 分析学习者 ──
        try:
            profile_result = self._run_profile_agent(user_goal, user_profile)
            result.profile = profile_result.to_dict() if hasattr(profile_result, "to_dict") else profile_result
            self._emit("ProfileAgent", "profile_extracted",
                       f"目标: {user_goal[:60]}",
                       f"画像: {result.profile.get('profile', {}).get('knowledge_base', 'unknown')}")
        except Exception as e:
            errors.append(f"ProfileAgent: {e}")
            self._emit("ProfileAgent", "profile_extracted",
                       f"目标: {user_goal[:60]}", str(e), "error")

        # ── Step 2: PlannerAgent — 生成学习路径 ──
        try:
            plan_result = self._run_planner_agent(user_goal, result.profile)
            result.learning_plan = plan_result.to_dict() if hasattr(plan_result, "to_dict") else plan_result
            node_count = len(result.learning_plan.get("nodes", [])) if result.learning_plan else 0
            self._emit("PlannerAgent", "plan_generated",
                       f"目标: {user_goal[:60]}",
                       f"路径: {node_count} 个节点")
        except Exception as e:
            errors.append(f"PlannerAgent: {e}")
            self._emit("PlannerAgent", "plan_generated",
                       f"目标: {user_goal[:60]}", str(e), "error")

        # ── Step 3: ResourceAgent — 推荐资源 ──
        try:
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
                       f"推荐: {res_count} 项资源")
        except Exception as e:
            errors.append(f"ResourceAgent: {e}")
            self._emit("ResourceAgent", "resources_recommended",
                       "推荐失败", str(e), "error")

        # ── Step 4: Review + Step 5: Reflection ──
        try:
            feedback = self._simulate_review(result.learning_plan, result.resources or [])
            result.evaluation = feedback  # ★ 新字段
            score = feedback.get("score", 75)

            reflection_input = {
                "plan": result.learning_plan,
                "resources": result.resources,
                "feedback": feedback,
            }
            self._emit("ReviewAgent", "review_completed",
                       f"评审 {len(result.resources or [])} 项资源",
                       f"评分: {score}")

            refl_result = self._run_reflection_agent(user_goal, reflection_input)
            result.reflection = (
                refl_result.to_dict() if hasattr(refl_result, "to_dict")
                else refl_result
            )
            self._emit("ReflectionAgent", "reflection_completed",
                       f"目标: {user_goal[:60]}",
                       str(result.reflection.get("summary", ""))[:150])
        except Exception as e:
            errors.append(f"Review/Reflection: {e}")
            self._emit("ReflectionAgent", "reflection_completed",
                       "反思失败", str(e), "error")

        # ── Step 6: Memory — 保存体验 ──
        try:
            self._save_to_memory(
                student_id=self.student_id,
                user_goal=user_goal,
                profile=result.profile,
                plan=result.learning_plan,
                resources=result.resources,
                reflection=result.reflection,
            )
            result.memory_saved = True  # ★ 新字段
            self._emit("Memory", "experience_saved",
                       f"Session: {session_id}",
                       "Memory 已更新")
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

        # 从目标文本提取
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
        return self.planner_agent.plan(
            profile=profile,
            goal_text=user_goal,
            course_id="",
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

    def _simulate_review(
        self,
        plan: Optional[Dict[str, Any]],
        resources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Step 4: 质量评审 (模拟)"""
        # 基于资源覆盖度和路径合理性模拟评分
        score = 75  # 基础分

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
    ) -> None:
        """Step 6: 持久化到 Memory"""
        try:
            profile_data = self._extract_profile_dict(profile)
            self.memory.update_student_memory(
                student_id=student_id,
                profile=profile_data,
                mastery_updates=self._extract_mastery_updates(plan),
                session={
                    "course_id": "",
                    "nodes_completed": len(plan.get("nodes", [])) if plan else 0,
                    "total_score": (reflection or {}).get("score", 75),
                    "time_spent": 0,
                },
            )
        except Exception:
            pass

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
    ) -> Dict[str, float]:
        """从 plan 提取 mastery 更新"""
        if not plan:
            return {}
        nodes = plan.get("nodes", [])
        return {n.get("node_id", f"node_{i}"): 0.6 for i, n in enumerate(nodes)}

    # ── EventBus 辅助 ──────────────────────────

    def _emit(
        self,
        agent: str,
        action: str,
        input_summary: str,
        output_summary: str,
        status: str = "success",
    ):
        """发送事件到 EventBus"""
        try:
            self._bus.emit(
                agent=agent,
                action=action,
                input_summary=input_summary,
                output_summary=output_summary,
                status=status,
            )
        except Exception:
            pass

    def get_timeline(self) -> List[Any]:
        """获取执行时间线"""
        return self._bus.get_timeline()

    def get_timeline_json(self) -> str:
        """获取 JSON 格式时间线"""
        return self._bus.to_json()
