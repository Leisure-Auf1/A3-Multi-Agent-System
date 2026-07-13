"""
A3 v4 — Evolution Memory: Agent 经验进化记忆

在现有 StudentMemory + ExperienceMemory 之上增加:
  AgentExperienceRecord — Agent 级别的策略经验
  StrategyInjector — 将经验自动注入 Agent 行为决策

使用场景:
  ResourceAgent 发现视觉型学生对文本资源完成率低
  → 记录经验 → 下次自动调整资源策略
"""

from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class AgentExperienceRecord:
    """
    Agent 经验记录 — 跨学生、跨会话的策略教训。

    与现有 ExperienceMemory 的区别:
      ExperienceMemory → 专注于内容生成失败的教训 (代码/文档质量)
      AgentExperienceRecord → 专注于 Agent 行为策略的教训 (资源选择/难度调整/教学策略)
    """
    record_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    agent_name: str = ""                  # 产生此经验的 Agent
    problem: str = ""                     # 发现的问题
    cause: str = ""                       # 根因分析
    solution: str = ""                    # 改进方案
    strategy_key: str = ""               # 策略键 (用于 Injector 的索引)
    success_rate: float = 0.5             # 此方案的历史成功率
    evidence: Dict[str, Any] = field(default_factory=dict)  # 支撑证据
    keywords: List[str] = field(default_factory=list)       # 召回关键词
    severity: str = "MEDIUM"             # LOW | MEDIUM | HIGH | CRITICAL
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_applied_at: Optional[str] = None
    apply_count: int = 0                 # 已应用次数

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "agent_name": self.agent_name,
            "problem": self.problem,
            "cause": self.cause,
            "solution": self.solution,
            "strategy_key": self.strategy_key,
            "success_rate": self.success_rate,
            "evidence": self.evidence,
            "keywords": self.keywords,
            "severity": self.severity,
            "created_at": self.created_at,
            "last_applied_at": self.last_applied_at,
            "apply_count": self.apply_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentExperienceRecord":
        return cls(
            record_id=data.get("record_id", uuid.uuid4().hex[:8]),
            agent_name=data.get("agent_name", ""),
            problem=data.get("problem", ""),
            cause=data.get("cause", ""),
            solution=data.get("solution", ""),
            strategy_key=data.get("strategy_key", ""),
            success_rate=data.get("success_rate", 0.5),
            evidence=data.get("evidence", {}),
            keywords=data.get("keywords", []),
            severity=data.get("severity", "MEDIUM"),
            created_at=data.get("created_at", ""),
            last_applied_at=data.get("last_applied_at"),
            apply_count=data.get("apply_count", 0),
        )

    def semantic_anchor(self) -> str:
        return (
            f"[{self.agent_name}] 问题: {self.problem[:80]}. "
            f"方案: {self.solution[:80]}. 成功率: {self.success_rate:.0%}"
        )


