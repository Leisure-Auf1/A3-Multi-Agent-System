"""Phase 4.4 — Evaluation package.

Exports:
  - EvaluationManager (new): unified quality score + decision explanations
  - agent_evaluator / judge (legacy): preserved for existing callers
"""

from .evaluator import EvaluationManager

__all__ = ["EvaluationManager"]
