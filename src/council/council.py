"""
A3 v4 — AgentCouncil 核心协商引擎

三阶段协议:
  Phase 1 — Proposal:   Agent 提交提案
  Phase 2 — Deliberation: 其他 Agent 评审投票
  Phase 3 — Decision:     Council 汇总生成最终决策

设计原则:
  - 无侵入: 现有 Agent 无需修改核心逻辑，仅注册 opinion 回调
  - 超时降级: 30s 内无共识 → Chairperson 独裁决策
  - 僵局处理: 3 轮无法达成 2/3 → 强制裁决 + 记录 minority_opinion
"""

from __future__ import annotations
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from . import (
    CouncilProposal, CouncilReview, CouncilDecision, CouncilSession,
    CouncilSessionState, VoteType,
)
from ..core.event_bus import AgentEventBus


# 回调签名: (CouncilProposal, Dict[str, Any]) -> CouncilReview
OpinionCallback = Callable[[CouncilProposal, Dict[str, Any]], CouncilReview]
# 回调签名: (Dict[str, Any]) -> Optional[CouncilProposal]
ProposalCallback = Callable[[Dict[str, Any]], Optional[CouncilProposal]]


@dataclass
class _AgentCapability:
    """Agent 协商能力注册"""
    agent_name: str
    opinion_cb: Optional[OpinionCallback] = None
    proposal_cb: Optional[ProposalCallback] = None
    weight: float = 1.0  # 投票权重 (1.0=标准, 2.0=专家)

    def __hash__(self):
        return hash(self.agent_name)


# 默认空 Agent (用于未注册 Agent 的 fallback)
_NOOP_CAP = _AgentCapability(agent_name="__noop__", weight=0.0)


