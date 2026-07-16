"""Render 部署前本地验证 — 完整 5-Agent 管道测试 (mock provider)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
os.environ.setdefault("LLM_PROVIDER", "mock")

from src.workflow import A3Workflow

wf = A3Workflow(student_id="render_verify")
result = wf.run(user_goal="I want to learn Python backend development")

checks = {
    "ProfileAgent (profile)": bool(result.profile),
    "PlannerAgent (learning_plan)": bool(result.learning_plan and result.learning_plan.get("nodes")),
    "ResourceAgent (resources)": bool(result.resources),
    "ReviewGate (evaluation)": bool(result.evaluation and "score" in result.evaluation),
    "ReflectionAgent (reflection)": bool(result.reflection),
    "Trace (EventBus timeline)": bool(result.trace and len(result.trace) >= 5),
    "Memory saved": result.memory_saved,
    "Workflow success": result.success,
}

print("=" * 52)
for name, ok in checks.items():
    print(f"  {'✅' if ok else '❌'}  {name}")
print("=" * 52)
print(f"  plan nodes:  {len((result.learning_plan or {}).get('nodes', []))}")
print(f"  resources:   {len(result.resources or [])}")
_ev = result.evaluation or {}
print(f"  review:      score={_ev.get('score')} passed={_ev.get('passed')}")
print(f"  trace items: {len(result.trace or [])}")
print(f"  duration:    {result.total_duration_ms} ms")
print(f"  errors:      {result.errors or '无'}")
print("=" * 52)

failed = [n for n, ok in checks.items() if not ok]
if failed:
    print("VERIFY_FAILED:", failed)
    sys.exit(1)
print("VERIFY_ALL_PASSED")