@dataclass
class StrategyInjector:
    """
    策略注入器 — 在 Agent 决策前自动注入已学经验。

    工作流:
      1. Agent 请求策略建议 → query(agent_name, context)
      2. Injector 基于关键词 + 历史成功率检索最佳经验
      3. 返回策略建议列表 → Agent 自主决定是否采纳

    使用:
      injector = StrategyInjector(memory_store)
      suggestions = injector.query("ResourceGenAgent", {
          "student_cognitive_style": "visual_dominant",
          "current_difficulty": 0.7,
      })
    """

    def __init__(self, store: Optional["AgentExperienceMemory"] = None):
        self._store = store
        self._override_rules: Dict[str, Dict[str, Any]] = {}  # 策略覆盖规则
        self._feedback_buffer: List[Dict[str, Any]] = []      # 待确认的反馈

    def set_store(self, store: "AgentExperienceMemory") -> None:
        self._store = store

    def query(
        self,
        agent_name: str,
        context: Dict[str, Any],
        top_k: int = 3,
        min_success_rate: float = 0.5,
    ) -> List[AgentExperienceRecord]:
        """
        查询适用于当前上下文的策略建议。

        检索策略:
          1. 精确匹配 strategy_key
          2. 关键词重叠度排序
          3. 按 success_rate 降序
          4. 返回 top_k 条
        """
        if self._store is None:
            return []

        candidates = self._store.query_by_agent(
            agent_name, context.get("keywords", [])
        )

        # 过滤 + 排序
        scored = []
        for rec in candidates:
            if rec.success_rate < min_success_rate:
                continue
            score = rec.success_rate * (1.0 + rec.apply_count * 0.02)  # 成功率高 + 多次应用
            scored.append((score, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [rec for _, rec in scored[:top_k]]

    def inject(
        self,
        agent_name: str,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """
        自动注入策略 — 返回 Agent 应该采用的策略建议文本。

        仅在经验置信度高时 (success_rate ≥ 0.7 且 apply_count ≥ 2) 自动注入。
        """
        suggestions = self.query(
            agent_name, context, top_k=1, min_success_rate=0.7,
        )
        for s in suggestions:
            if s.apply_count >= 2:
                s.last_applied_at = datetime.now(timezone.utc).isoformat()
                s.apply_count += 1
                return f"[AutoStrategy] {s.solution} (based on {s.record_id}, success_rate={s.success_rate:.0%})"
        return None

    def record_feedback(
        self, record_id: str, was_successful: bool, evidence: Dict[str, Any]
    ) -> None:
        """记录策略应用后的反馈 (用于更新 success_rate)。"""
        if self._store:
            self._store.update_success_rate(record_id, was_successful, evidence)

    def set_override(
        self, strategy_key: str, rule: Dict[str, Any]
    ) -> None:
        """设置策略覆盖规则 (用于紧急纠正)。"""
        self._override_rules[strategy_key] = rule

    def get_override(self, strategy_key: str) -> Optional[Dict[str, Any]]:
        return self._override_rules.get(strategy_key)


class AgentExperienceMemory:
    """
    Agent 经验记忆存储。

    存储方式: JSON 文件 (竞赛阶段) / SQLite (生产)
    接口预留 Vector DB 迁移路径。
    """

    def __init__(self, storage_path: str = "storage/memory/agent_experience.json"):
        self._path = storage_path
        self._records: Dict[str, AgentExperienceRecord] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(self._path, "r") as f:
                data = json.load(f)
            for item in data.get("records", []):
                rec = AgentExperienceRecord.from_dict(item)
                self._records[rec.record_id] = rec
        except (FileNotFoundError, json.JSONDecodeError):
            self._records = {}
            self.seed_defaults()

    def _save(self) -> None:
        import os
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            json.dump({
                "records": [r.to_dict() for r in self._records.values()],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, f, ensure_ascii=False, indent=2)

    def store(self, record: AgentExperienceRecord) -> str:
        self._records[record.record_id] = record
        self._save()
        return record.record_id

    def query_by_agent(self, agent_name: str, keywords: List[str]) -> List[AgentExperienceRecord]:
        """按 Agent 名和关键词查询。"""
        results = []
        for rec in self._records.values():
            if rec.agent_name != agent_name:
                continue
            # 关键词匹配
            overlap = len(set(kw.lower() for kw in rec.keywords) &
                         set(kw.lower() for kw in keywords))
            if overlap > 0 or not keywords:
                results.append(rec)
        return results

    def query_by_keyword(self, keyword: str) -> List[AgentExperienceRecord]:
        return self.query_by_agent("", [keyword])

    def update_success_rate(
        self, record_id: str, was_successful: bool, evidence: Dict[str, Any]
    ) -> None:
        """EMA 更新成功率。"""
        rec = self._records.get(record_id)
        if rec is None:
            return
        delta = 0.15 if was_successful else -0.10
        rec.success_rate = round(max(0.0, min(1.0, rec.success_rate + delta)), 2)
        rec.apply_count += 1
        rec.last_applied_at = datetime.now(timezone.utc).isoformat()
        rec.evidence = {**rec.evidence, **evidence}
        self._save()

    def seed_defaults(self) -> None:
        """预注入默认经验 (解决冷启动问题)。"""
        defaults = [
            AgentExperienceRecord(
                agent_name="ResourceGenAgent",
                problem="视觉型学生对纯文本资源完成率低",
                cause="认知风格与资源类型不匹配——visual_dominant 学生需要图解/动画",
                solution="对 cognitive_style=visual_dominant 的学生, 优先分配 MindMap + Animation 类型资源, 降低纯文本比例",
                strategy_key="resource_style_match",
                success_rate=0.85,
                keywords=["visual_dominant", "cognitive_style", "mindmap", "animation"],
                severity="HIGH",
            ),
            AgentExperienceRecord(
                agent_name="PlannerAgent",
                problem="学生 mastery<0.3 仍被分配高难度概念",
                cause="规划时未充分前置 mastery_map 检查",
                solution="规划前强制检查 mastery_map: 若目标概念前置知识 mastery<0.3 → 插入补充节点并降低目标难度一档",
                strategy_key="mastery_gated_planning",
                success_rate=0.80,
                keywords=["mastery", "difficulty", "prerequisite"],
                severity="CRITICAL",
            ),
            AgentExperienceRecord(
                agent_name="AgentEvaluator",
                problem="同一概念连错 3 次未触发难度降级",
                cause="Evaluator 仅评分但未将结果传递给 Planner 做主动调整",
                solution="Evaluator 检测到连续 3 次低分 → 通过 EventBus 发出 council.proposal(ProposalType.DIFFICULTY_OVERRIDE) 触发 Council 重新规划",
                strategy_key="consecutive_failure_trigger",
                success_rate=0.75,
                keywords=["evaluation", "failure", "difficulty_override", "council"],
                severity="HIGH",
            ),
            AgentExperienceRecord(
                agent_name="ResourceRecommendationAgent",
                problem="学生 self_regulation 低但未减少单次资源量",
                cause="推荐逻辑未考虑自我调节能力维度",
                solution="self_regulation<0.4 → 单次推荐上限从 8 降至 4, 每资源 estimated_minutes 上限 25min",
                strategy_key="self_regulation_pacing",
                success_rate=0.70,
                keywords=["self_regulation", "pacing", "recommendation"],
                severity="MEDIUM",
            ),
        ]
        for rec in defaults:
            self._records[rec.record_id] = rec
        self._save()

    @property
    def record_count(self) -> int:
        return len(self._records)
