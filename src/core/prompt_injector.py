"""
Phase 4 HITL — 双轨自适应拦截器 (Prompt Injector)

功能:
  将单向检索升级为双轨隔离检索:
    - HUMAN 轨: 人类最高指令, 绝对置顶, 最高上下文压制权重
    - AGENT 轨: Agent 自愈经验, 次级补充

用法:
    from core.prompt_injector import build_tiered_adaptive_prompt
    adapted = build_tiered_adaptive_prompt(base_prompt, "装饰器", collection)
"""

import json
from typing import Any, Optional


def build_tiered_adaptive_prompt(
    base_prompt: str,
    target_concept: str,
    collection: Any,
    max_human: int = 2,
    max_agent: int = 2,
) -> str:
    """
    双轨制自适应检索 — 人类经验绝对置顶, Agent 自愈经验次级补位.

    Args:
        base_prompt: 基础 System Prompt
        target_concept: 目标概念 (用于语义检索)
        collection: 记忆库 (LocalMemoryStore 或 ChromaDB)
        max_human: 最多注入条人类教训
        max_agent: 最多注入条 Agent 自愈教训

    Returns:
        注入双轨教训后的增强 System Prompt
    """

    # —— HUMAN 轨: 查询 source=human ——
    try:
        human_results = collection.query(
            query_texts=[target_concept],
            n_results=max_human,
            where={"$and": [
                {"doc_type": "failure_lessons"},
                {"source": "human"},
            ]},
        )
    except Exception:
        human_results = {"metadatas": [[]]}

    # —— AGENT 轨: 查询 source=agent ——
    try:
        agent_results = collection.query(
            query_texts=[target_concept],
            n_results=max_agent,
            where={"$and": [
                {"doc_type": "failure_lessons"},
                {"source": "agent"},
            ]},
        )
    except Exception:
        agent_results = {"metadatas": [[]]}

    has_human = (
        human_results.get("metadatas")
        and human_results["metadatas"]
        and human_results["metadatas"][0]
    )
    has_agent = (
        agent_results.get("metadatas")
        and agent_results["metadatas"]
        and agent_results["metadatas"][0]
    )

    if not has_human and not has_agent:
        return base_prompt

    # 构建注入块
    injection_parts = [
        "\n\n# ==================================================",
        "# ====== CRITICAL ARCHITECTURAL CONSTRAINTS =======",
        "# ==================================================",
    ]

    # —— 🚨 HUMAN 轨: 最高优先级 ——
    if has_human:
        injection_parts.extend([
            "",
            "# 🚨 [MANDATORY LAWS — DICTATED BY SUPREME HUMAN ARBITERS]",
            "# You have failed catastrophically here before and required human",
            "# intervention. You MUST follow these structural rules absolutely:",
            "",
        ])

        for i, meta in enumerate(human_results["metadatas"][0], 1):
            try:
                lesson = json.loads(meta["structured_data"])
            except Exception:
                continue

            injection_parts.extend([
                f"## HIGHEST PRIORITY CONSTRAINT {i}: {lesson.get('abstract_lint_rule', '')}",
                f"  * Context of Failure: {lesson.get('root_cause_analysis', '')[:150]}",
                f"  * DEADLY ANTI-PATTERN (NEVER REPLICATE):",
                "```python",
                lesson.get("anti_pattern_code", "# N/A"),
                "```",
                f"  * GOLDEN REFERENCE PATH (MUST FOLLOW):",
                "```python",
                lesson.get("golden_patch_code", "# N/A"),
                "```",
                "",
            ])

    # —— 💡 AGENT 轨: 次级建议 ——
    if has_agent:
        injection_parts.extend([
            "",
            "# 💡 [HISTORICAL SELF-HEALING REFLECTIONS — ADVISORY]",
            "# Minor auto-corrections from previous runs for optimization:",
            "",
        ])

        for i, meta in enumerate(agent_results["metadatas"][0], 1):
            try:
                lesson = json.loads(meta["structured_data"])
            except Exception:
                continue

            injection_parts.append(
                f"  {i}. [{lesson.get('error_type', 'N/A')}] "
                f"{lesson.get('abstract_lint_rule', '')[:100]}"
            )
            injection_parts.append(
                f"     Ref: {lesson.get('problem_context', '')[:80]}"
            )
        injection_parts.append("")

    injection_parts.append("# ====== END CONSTRAINTS TREE ======\n")

    return base_prompt + "\n".join(injection_parts)


def inject_if_available(
    base_prompt: str,
    target_concept: str,
    collection: Optional[Any] = None,
) -> str:
    """
    便捷包装: 如果记忆库可用则注入, 否则返回原 prompt.
    """
    if collection is None:
        try:
            from .meta_reflector import _LocalMemoryStore
            collection = _LocalMemoryStore()
        except Exception:
            return base_prompt
    return build_tiered_adaptive_prompt(base_prompt, target_concept, collection)