class AgentCouncil:
    """
    多 Agent 协商层。

    使用示例:
        council = AgentCouncil()
        council.register("PlannerAgent", opinion_cb=my_planner_opinion)
        council.register("ResourceGenAgent", opinion_cb=my_resource_opinion)

        sid = council.open_session({"student_id": "xiao_lin"})
        decision = council.deliberate(sid, proposal)
    """

    def __init__(self, chairperson: str = "PlannerAgent", timeout_s: float = 30.0):
        self.chairperson = chairperson
        self.timeout_s = timeout_s
        self._agents: Dict[str, _AgentCapability] = {}
        self._sessions: Dict[str, CouncilSession] = {}
        self._bus = AgentEventBus.get_instance()

    # ── 注册 ──────────────────────────────────

    def register(
        self,
        agent_name: str,
        opinion_cb: OpinionCallback,
        proposal_cb: Optional[ProposalCallback] = None,
        weight: float = 1.0,
    ) -> None:
        """注册 Agent 的协商能力。"""
        self._agents[agent_name] = _AgentCapability(
            agent_name=agent_name,
            opinion_cb=opinion_cb,
            proposal_cb=proposal_cb,
            weight=weight,
        )

    def unregister(self, agent_name: str) -> None:
        self._agents.pop(agent_name, None)

    @property
    def registered_agents(self) -> List[str]:
        return list(self._agents.keys())

    def _get_cap(self, agent_name: str) -> _AgentCapability:
        return self._agents.get(agent_name, _NOOP_CAP)

    # ── 会话管理 ──────────────────────────────

    def open_session(self, context: Dict[str, Any]) -> str:
        """开启协商会话，返回 session_id。"""
        session_id = f"council_{uuid.uuid4().hex[:12]}"
        session = CouncilSession(
            session_id=session_id,
            context=context,
            chairperson=self.chairperson,
        )
        self._sessions[session_id] = session

        self._bus.emit(
            "AgentCouncil", "session_opened",
            input_summary=f"context_keys={list(context.keys())}",
            output_summary=f"session_id={session_id}",
            metadata={"session_id": session_id, "state": "OPEN"},
        )
        return session_id

    def _get_session(self, session_id: str) -> CouncilSession:
        if session_id not in self._sessions:
            raise ValueError(f"Council session not found: {session_id}")
        return self._sessions[session_id]

    # ── Phase 1: Proposal ────────────────────

    def submit_proposal(self, proposal: CouncilProposal) -> str:
        """Agent 提交提案 → 进入 Deliberation。"""
        session = self._get_session(proposal.session_id)
        session.proposals.append(proposal)
        session.state = CouncilSessionState.DELIBERATING
        session.round_number += 1

        self._bus.emit(
            "AgentCouncil", "proposal_submitted",
            input_summary=f"from={proposal.proposer_agent} type={proposal.proposal_type.value}",
            output_summary=f"pid={proposal.proposal_id} target={proposal.target_layer}",
            metadata={"proposal": proposal.to_dict()},
        )
        return proposal.proposal_id

    # ── Phase 2: Deliberation ────────────────

    def collect_reviews(self, session_id: str, proposal: CouncilProposal) -> List[CouncilReview]:
        """收集所有注册 Agent 对提案的评审意见。"""
        session = self._get_session(session_id)
        reviews: List[CouncilReview] = []

        for name, cap in self._agents.items():
            if name == proposal.proposer_agent:
                continue  # 提案人不评审自己的提案
            try:
                if cap.opinion_cb:
                    review = cap.opinion_cb(proposal, session.context)
                    reviews.append(review)
                else:
                    reviews.append(CouncilReview(
                        review_id=f"rev_{uuid.uuid4().hex[:8]}",
                        proposal_id=proposal.proposal_id,
                        reviewer_agent=name,
                        vote=VoteType.ABSTAIN,
                        reasoning="Agent 未注册协商能力",
                        confidence=0.0,
                    ))
            except Exception as e:
                reviews.append(CouncilReview(
                    review_id=f"rev_{uuid.uuid4().hex[:8]}",
                    proposal_id=proposal.proposal_id,
                    reviewer_agent=name,
                    vote=VoteType.ABSTAIN,
                    reasoning=f"Agent 评审异常: {e}",
                    confidence=0.0,
                ))

        session.reviews.extend(reviews)

        for r in reviews:
            self._bus.emit(
                "AgentCouncil", "review_collected",
                input_summary=f"reviewer={r.reviewer_agent} vote={r.vote.value}",
                output_summary=r.reasoning[:200],
                metadata={"review": r.to_dict()},
            )
        return reviews

    def _weight_of(self, agent_name: str) -> float:
        return self._get_cap(agent_name).weight

    def _total_weight(self, agent_names: List[str]) -> float:
        return sum(self._weight_of(n) for n in agent_names)

    # ── Phase 3: Decision ────────────────────

    def deliberate(self, session_id: str, proposal: CouncilProposal) -> CouncilDecision:
        """完整协商流程: 提交提案 → 收集评审 → 生成决策。"""
        self.submit_proposal(proposal)
        reviews = self.collect_reviews(session_id, proposal)
        return self._resolve(session_id, proposal, reviews)

    def _resolve(
        self, session_id: str, proposal: CouncilProposal, reviews: List[CouncilReview]
    ) -> CouncilDecision:
        """汇总投票 → 生成决策。"""
        session = self._get_session(session_id)

        approving: List[str] = []
        rejecting: List[str] = []
        minority_opinions: List[str] = []

        for r in reviews:
            if r.vote == VoteType.APPROVE:
                approving.append(r.reviewer_agent)
            elif r.vote == VoteType.REJECT:
                rejecting.append(r.reviewer_agent)
                if r.reasoning:
                    minority_opinions.append(f"[{r.reviewer_agent}] {r.reasoning[:120]}")
            elif r.vote == VoteType.COUNTER_PROPOSE and r.counter_proposal:
                rejecting.append(r.reviewer_agent)
                minority_opinions.append(
                    f"[{r.reviewer_agent}] 替代方案: {r.counter_proposal.suggested_action[:120]}"
                )

        # 计算加权共识
        total_w = self._total_weight([r.reviewer_agent for r in reviews])
        approve_w = self._total_weight(approving)
        consensus = approve_w / max(total_w, 1.0)

        resolved_by = "majority"
        final_strategy = proposal.suggested_action
        final_reasoning = proposal.rationale

        if consensus >= 0.67:
            resolved_by = "majority"
        elif consensus >= 0.5:
            resolved_by = "chairperson"
            final_strategy = f"[Chairperson裁决] {proposal.suggested_action}"
            final_reasoning = f"{proposal.rationale} (chairperson override, consensus={consensus:.2f})"
        else:
            resolved_by = "chairperson"
            final_strategy = "REJECTED — 维持原方案不变"
            final_reasoning = f"共识度不足 ({consensus:.2f}), 提案被驳回: {proposal.rationale[:200]}"

        # 处理替代方案
        counter_reviews = [r for r in reviews
                           if r.vote == VoteType.COUNTER_PROPOSE and r.counter_proposal]
        if counter_reviews and consensus < 0.67:
            cp = counter_reviews[0].counter_proposal
            if cp is not None:
                cp_reviews = self.collect_reviews(session_id, cp)
                cp_approving = [r.reviewer_agent for r in cp_reviews if r.vote == VoteType.APPROVE]
                cp_total = self._total_weight([r.reviewer_agent for r in cp_reviews])
                cp_approve = self._total_weight(cp_approving)
                cp_consensus = cp_approve / max(cp_total, 1.0)
                if cp_consensus >= 0.67:
                    final_strategy = cp.suggested_action
                    final_reasoning = f"替代方案通过 (consensus={cp_consensus:.2f}): {cp.rationale}"
                    resolved_by = "compromise"
                    approving = cp_approving

        decision = CouncilDecision(
            decision_id=f"dec_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            original_proposal_ids=[proposal.proposal_id],
            reviews=reviews,
            final_strategy=final_strategy,
            reasoning=final_reasoning[:500],
            supporting_agents=approving,
            dissenting_agents=rejecting,
            consensus_score=round(consensus, 2),
            minority_opinion="; ".join(minority_opinions)[:500] if minority_opinions else None,
            resolved_by=resolved_by,
        )

        session.decisions.append(decision)
        session.state = CouncilSessionState.RESOLVED

        self._bus.emit(
            "AgentCouncil", "decision_finalized",
            input_summary=f"consensus={consensus:.2f} resolved_by={resolved_by}",
            output_summary=decision.final_strategy[:300],
            metadata={"decision": decision.to_dict()},
        )
        return decision

    def resolve_deadlock(self, session_id: str) -> CouncilDecision:
        """僵局处理: 3 轮无共识 → Chairperson 强制裁决。"""
        session = self._get_session(session_id)
        session.state = CouncilSessionState.DEADLOCKED

        decision = CouncilDecision(
            decision_id=f"dec_{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            original_proposal_ids=[p.proposal_id for p in session.proposals],
            reviews=session.reviews,
            final_strategy="CHAIRPERSON_OVERRIDE: 恢复默认 Pipeline 策略",
            reasoning=f"协商僵局 ({session.round_number} 轮未达成共识), {self.chairperson} 独裁裁决",
            supporting_agents=[self.chairperson],
            dissenting_agents=[],
            consensus_score=0.0,
            minority_opinion="僵局 — 无共识达成",
            resolved_by="chairperson",
        )

        session.decisions.append(decision)
        session.state = CouncilSessionState.RESOLVED

        self._bus.emit(
            "AgentCouncil", "deadlock_resolved",
            input_summary=f"rounds={session.round_number}",
            output_summary="CHAIRPERSON_OVERRIDE",
            metadata={"decision": decision.to_dict()},
        )
        return decision

    # ── 工具方法 ──────────────────────────────

    def get_session_log(self, session_id: str) -> Dict[str, Any]:
        """获取协商会话的完整日志 (用于 Dashboard)。"""
        session = self._get_session(session_id)
        return {
            "session_id": session.session_id,
            "state": session.state.value,
            "round_number": session.round_number,
            "chairperson": session.chairperson,
            "proposals": [p.to_dict() for p in session.proposals],
            "reviews": [r.to_dict() for r in session.reviews],
            "decisions": [d.to_dict() for d in session.decisions],
            "created_at": session.created_at,
        }

    def close_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
