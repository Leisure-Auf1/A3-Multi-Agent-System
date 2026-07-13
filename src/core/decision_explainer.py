"""
Phase 11 — DecisionExplainer: Agent 决策解释引擎

让每个 Agent 输出 "为什么这么决定"。

支持的 Agent:
  - ProfileAgent: 为什么输出这个画像？
  - PlannerAgent: 为什么跳过/加深某个节点？
  - ResourceRecommendationAgent: 为什么推荐这个资源？

使用:
    explainer = DecisionExplainer()
    explanation = explainer.explain_profile_extraction(profile_dict, student_text)
    explanation = explainer.explain_plan_decision(mastery_map, node, action)
    explanation = explainer.explain_recommendation(resource, profile, mastery)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

@dataclass
class DecisionExplanation:
    """一次决策解释"""
    agent: str
    action: str
    decision: str                                # 决策描述
    reason: str                                  # 核心理由
    confidence: float = 1.0                      # 置信度 0-1
    evidence: List[str] = field(default_factory=list)  # 证据链
    alternative: str = ""                        # 备选方案
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "action": self.action,
            "decision": self.decision,
            "reason": self.reason,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "alternative": self.alternative,
            "timestamp": self.timestamp,
        }

    def to_markdown(self) -> str:
        lines = [
            f"**{self.agent}** → `{self.action}`",
            f"> 决策: {self.decision}",
            f"> 理由: {self.reason}",
            f"> 置信度: {self.confidence:.0%}",
        ]
        if self.evidence:
            lines.append("> 证据: " + ", ".join(self.evidence))
        if self.alternative:
            lines.append(f"> 备选: {self.alternative}")
        return "\n".join(lines)


# ──────────────────────────────────────────────
# DecisionExplainer
# ──────────────────────────────────────────────

class DecisionExplainer:
    """
    Agent 决策解释器.

    为每个 Agent 的决策生成人类可读的解释。
    """

    # ── ProfileAgent 解释 ──────────────────

    def explain_profile_extraction(
        self,
        profile_dict: Dict[str, str],
        student_text: str = "",
        memory_context: Optional[Dict[str, Any]] = None,
    ) -> List[DecisionExplanation]:
        """解释画像提取"""
        explanations: List[DecisionExplanation] = []

        dim_labels = {
            "knowledge_base": "知识基础", "cognitive_style": "认知风格",
            "error_prone_bias": "易错倾向", "learning_pace": "学习节奏",
            "interaction_preference": "交互偏好", "frustration_threshold": "抗挫能力",
        }
        dim_descriptions = {
            "junior_dev": "学生描述了零基础或初学者特征",
            "mid_level": "学生提到有一定编程经验",
            "senior": "学生展示了丰富开发经验",
            "visual_dominant": "学生偏好图解和视频学习",
            "text_linear": "学生偏好阅读文字材料",
            "auditory": "学生偏好听课和音频学习",
            "fast_track": "学生表达了快速学习意愿",
            "normal": "学生未特别强调学习节奏",
            "deep_dive": "学生想深入理解底层原理",
            "code_sandbox": "学生喜欢动手写代码",
            "quiz_first": "学生偏好做题测试",
            "passive_read": "学生喜欢先阅读理解",
            "low": "学生表达了容易挫败或放弃",
            "medium": "学生未表达特殊抗挫特征",
            "high": "学生表达了较强的抗压能力",
            "magic_syntax_blind": "学生提到不理解语法糖/@装饰器",
            "indentation_errors": "学生提到缩进格式问题",
            "variable_scoping": "学生提到变量作用域混淆",
            "type_mismatch": "学生提到类型错误",
            "import_issues": "学生提到导入问题",
        }

        for dim, label in dim_labels.items():
            val = profile_dict.get(dim, "")
            if not val:
                continue
            desc = dim_descriptions.get(val, f"推理为 {val}")
            evidence = [student_text[:100]] if student_text else []
            if memory_context and dim in memory_context:
                evidence.append(f"历史画像: {memory_context[dim]}")

            explanations.append(DecisionExplanation(
                agent="ProfileAgent",
                action=f"detect_{dim}",
                decision=f"{label} = {val}",
                reason=desc,
                confidence=0.85,
                evidence=evidence,
            ))

        return explanations

    # ── PlannerAgent 解释 ──────────────────

    def explain_plan_decision(
        self,
        mastery_map: Dict[str, float],
        node_id: str,
        node_title: str,
        action: str,          # skip | boost | normal
        detail: str = "",
    ) -> DecisionExplanation:
        """解释学习路径决策"""
        score = mastery_map.get(node_id, -1)

        if action == "skip":
            return DecisionExplanation(
                agent="PlannerAgent",
                action=f"skip_{node_id}",
                decision=f"跳过「{node_title}」",
                reason=f"已掌握 (mastery={score:.0%}), 无需重复学习",
                confidence=min(score + 0.1, 1.0),
                evidence=[f"mastery_map['{node_id}'] = {score:.2f}"],
                alternative=f"如果 mastery < 0.8 则会保留此节点",
            )
        elif action == "boost":
            return DecisionExplanation(
                agent="PlannerAgent",
                action=f"boost_{node_id}",
                decision=f"强化「{node_title}」(深度+1, 练习+2)",
                reason=f"薄弱环节 (mastery={score:.0%}), 需要更多练习{', ' + detail if detail else ''}",
                confidence=0.92,
                evidence=[f"mastery_map['{node_id}'] = {score:.2f}",
                          f"weak_points 包含相关概念"],
            )
        else:
            return DecisionExplanation(
                agent="PlannerAgent",
                action=f"include_{node_id}",
                decision=f"保留「{node_title}」正常学习",
                reason=f"掌握度正常 (mastery={score:.0%}), 标准路径",
                confidence=0.88,
                evidence=[f"mastery_map['{node_id}'] = {score:.2f}"],
            )

    # ── ResourceRecommendationAgent 解释 ──

    def explain_recommendation(
        self,
        resource_type: str,
        resource_title: str,
        profile: Dict[str, str],
        mastery_map: Dict[str, float],
        concept: str = "",
    ) -> DecisionExplanation:
        """解释资源推荐"""
        reasons = []
        evidence = []

        mastery = mastery_map.get(concept, -1) if concept else -1
        cognitive = profile.get("cognitive_style", "")
        interaction = profile.get("interaction_preference", "")

        if mastery >= 0 and mastery < 0.3:
            reasons.append(f"薄弱概念 (mastery={mastery:.0%})")
            evidence.append(f"mastery['{concept}']={mastery:.2f}")
        elif mastery >= 0.8:
            reasons.append(f"已掌握 — 提供拓展挑战")
            evidence.append(f"mastery['{concept}']={mastery:.2f}")

        if cognitive == "visual_dominant" and resource_type == "visual":
            reasons.append("视觉学习偏好")
            evidence.append(f"cognitive_style={cognitive}")
        if interaction == "code_sandbox" and resource_type == "code_lab":
            reasons.append("动手实践偏好")
            evidence.append(f"interaction_preference={interaction}")

        reason_text = "; ".join(reasons) if reasons else f"匹配学生画像 ({cognitive}/{interaction})"

        return DecisionExplanation(
            agent="ResourceRecommendationAgent",
            action="recommend",
            decision=f"推荐「{resource_title}」({resource_type})",
            reason=reason_text,
            confidence=0.85,
            evidence=evidence,
            alternative=f"如果画像不同会推荐其他类型",
        )

    # ── 通用解释 ──────────────────────────

    def explain_memory_decision(
        self,
        agent: str,
        memory_key: str,
        old_value: Any,
        new_value: Any,
    ) -> DecisionExplanation:
        """解释 Memory 更新决策"""
        return DecisionExplanation(
            agent=agent,
            action=f"update_{memory_key}",
            decision=f"{memory_key}: {old_value} → {new_value}",
            reason=f"基于本轮反馈, {memory_key} 发生了变化",
            confidence=0.9,
            evidence=[f"old: {old_value}", f"new: {new_value}"],
        )


# ──────────────────────────────────────────────
# ReflectionResult
# ──────────────────────────────────────────────

@dataclass
class ReflectionResult:
    """MetaReflector 自我反思结果"""
    mistake: str                  # 错误描述
    root_cause: str               # 根因
    improvement: str              # 改进方案
    future_strategy: str          # 未来策略
    severity: str = "MEDIUM"      # LOW | MEDIUM | HIGH | CRITICAL
    concept: str = ""             # 关联概念
    node_id: str = ""             # 关联节点
    affected_profiles: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mistake": self.mistake,
            "root_cause": self.root_cause,
            "improvement": self.improvement,
            "future_strategy": self.future_strategy,
            "severity": self.severity,
            "concept": self.concept,
            "node_id": self.node_id,
            "affected_profiles": self.affected_profiles,
        }

    def to_experience_entry(self) -> Dict[str, Any]:
        """转换为 ExperienceMemory 可存储格式"""
        return {
            "problem": self.mistake[:120],
            "cause": self.root_cause[:120],
            "context": f"node-{self.node_id} / {self.concept}",
            "solution": f"{self.improvement} | 策略: {self.future_strategy}",
            "source": "metareflector",
            "node_id": self.node_id,
            "severity": self.severity,
        }
