#!/usr/bin/env python3
"""
Basic Agent — Veritas Runtime Example

Minimal example showing how to use RuntimeClient to execute a task.
No RuntimeEngine imports — all through the public SDK.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.sdk import RuntimeClient, TaskRequest
from src.sdk.exceptions import VeritasError


def main():
    print("=" * 50)
    print("  Veritas Basic Agent Example")
    print("=" * 50)
    print()

    client = RuntimeClient()

    # Example 1: Simple task
    print("▶ Running: planner task...")
    result = client.run(TaskRequest(
        objective="generate a Python learning plan",
        agent="planner",
    ))
    print(f"  Status: {result.status.value}")
    print(f"  Time:   {result.execution_time_ms:.1f}ms")
    print()

    # Example 2: Task with context
    print("▶ Running: evaluator with context...")
    result = client.run(TaskRequest(
        objective="evaluate student progress",
        agent="evaluator",
        context={"student_level": "intermediate", "topic": "async/await"},
    ))
    print(f"  Status: {result.status.value}")
    print(f"  Session: {result.session_id}")
    print()

    # Example 3: Query sessions
    print("▶ Sessions:")
    for s in client.sessions():
        print(f"  {s.session_id} | {s.state} | {s.total_duration_ms:.0f}ms")

    # Example 4: Runtime status
    print()
    print("▶ Runtime status:")
    status = client.status()
    for k, v in status.items():
        print(f"  {k}: {v}")

    # Example 5: Explainability
    print()
    print("▶ Explainability for last session:")
    try:
        explanation = client.explain(result.session_id)
        print(f"  Decisions: {explanation['total_decisions']}")
        print(f"  Score: {explanation['explainability_score']:.2f}")
    except VeritasError as e:
        print(f"  {e}")


if __name__ == "__main__":
    main()
