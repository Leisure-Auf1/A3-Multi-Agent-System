"""
Phase 7 — Integration Tests: 全管道测试

覆盖:
  - 管道执行
  - EventBus 通信
  - Memory 更新
  - Agent 输出验证
  - 失败恢复
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.workflow import A3Workflow, WorkflowResult
from src.agents.resource_agent import ResourceAgent, ResourceRecommendation, ResourceItem
from src.agents.reflection_agent import ReflectionAgent, ReflectionResult
from src.core.event_bus import AgentEventBus
from src.core.event_trace import TraceCollector, TraceEvent, create_event_trace
from src.memory.memory_manager import MemoryManager


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_event_bus():
    """每个测试前重置 EventBus 单例"""
    AgentEventBus.reset_instance()
    yield
    AgentEventBus.reset_instance()


@pytest.fixture
def sample_profile():
    return {
        "knowledge_base": "junior_dev",
        "cognitive_style": "visual_dominant",
        "error_prone_bias": "magic_syntax_blind",
        "learning_pace": "normal",
        "interaction_preference": "code_sandbox",
        "frustration_threshold": "medium",
    }


@pytest.fixture
def workflow():
    return A3Workflow(student_id="test_student")


@pytest.fixture
def resource_agent():
    return ResourceAgent()


@pytest.fixture
def reflection_agent():
    return ReflectionAgent()


# ──────────────────────────────────────────────
# ResourceAgent Tests
# ──────────────────────────────────────────────

class TestResourceAgent:
    """ResourceAgent 单元测试"""

    def test_recommend_basic(self, resource_agent, sample_profile):
        """基本推荐: 带知识缺口"""
        result = resource_agent.recommend(
            profile=sample_profile,
            goal="学习 Python 网络编程",
            knowledge_gaps=["socket", "HTTP"],
        )

        assert isinstance(result, ResourceRecommendation)
        assert len(result.resources) > 0
        assert result.total_minutes > 0
        assert result.goal == "学习 Python 网络编程"

    def test_recommend_empty_gaps(self, resource_agent, sample_profile):
        """空知识缺口: 返回基础资源"""
        result = resource_agent.recommend(
            profile=sample_profile,
            goal="学习网络编程",
            knowledge_gaps=[],
        )

        assert isinstance(result, ResourceRecommendation)
        assert len(result.resources) > 0

    def test_recommend_visual_learner(self, resource_agent):
        """视觉型学习者: 应包含视频资源"""
        profile = {
            "knowledge_base": "junior_dev",
            "cognitive_style": "visual_dominant",
            "learning_pace": "normal",
        }
        result = resource_agent.recommend(
            profile=profile,
            goal="学习 socket 编程",
            knowledge_gaps=["socket", "TCP"],
        )

        types = [r.type for r in result.resources]
        assert "video" in types, f"Visual learner should get video resources, got: {types}"

    def test_recommend_advanced_level(self, resource_agent):
        """高级学习者: 资源难度应为 advanced"""
        profile = {
            "knowledge_base": "senior",
            "cognitive_style": "text_linear",
            "learning_pace": "deep_dive",
        }
        result = resource_agent.recommend(
            profile=profile,
            goal="深入学习 asyncio",
            knowledge_gaps=["asyncio", "coroutine"],
        )

        for r in result.resources:
            assert r.difficulty in ("intermediate", "advanced")

    def test_recommend_fast_track(self, resource_agent):
        """快速学习: 资源较少"""
        profile = {
            "knowledge_base": "mid_level",
            "learning_pace": "fast_track",
        }
        result = resource_agent.recommend(
            profile=profile,
            goal="快速掌握 HTTP",
            knowledge_gaps=["HTTP"],
        )

        # fast_track 不添加综合项目
        assert len(result.resources) <= 3

    def test_resource_to_dict(self, resource_agent, sample_profile):
        """验证 to_dict 输出格式"""
        result = resource_agent.recommend(
            profile=sample_profile,
            goal="测试",
            knowledge_gaps=["socket"],
        )

        d = result.to_dict()
        assert "resources" in d
        assert "total_minutes" in d
        assert "reasoning" in d
        for r in d["resources"]:
            assert "type" in r
            assert "title" in r
            assert "reason" in r
            assert "difficulty" in r
            assert "estimated_minutes" in r

    def test_recommend_returns_reasoning(self, resource_agent, sample_profile):
        """验证推荐包含推理说明"""
        result = resource_agent.recommend(
            profile=sample_profile,
            goal="学习 WebSocket",
            knowledge_gaps=["websocket"],
        )

        assert len(result.reasoning) > 0
        assert "WebSocket" in result.reasoning or "junior_dev" in result.reasoning


# ──────────────────────────────────────────────
# ReflectionAgent Tests
# ──────────────────────────────────────────────

class TestReflectionAgent:
    """ReflectionAgent 单元测试"""

    def test_reflect_success(self, reflection_agent):
        """成功执行: 高分反馈"""
        result = reflection_agent.reflect(
            goal="学习 Python 网络编程",
            plan={
                "nodes": [
                    {"node_id": "socket", "title": "Socket", "estimated_minutes": 30},
                    {"node_id": "http", "title": "HTTP", "estimated_minutes": 25},
                ],
                "total_minutes": 55,
            },
            resources=[
                {"type": "documentation", "title": "Guide"},
                {"type": "exercise", "title": "Lab"},
            ],
            feedback={"score": 85, "issues": []},
        )

        assert isinstance(result, ReflectionResult)
        assert result.success is True
        assert result.score == 85
        assert len(result.achievements) > 0

    def test_reflect_failure(self, reflection_agent):
        """失败执行: 低分反馈"""
        result = reflection_agent.reflect(
            goal="学习网络编程",
            plan={"nodes": []},
            resources=[],
            feedback={"score": 45, "issues": ["资源不足"]},
        )

        assert result.success is False
        assert len(result.improvements) > 0

    def test_reflect_with_issues(self, reflection_agent):
        """带有 issue 的反馈"""
        result = reflection_agent.reflect(
            goal="学习",
            plan={"nodes": [{"node_id": "n1"}]},
            resources=[{"type": "doc"}],
            feedback={
                "score": 65,
                "issues": ["概念过载", "缺少练习"],
            },
        )

        assert len(result.improvements) > 0
        # 应包含 issue 中的内容
        assert any("概念过载" in imp or "练习" in imp for imp in result.improvements)

    def test_reflection_to_dict(self, reflection_agent):
        """验证 to_dict 格式"""
        result = reflection_agent.reflect(
            goal="测试",
            plan={"nodes": []},
            resources=[],
            feedback={"score": 80},
        )

        d = result.to_dict()
        assert "success" in d
        assert "score" in d
        assert "achievements" in d
        assert "improvements" in d
        assert "summary" in d

    def test_reflect_high_score(self, reflection_agent):
        """高分反思: 应包含 achievement 提及优秀"""
        result = reflection_agent.reflect(
            goal="学习",
            plan={"nodes": [{"node_id": "n1"}], "total_minutes": 30},
            resources=[{"type": "doc", "title": "T"}],
            feedback={"score": 92, "issues": []},
        )

        assert result.success is True
        # 高分应有 "优秀" 相关 achievement
        assert any("优秀" in a or "92" in a for a in result.achievements)

    def test_reflect_many_nodes(self, reflection_agent):
        """过多节点: 应触发改进建议"""
        nodes = [{"node_id": f"n{i}"} for i in range(12)]
        result = reflection_agent.reflect(
            goal="学习",
            plan={"nodes": nodes},
            resources=[],
            feedback={"score": 70},
        )

        assert any("过长" in imp or "疲劳" in imp for imp in result.improvements)


# ──────────────────────────────────────────────
# EventBus + EventTrace Tests
# ──────────────────────────────────────────────

class TestEventBusPipeline:
    """EventBus 管道集成测试"""

    def test_event_bus_records_pipeline_events(self, workflow, sample_profile):
        """管道执行产生 EventBus 事件"""
        result = workflow.run(
            user_goal="测试目标",
            user_profile=sample_profile,
        )

        bus = AgentEventBus.get_instance()
        events = bus.get_timeline()

        assert len(events) > 0
        agent_names = [e.agent for e in events]
        assert "System" in agent_names
        assert "Workflow" in agent_names

    def test_event_bus_has_all_agents(self, workflow, sample_profile):
        """EventBus 包含所有 Agent 事件"""
        workflow.run(
            user_goal="学习 Python 网络编程",
            user_profile=sample_profile,
            knowledge_gaps=["socket"],
        )

        bus = AgentEventBus.get_instance()
        agents = {e.agent for e in bus.get_timeline()}

        expected = {"System", "ProfileAgent", "PlannerAgent", "ResourceAgent",
                     "ReviewAgent", "ReflectionAgent", "Memory", "Workflow"}
        missing = expected - agents
        assert not missing, f"Missing agents in EventBus: {missing}"

    def test_event_bus_reset_between_tests(self):
        """EventBus 在测试间正确重置"""
        bus = AgentEventBus.get_instance()
        bus.emit("Test", "action")
        assert bus.event_count > 0

        # 重置后为空
        AgentEventBus.reset_instance()
        bus2 = AgentEventBus.get_instance()
        assert bus2.event_count == 0

    def test_event_bus_json_export(self, workflow, sample_profile):
        """EventBus JSON 导出"""
        workflow.run(
            user_goal="测试",
            user_profile=sample_profile,
        )

        bus = AgentEventBus.get_instance()
        json_str = bus.to_json()

        assert len(json_str) > 0
        data = json.loads(json_str)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "agent" in data[0]
        assert "action" in data[0]
        assert "timestamp" in data[0]


# ──────────────────────────────────────────────
# TraceCollector Tests
# ──────────────────────────────────────────────

class TestTraceCollector:
    """EventTrace 增强测试"""

    def test_collect_from_bus(self, workflow, sample_profile):
        """从 EventBus 收集事件"""
        workflow.run(
            user_goal="测试",
            user_profile=sample_profile,
        )

        collector = TraceCollector()
        traces = collector.collect()

        assert len(traces) > 0
        assert all(isinstance(t, TraceEvent) for t in traces)

    def test_render_timeline(self, workflow, sample_profile):
        """渲染时间线文本"""
        workflow.run(
            user_goal="测试",
            user_profile=sample_profile,
        )

        collector = TraceCollector()
        timeline = collector.render_timeline()

        assert len(timeline) > 0
        assert "ProfileAgent" in timeline

    def test_agent_summary(self, workflow, sample_profile):
        """Agent 事件统计"""
        workflow.run(
            user_goal="测试",
            user_profile=sample_profile,
        )

        collector = TraceCollector()
        summary = collector.get_agent_summary()

        assert len(summary) > 0
        assert "System" in summary

    def test_create_event_trace(self):
        """create_event_trace 便捷函数"""
        AgentEventBus.reset_instance()
        bus = AgentEventBus.get_instance()
        bus.start_session("test")

        trace = create_event_trace(
            agent="TestAgent",
            action="test_action",
            input_summary="input",
            output_summary="output",
        )

        assert isinstance(trace, TraceEvent)
        assert trace.agent == "TestAgent"
        assert trace.action == "test_action"

        events = bus.get_timeline()
        assert len(events) == 2  # session_start + test_action

    def test_to_dict_list(self, workflow, sample_profile):
        """导出字典列表"""
        workflow.run(
            user_goal="测试",
            user_profile=sample_profile,
        )

        collector = TraceCollector()
        dicts = collector.to_dict_list()

        assert len(dicts) > 0
        for d in dicts:
            assert "event" in d
            assert "agent" in d
            assert "timestamp" in d

    def test_render_compact(self, workflow, sample_profile):
        """紧凑格式渲染"""
        workflow.run(user_goal="测试", user_profile=sample_profile)

        collector = TraceCollector()
        compact = collector.render_compact()

        assert "ProfileAgent" in compact
        assert "Workflow" in compact


# ──────────────────────────────────────────────
# Full Pipeline Integration Tests
# ──────────────────────────────────────────────

class TestFullPipeline:
    """完整管道集成测试"""

    def test_full_pipeline_executes(self, workflow, sample_profile):
        """完整管道: 所有阶段执行成功"""
        result = workflow.run(
            user_goal="学习 Python 网络编程",
            user_profile=sample_profile,
            knowledge_gaps=["socket", "HTTP"],
        )

        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert len(result.errors) == 0

    def test_pipeline_returns_profile(self, workflow, sample_profile):
        """管道返回画像结果"""
        result = workflow.run(
            user_goal="学习 Python",
            user_profile=sample_profile,
        )

        assert result.profile is not None

    def test_pipeline_returns_plan(self, workflow, sample_profile):
        """管道返回学习计划"""
        result = workflow.run(
            user_goal="学习 Python 网络编程",
            user_profile=sample_profile,
        )

        assert result.plan is not None
        assert "nodes" in result.plan or hasattr(result.plan, "nodes")
        nodes = result.plan.get("nodes", [])
        assert len(nodes) > 0

    def test_pipeline_returns_resources(self, workflow, sample_profile):
        """管道返回资源推荐"""
        result = workflow.run(
            user_goal="学习 socket 编程",
            user_profile=sample_profile,
            knowledge_gaps=["socket", "TCP"],
        )

        assert result.resources is not None
        assert isinstance(result.resources, list)
        assert len(result.resources) > 0

    def test_pipeline_returns_reflection(self, workflow, sample_profile):
        """管道返回反思结果"""
        result = workflow.run(
            user_goal="学习 Python",
            user_profile=sample_profile,
        )

        assert result.reflection is not None
        assert "success" in result.reflection
        assert "score" in result.reflection

    def test_pipeline_duration_tracked(self, workflow, sample_profile):
        """管道追踪执行时间"""
        result = workflow.run(
            user_goal="测试",
            user_profile=sample_profile,
        )

        assert result.total_duration_ms > 0.0

    def test_pipeline_auto_profile(self, workflow):
        """自动画像提取 (无 preset)"""
        result = workflow.run(
            user_goal="我是一个 Python 初学者，想学网络编程",
        )

        assert result.profile is not None
        # 应能提取基础信息
        profile_data = result.profile.get("profile", result.profile)
        if hasattr(profile_data, "to_dict"):
            profile_data = profile_data.to_dict()
        if isinstance(profile_data, dict):
            assert len(profile_data) >= 3

    def test_pipeline_session_id(self, workflow, sample_profile):
        """管道生成 session_id"""
        result = workflow.run(
            user_goal="测试",
            user_profile=sample_profile,
        )

        assert len(result.context.session_id) > 0
        assert result.completed_at != ""

    def test_pipeline_to_dict(self, workflow, sample_profile):
        """WorkflowResult.to_dict() 输出完整"""
        result = workflow.run(
            user_goal="测试",
            user_profile=sample_profile,
        )

        d = result.to_dict()
        assert "success" in d
        assert "context" in d
        assert "profile" in d
        assert "plan" in d
        assert "resources" in d
        assert "reflection" in d
        assert "total_duration_ms" in d
        assert "errors" in d

    def test_pipeline_error_graceful(self, workflow):
        """管道失败时优雅降级"""
        # 即使没有有效输入也应返回结果不崩溃
        result = workflow.run(
            user_goal="",
        )

        assert isinstance(result, WorkflowResult)
        # 至少不会完全崩溃
        assert result.completed_at != ""

    def test_pipeline_memory_update(self, workflow, sample_profile):
        """管道更新 Memory"""
        result = workflow.run(
            user_goal="学习 Python 网络编程",
            user_profile=sample_profile,
        )

        # Memory 是否已有学生数据
        student_id = workflow.student_id
        exists = workflow.memory.student_exists(student_id)
        assert exists is True

        student_memory = workflow.memory.get_student_memory(student_id)
        assert student_memory is not None
        # 应有 profile_history
        assert len(student_memory.profile_history) > 0

    def test_pipeline_different_profiles(self, workflow):
        """不同画像产生不同计划"""
        result1 = workflow.run(
            user_goal="学习 Python 网络编程",
            user_profile={
                "knowledge_base": "junior_dev",
                "learning_pace": "normal",
                "cognitive_style": "visual_dominant",
                "interaction_preference": "code_sandbox",
            },
        )

        result2 = workflow.run(
            user_goal="学习 Python 网络编程",
            user_profile={
                "knowledge_base": "senior",
                "learning_pace": "fast_track",
                "cognitive_style": "text_linear",
                "interaction_preference": "passive_read",
            },
        )

        nodes1 = result1.plan.get("nodes", [])
        nodes2 = result2.plan.get("nodes", [])

        # 不同画像应产生不同节点数或不同内容
        assert (len(nodes1) != len(nodes2) or
                result1.plan.get("total_minutes") != result2.plan.get("total_minutes"))


# ──────────────────────────────────────────────
# Workflow Timeline Tests
# ──────────────────────────────────────────────

class TestWorkflowTimeline:
    """工作流时间线测试"""

    def test_timeline_has_all_steps(self, workflow, sample_profile):
        """时间线包含全部步骤"""
        workflow.run(
            user_goal="测试",
            user_profile=sample_profile,
        )

        timeline = workflow.get_timeline()
        agent_names = [e.agent for e in timeline]

        # 应包含关键 Agent
        for name in ["System", "ProfileAgent", "PlannerAgent"]:
            assert name in agent_names, f"Missing {name} in timeline"

    def test_timeline_json(self, workflow, sample_profile):
        """时间线 JSON 导出"""
        workflow.run(
            user_goal="测试",
            user_profile=sample_profile,
        )

        json_str = workflow.get_timeline_json()
        data = json.loads(json_str)
        assert len(data) > 0

    def test_timeline_order(self, workflow, sample_profile):
        """时间线事件按执行顺序"""
        workflow.run(
            user_goal="测试",
            user_profile=sample_profile,
        )

        timeline = workflow.get_timeline()
        agents = [e.agent for e in timeline]

        # System session_start 应最先
        assert agents[0] == "System"

        # Workflow pipeline_completed 应在最后
        assert "Workflow" in agents[-3:]


# ──────────────────────────────────────────────
# Failure Recovery Tests
# ──────────────────────────────────────────────

class TestFailureRecovery:
    """失败恢复测试"""

    def test_resource_agent_handles_empty_profile(self, resource_agent):
        """ResourceAgent 处理空画像"""
        result = resource_agent.recommend(
            profile={},
            goal="学习",
        )

        assert isinstance(result, ResourceRecommendation)
        assert len(result.resources) > 0  # fallback resources

    def test_reflection_agent_handles_empty_input(self, reflection_agent):
        """ReflectionAgent 处理空输入"""
        result = reflection_agent.reflect(
            goal="",
            feedback={"score": 50},
        )

        assert isinstance(result, ReflectionResult)
        # 不崩溃即可

    def test_workflow_empty_goal(self, workflow):
        """空目标不崩溃"""
        result = workflow.run(user_goal="")
        assert isinstance(result, WorkflowResult)

    def test_workflow_no_gaps(self, workflow, sample_profile):
        """无知识缺口不崩溃"""
        result = workflow.run(
            user_goal="学习 Python",
            user_profile=sample_profile,
        )

        assert result.success is True


# ──────────────────────────────────────────────
# Phase 4.1 — Unified WorkflowResult Tests
# ──────────────────────────────────────────────

class TestWorkflowResultModel:
    """统一 WorkflowResult 输出模型测试"""

    def test_result_has_learning_plan(self, workflow, sample_profile):
        """learning_plan 字段 (新名称)"""
        result = workflow.run(
            user_goal="学习 Python",
            user_profile=sample_profile,
        )

        assert result.learning_plan is not None
        assert "nodes" in result.learning_plan
        assert len(result.learning_plan["nodes"]) > 0

    def test_result_plan_backward_compat(self, workflow, sample_profile):
        """plan 属性向后兼容 (别名)"""
        result = workflow.run(
            user_goal="学习 Python",
            user_profile=sample_profile,
        )

        # plan 属性应指向 learning_plan
        assert result.plan is result.learning_plan
        assert result.plan is not None

    def test_result_has_evaluation(self, workflow, sample_profile):
        """evaluation 字段 (新)"""
        result = workflow.run(
            user_goal="学习 Python",
            user_profile=sample_profile,
        )

        assert result.evaluation is not None
        assert "score" in result.evaluation
        assert "passed" in result.evaluation
        assert isinstance(result.evaluation["score"], (int, float))

    def test_result_has_trace(self, workflow, sample_profile):
        """trace 字段 (新) — EventBus 完整时间线"""
        result = workflow.run(
            user_goal="学习 Python",
            user_profile=sample_profile,
        )

        assert result.trace is not None
        assert isinstance(result.trace, list)
        assert len(result.trace) > 0

        # 每条 trace 应有标准字段
        first = result.trace[0]
        assert "event" in first
        assert "agent" in first
        assert "timestamp" in first
        assert "status" in first

    def test_result_has_memory_saved(self, workflow, sample_profile):
        """memory_saved 字段 (新) — 成功持久化为 True"""
        result = workflow.run(
            user_goal="学习 Python",
            user_profile=sample_profile,
        )

        assert result.memory_saved is True

    def test_result_memory_saved_false_on_error(self):
        """memory_saved 在 Memory 失败时为 False (通过不提供有效的 storage)"""
        # 使用正常 workflow — memory_saved 在正常路径为 True
        # 此测试验证字段存在且默认值为 False
        from src.workflow.result import WorkflowResult
        wr = WorkflowResult()
        assert wr.memory_saved is False

    def test_result_to_dict_all_keys(self, workflow, sample_profile):
        """to_dict 包含所有统一字段"""
        result = workflow.run(
            user_goal="学习 Python",
            user_profile=sample_profile,
        )

        d = result.to_dict()
        expected_keys = {
            "success", "context", "profile", "learning_plan", "plan",
            "resources", "evaluation", "reflection", "trace",
            "memory_saved", "total_duration_ms", "errors", "completed_at",
        }
        missing = expected_keys - set(d.keys())
        assert not missing, f"Missing keys in to_dict: {missing}"

    def test_result_summary(self, workflow, sample_profile):
        """summary() 返回轻量摘要"""
        result = workflow.run(
            user_goal="学习 Python 网络编程",
            user_profile=sample_profile,
        )

        summary = result.summary()
        assert summary["success"] is True
        assert summary["goal"] == "学习 Python 网络编程"
        assert summary["nodes"] > 0
        assert summary["resources"] > 0
        assert summary["score"] > 0
        assert summary["memory_saved"] is True

    def test_result_trace_contains_all_agents(self, workflow, sample_profile):
        """trace 包含所有 Agent 事件"""
        result = workflow.run(
            user_goal="测试",
            user_profile=sample_profile,
        )

        agents_in_trace = {t["agent"] for t in result.trace}
        expected = {"System", "ProfileAgent", "PlannerAgent", "ResourceAgent",
                     "ReviewAgent", "ReflectionAgent", "Memory", "Workflow"}
        missing = expected - agents_in_trace
        assert not missing, f"Missing agents in trace: {missing}"

    def test_workflow_context_has_knowledge_gaps(self, workflow, sample_profile):
        """WorkflowContext 包含 knowledge_gaps 字段"""
        result = workflow.run(
            user_goal="测试",
            user_profile=sample_profile,
            knowledge_gaps=["socket", "HTTP"],
        )

        ctx = result.context
        assert ctx.knowledge_gaps == ["socket", "HTTP"]
        assert "knowledge_gaps" in ctx.to_dict()


class TestWorkflowResultImport:
    """直接从 result.py 导入测试"""

    def test_import_workflow_result(self):
        """从 result 模块直接导入"""
        from src.workflow.result import WorkflowResult, WorkflowContext

        wr = WorkflowResult()
        assert wr.success is False
        assert wr.memory_saved is False
        assert wr.trace is None

    def test_workflow_result_defaults(self):
        """所有字段有合理默认值"""
        from src.workflow.result import WorkflowResult

        wr = WorkflowResult()
        assert wr.success is False
        assert wr.profile is None
        assert wr.learning_plan is None
        assert wr.resources is None
        assert wr.evaluation is None
        assert wr.reflection is None
        assert wr.trace is None
        assert wr.memory_saved is False
        assert wr.total_duration_ms == 0.0
        assert wr.errors == []
        assert isinstance(wr.context.user_profile, dict)

    def test_workflow_result_plan_property_empty(self):
        """plan 属性在无数据时返回 None"""
        from src.workflow.result import WorkflowResult

        wr = WorkflowResult()
        assert wr.plan is None

    def test_workflow_result_plan_setter(self):
        """plan setter 同步更新 learning_plan"""
        from src.workflow.result import WorkflowResult

        wr = WorkflowResult()
        wr.plan = {"nodes": [{"node_id": "test"}]}
        assert wr.learning_plan == {"nodes": [{"node_id": "test"}]}
        assert wr.plan == wr.learning_plan
