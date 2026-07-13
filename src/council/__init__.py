"""
A3 v4 — Council Protocols: 多 Agent 协商消息协议

三阶段协议: Proposal → Deliberation → Decision
所有数据模型与现有 contracts.py 风格一致 (dataclass + to_dict/from_dict)。
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════
# 枚举
# ═══════════════════════════════════════════

class ProposalType(str, Enum):
    """提案类型"""
    PATH_ADJUSTMENT = "path_adjustment"         # 学习路径调整
    RESOURCE_CHANGE = "resource_change"         # 资源类型/难度变更
    DIFFICULTY_OVERRIDE = "difficulty_override" # 难度覆盖
    PACING_CHANGE = "pacing_change"             # 学习节奏调整
    STRATEGY_SWITCH = "strategy_switch"         # 教学策略切换
    EMERGENCY_HALT = "emergency_halt"           # 紧急暂停 (检测到严重错误)


class VoteType(str, Enum):
    """投票类型"""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"
    COUNTER_PROPOSE = "counter_propose"  # 附替代方案


class CouncilSessionState(str, Enum):
    """协商会话状态"""
    OPEN = "open"                   # 接受提案中
    DELIBERATING = "deliberating"   # 投票进行中
    DEADLOCKED = "deadlocked"       # 僵局 — 需 Chairperson 裁决
    RESOLVED = "resolved"           # 已达成决策
    TIMED_OUT = "timed_out"         # 超时降级


# ═══════════════════════════════════════════
# 消息协议
# ═══════════════════════════════════════════

@dataclass
class CouncilProposal:
    """协商提案 — 任何 Agent 可发起"""
    proposal_id: str
    session_id: str
    proposer_agent: str                     # e.g. "PlannerAgent"
    proposal_type: ProposalType
    target_layer: str                       # 被建议修改的模块
    rationale: str                          # 建议理由
    evidence: Dict[str, Any] = field(default_factory=dict)  # mastery_map 快照等
    suggested_action: str = ""              # 具体建议操作
    priority: int = 5                       # 1-10
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "session_id": self.session_id,
            "proposer_agent": self.proposer_agent,
            "proposal_type": self.proposal_type.value,
            "target_layer": self.target_layer,
            "rationale": self.rationale,
            "evidence": self.evidence,
            "suggested_action": self.suggested_action,
            "priority": self.priority,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CouncilProposal":
        return cls(
            proposal_id=data["proposal_id"],
            session_id=data["session_id"],
            proposer_agent=data["proposer_agent"],
            proposal_type=ProposalType(data["proposal_type"]),
            target_layer=data.get("target_layer", ""),
            rationale=data.get("rationale", ""),
            evidence=data.get("evidence", {}),
            suggested_action=data.get("suggested_action", ""),
            priority=data.get("priority", 5),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class CouncilReview:
    """Agent 对提案的评审意见"""
    review_id: str
    proposal_id: str
    reviewer_agent: str
    vote: VoteType
    reasoning: str                          # 投票理由
    counter_proposal: Optional[CouncilProposal] = None  # 替代方案
    confidence: float = 1.0                 # Agent 对自身判断的置信度
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "review_id": self.review_id,
            "proposal_id": self.proposal_id,
            "reviewer_agent": self.reviewer_agent,
            "vote": self.vote.value,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }
        if self.counter_proposal:
            result["counter_proposal"] = self.counter_proposal.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CouncilReview":
        cp = None
        if "counter_proposal" in data and data["counter_proposal"]:
            cp = CouncilProposal.from_dict(data["counter_proposal"])
        return cls(
            review_id=data["review_id"],
            proposal_id=data["proposal_id"],
            reviewer_agent=data["reviewer_agent"],
            vote=VoteType(data["vote"]),
            reasoning=data.get("reasoning", ""),
            counter_proposal=cp,
            confidence=data.get("confidence", 1.0),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class CouncilDecision:
    """协商最终决策"""
    decision_id: str
    session_id: str
    original_proposal_ids: List[str] = field(default_factory=list)
    reviews: List[CouncilReview] = field(default_factory=list)
    final_strategy: str = ""                # 最终采纳的教学策略
    reasoning: str = ""                     # 决策理由摘要
    supporting_agents: List[str] = field(default_factory=list)  # 支持该决策的 Agent
    dissenting_agents: List[str] = field(default_factory=list)  # 反对的 Agent
    consensus_score: float = 0.0            # 0.0-1.0
    minority_opinion: Optional[str] = None  # 少数派意见保留
    resolved_by: str = ""                   # "majority" | "weighted" | "chairperson"
    state: str = "RESOLVED"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "session_id": self.session_id,
            "original_proposal_ids": self.original_proposal_ids,
            "reviews": [r.to_dict() for r in self.reviews],
            "final_strategy": self.final_strategy,
            "reasoning": self.reasoning,
            "supporting_agents": self.supporting_agents,
            "dissenting_agents": self.dissenting_agents,
            "consensus_score": self.consensus_score,
            "minority_opinion": self.minority_opinion,
            "resolved_by": self.resolved_by,
            "state": self.state,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CouncilDecision":
        reviews = [CouncilReview.from_dict(r) for r in data.get("reviews", [])]
        return cls(
            decision_id=data["decision_id"],
            session_id=data["session_id"],
            original_proposal_ids=data.get("original_proposal_ids", []),
            reviews=reviews,
            final_strategy=data.get("final_strategy", ""),
            reasoning=data.get("reasoning", ""),
            supporting_agents=data.get("supporting_agents", []),
            dissenting_agents=data.get("dissenting_agents", []),
            consensus_score=data.get("consensus_score", 0.0),
            minority_opinion=data.get("minority_opinion"),
            resolved_by=data.get("resolved_by", ""),
            state=data.get("state", "RESOLVED"),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class CouncilSession:
    """单次协商会话"""
    session_id: str
    context: Dict[str, Any] = field(default_factory=dict)
    proposals: List[CouncilProposal] = field(default_factory=list)
    reviews: List[CouncilReview] = field(default_factory=list)
    decisions: List[CouncilDecision] = field(default_factory=list)
    state: CouncilSessionState = CouncilSessionState.OPEN
    chairperson: str = "PlannerAgent"
    round_number: int = 0
    max_rounds: int = 3
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
