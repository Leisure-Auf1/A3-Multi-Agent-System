#!/usr/bin/env python3
"""
A3 Multi-Agent Pipeline Demo

运行:
    python examples/full_pipeline_demo.py

演示从用户意图到个性化执行的多 Agent 协作全流程:
  User Goal → ProfileAgent → PlannerAgent → ResourceAgent → ReviewAgent → ReflectionAgent → Memory
"""

import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_separator(title: str = ""):
    """打印分隔线"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    else:
        print("-" * 60)


def demo_basic_pipeline():
    """基础管道演示"""
    print_separator("A3 Multi-Agent Demo")
    print()
    print("User Goal:")
    print("  Learn Python Network Programming")
    print()

    from src.workflow import A3Workflow
    from src.core.event_trace import TraceCollector

    # 创建工作流
    workflow = A3Workflow(student_id="demo_user_001")

    # 执行
    print_separator()
    print("[ProfileAgent]")
    print("  Analyzing learner profile...")

    print("\n[PlannerAgent]")
    print("  Generating personalized learning path...")

    print("\n[ResourceAgent]")
    print("  Finding matching resources...")

    print("\n[ConversationAgent]")
    print("  Creating explanation content...")

    print("\n[ReviewAgent]")
    print("  Evaluating quality...")

    print("\n[Memory]")
    print("  Saving learning experience...")

    # 实际执行
    result = workflow.run(
        user_goal="Learn Python Network Programming",
        user_profile={
            "knowledge_base": "junior_dev",
            "cognitive_style": "visual_dominant",
            "learning_pace": "normal",
            "interaction_preference": "code_sandbox",
            "frustration_threshold": "medium",
        },
        knowledge_gaps=["socket", "HTTP", "asyncio"],
    )

    print_separator()
    print("Pipeline Execution Complete")
    print()

    # Profile
    if result.profile:
        profile_data = result.profile.get("profile", result.profile)
        if hasattr(profile_data, "to_dict"):
            profile_data = profile_data.to_dict()
        print("📋 Profile:")
        for k, v in profile_data.items():
            print(f"    {k}: {v}")

    # Plan
    if result.plan:
        nodes = result.plan.get("nodes", [])
        print(f"\n🗺️  Learning Plan: {len(nodes)} nodes, "
              f"{result.plan.get('total_minutes', 0)} min")
        for n in nodes[:5]:
            print(f"    [{n.get('node_id')}] {n.get('title')} "
                  f"({n.get('estimated_minutes')}min, depth={n.get('depth')})")

    # Resources
    if result.resources:
        print(f"\n📚 Resources: {len(result.resources)} items")
        for r in result.resources[:5]:
            print(f"    [{r.get('type')}] {r.get('title')} "
                  f"({r.get('difficulty')}, {r.get('estimated_minutes')}min)")
            print(f"        → {r.get('reason', '')[:80]}")

    # Reflection
    if result.reflection:
        ref = result.reflection
        print(f"\n🔍 Reflection:")
        print(f"    Success: {ref.get('success')}")
        print(f"    Score: {ref.get('score')}/100")
        print(f"    Summary: {ref.get('summary', '')[:120]}")

    # ★ Evaluation (new unified field)
    if result.evaluation:
        ev = result.evaluation
        print(f"\n📊 Evaluation:")
        print(f"    Score: {ev.get('score')}/100")
        print(f"    Passed: {ev.get('passed')}")

    # ★ Memory Saved (new unified field)
    print(f"\n💾 Memory Saved: {'✅ Yes' if result.memory_saved else '❌ No'}")

    # ★ Timeline (from result.trace — unified)
    print_separator("Execution Timeline (from result.trace)")
    if result.trace:
        for t in result.trace[:12]:
            mark = "✓" if t["status"] == "success" else "✗"
            print(f"  {mark} [{t['agent']:<15s}] {t['action']:<22s}"
                  f" → {t['output'][:60]}")

    print_separator()
    print(f"Status: {'✅ SUCCESS' if result.success else '⚠️  WITH ERRORS'}")
    print(f"Duration: {result.total_duration_ms:.1f}ms")
    if result.errors:
        print(f"Errors: {result.errors}")
    print(f"Session: {result.context.session_id}")
    print_separator("Completed")

    return result


def demo_with_knowledge_gaps():
    """带知识缺口的演示"""
    print_separator("A3 Multi-Agent Demo — Knowledge Gap Focus")

    from src.workflow import A3Workflow

    workflow = A3Workflow(student_id="demo_user_002")

    result = workflow.run(
        user_goal="学习异步网络编程和 WebSocket 实时通信",
        user_profile={
            "knowledge_base": "mid_level",
            "cognitive_style": "text_linear",
            "learning_pace": "deep_dive",
            "interaction_preference": "code_sandbox",
            "frustration_threshold": "high",
        },
        knowledge_gaps=["asyncio", "websocket", "coroutine", "event_loop"],
    )

    print(f"\n📋 Profile: {result.profile.get('profile', result.profile)}")
    print(f"🗺️  Plan: {result.plan.get('total_minutes', 0)} min, "
          f"{len(result.plan.get('nodes', []))} nodes")
    print(f"📚 Resources: {len(result.resources or [])} items")
    print(f"🔍 Reflection Score: {result.reflection.get('score', 0)}/100")
    print(f"⏱️  Duration: {result.total_duration_ms:.1f}ms")

    return result


def demo_event_trace_standalone():
    """独立 EventTrace 演示"""
    print_separator("EventTrace Standalone Demo")

    from src.core.event_trace import create_event_trace, get_execution_timeline
    from src.core.event_bus import AgentEventBus

    # 重置总线
    AgentEventBus.reset_instance()
    bus = AgentEventBus.get_instance()
    bus.start_session("trace_demo")

    # 模拟一系列 Agent 事件
    events = [
        ("ProfileAgent", "extract_profile", "学生: 零基础学Python",
         "画像: junior_dev / visual / normal"),
        ("PlannerAgent", "generate_plan", "目标: Python基础",
         "路径: 4节点, 90min"),
        ("ResourceAgent", "recommend_resources", "缺口: socket, asyncio",
         "资源: 5项 (doc×2, video×1, exercise×2)"),
        ("ContentAgent", "generate_content", "节点: var_types",
         "内容: 讲解+练习+图解"),
        ("ReviewAgent", "evaluate_quality", "评审 5项资源",
         "评分: 85/100 ✅"),
        ("ReflectionAgent", "reflect", "总结执行结果",
         "成功 ✅ 建议: 增加练习量"),
        ("Memory", "save_experience", "Session: demo_001",
         "Memory 已更新"),
    ]

    for agent, action, inp, out in events:
        create_event_trace(agent, action, inp, out)

    # 输出时间线
    print("\nExecution Timeline:")
    print(get_execution_timeline())

    print_separator()


def demo_advanced_pipeline():
    """高级管道演示：自动画像提取 + 课程检测"""
    print_separator("Advanced: Auto-Profile + Course Detection")

    from src.workflow import A3Workflow
    from src.core.event_trace import TraceCollector

    workflow = A3Workflow(student_id="auto_detect_user")

    # 仅提供目标文本，自动检测课程
    result = workflow.run(
        user_goal="I want to learn Multi-Agent AI systems and build autonomous agents",
        # 不提供 user_profile，让系统自动提取
        knowledge_gaps=["agent_loop", "tool_calling", "eventbus_arch"],
    )

    print(f"\n自动课程检测: {result.plan.get('metadata', {}).get('course_id', 'unknown')}")
    print(f"节点数: {len(result.plan.get('nodes', []))}")
    print(f"评分: {result.reflection.get('score', 0)}/100")

    collector = TraceCollector()
    print(f"\n事件汇总:")
    summary = collector.get_agent_summary()
    for agent, count in sorted(summary.items()):
        print(f"  {agent}: {count} events")

    return result


if __name__ == "__main__":
    print("\n" + "█" * 60)
    print("█  A3 Multi-Agent Collaboration Pipeline Demo  █")
    print("█" * 60)

    # Demo 1: 基础管道
    demo_basic_pipeline()

    # Demo 2: 知识缺口
    print("\n")
    demo_with_knowledge_gaps()

    # Demo 3: EventTrace 独立演示
    print("\n")
    demo_event_trace_standalone()

    # Demo 4: 高级自动检测
    print("\n")
    demo_advanced_pipeline()

    print("\n" + "█" * 60)
    print("█  All Demos Complete  █")
    print("█" * 60 + "\n")
