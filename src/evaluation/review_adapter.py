"""
Phase 4.5 — ReviewGate Adapter

Adapts ReviewGateManager.evaluate_content_quality() output
into the structured format consumed by EvaluationManager.

Zero file I/O. Zero ReviewGate modification.
"""

from __future__ import annotations
import time
from typing import Any, Dict


def adapt_review_gate_result(
    review_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convert ReviewGate content quality result into evaluation format.

    Args:
        review_result: Output from ReviewGateManager.evaluate_content_quality(text)
            → {score: int, passed: bool, scores: {colloquialism, clarity, progression}}

    Returns:
        {
            score: int (0-100),
            passed: bool,
            gates: [{name, passed, message, scores}],
            checkpoint_sig: str,
        }
    """
    score = review_result.get("score", 50)
    passed = review_result.get("passed", False)
    scores = review_result.get("scores", {})

    return {
        "score": score,
        "passed": passed,
        "gates": [
            {
                "name": "CONTENT_QUALITY",
                "passed": passed,
                "message": (
                    f"{'✅' if passed else '❌'} 内容评审 "
                    f"(得分: {score}/100, 口语化: {scores.get('colloquialism', 0):.0f}, "
                    f"清晰度: {scores.get('clarity', 0):.0f}, "
                    f"过渡: {scores.get('progression', 0):.0f})"
                ),
                "scores": scores,
            }
        ],
        "checkpoint_sig": f"SIG_RG_EVAL_{int(time.time())}",
    }
