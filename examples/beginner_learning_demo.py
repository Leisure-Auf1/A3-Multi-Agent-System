#!/usr/bin/env python3
"""
A3 Demo — Beginner Learning Flow

Scenario: "I want to learn Python network programming"

Shows: ProfileAgent → PlannerAgent → ResourceAgent → Learning Plan

Run: python examples/beginner_learning_demo.py
"""
from __future__ import annotations
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 60)
    print("  A3 Demo — Beginner Learning Flow")
    print("=" * 60)
    print()

    # ═══════════════════════════════════════════════════════
    # Step 1: Student input
    # ═══════════════════════════════════════════════════════
    student_text = "I want to learn Python network programming. I know basic Python syntax."
    print(f"📝 Student: \"{student_text}\"")
    print()

    # ═══════════════════════════════════════════════════════
    # Step 2: ProfileAgent — build student profile
    # ═══════════════════════════════════════════════════════
    print("─" * 40)
    print("🔍 ProfileAgent — Analyzing student...")
    from src.agents.profile_agent import ProfileAgent

    profile_agent = ProfileAgent()
    profile_result = profile_agent.extract(student_text)

    profile_dict = profile_result.to_dict() if hasattr(profile_result, 'to_dict') else {}
    print()
    print("📊 Student Profile (6 dimensions):")
    for key, value in profile_dict.items():
        print(f"   {key}: {value}")
    print(f"   Confidence: {getattr(profile_result, 'confidence', 'N/A')}")
    print()

    # ═══════════════════════════════════════════════════════
    # Step 3: PlannerAgent — generate learning path
    # ═══════════════════════════════════════════════════════
    print("─" * 40)
    print("🗺️  PlannerAgent — Generating learning path...")
    from src.agents.planner_agent import PlannerAgent

    planner = PlannerAgent()
    plan = planner.plan(profile=profile_dict, goal_text="Learn Python network programming")

    topic = getattr(plan, 'topic', 'Network Programming')
    difficulty = getattr(plan, 'difficulty', 'beginner')
    nodes = getattr(plan, 'nodes', [])

    print()
    print(f"📋 Learning Plan: {topic}")
    print(f"   Difficulty: {difficulty}")
    print(f"   Nodes: {len(nodes)}")
    print()

    for i, node in enumerate(nodes[:6], 1):
        title = getattr(node, 'title', f'Node {i}')
        concepts = getattr(node, 'concepts', [])
        hours = getattr(node, 'estimated_hours', 1.0)
        print(f"   {i}. {title} ({hours}h)")
        for c in concepts[:3]:
            print(f"      • {c}")
    print()

    # ═══════════════════════════════════════════════════════
    # Step 4: ResourceAgent — recommend resources
    # ═══════════════════════════════════════════════════════
    print("─" * 40)
    print("📚 ResourceAgent — Recommending resources...")
    from src.agents.resource_agent import ResourceAgent

    resource_agent = ResourceAgent()
    recommendation = resource_agent.recommend(profile_dict, goal="network programming")

    items = getattr(recommendation, 'items', [])
    print()
    print(f"📦 Recommended Resources: {len(items)} items")
    for item in items[:5]:
        rtype = getattr(item, 'resource_type', getattr(item, 'type', 'document'))
        title = getattr(item, 'title', str(item))
        priority = getattr(item, 'priority', 5)
        print(f"   [{rtype}] {title} (priority: {priority})")
    print()

    # ═══════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════
    print("=" * 60)
    print("  ✅ Demo Complete")
    print()
    print("  Pipeline: Student → ProfileAgent → PlannerAgent → ResourceAgent")
    print(f"  Result: {len(nodes)}-node learning plan with {len(items)} resources")
    print("=" * 60)


if __name__ == "__main__":
    main()
