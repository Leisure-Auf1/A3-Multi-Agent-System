"""
Experience Memory — Agent 失败经验库

存储来自 UserSim / ReviewGate / MetaReflector 的经验教训。
第一阶段: JSON + 关键词搜索。
接口设计: 未来可替换 ChromaDB / Vector DB。
"""

from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

@dataclass
class ExperienceRecord:
    """一条失败经验"""

    record_id: str

    # 问题描述
    problem: str                           # 问题摘要
    cause: str                             # 根因分析
    context: str                           # 情境 (课程/节点/画像)
    solution: str                          # 解决方案
    applicable_profile: str = ""           # 适用画像类型

    # 统计
    success_rate: float = 0.0              # 此方案成功率 0-1
    usage_count: int = 0                   # 被使用次数
    last_used: str = ""                    # 最后使用时间

    # 来源
    source: str = "unknown"                # usersim | reviewgate | metareflector
    node_id: str = ""                      # 关联节点
    severity: str = "MEDIUM"               # LOW | MEDIUM | HIGH | CRITICAL

    # 关键词 (自动提取 + 手动标注)
    keywords: List[str] = field(default_factory=list)

    # 元数据
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "problem": self.problem,
            "cause": self.cause,
            "context": self.context,
            "solution": self.solution,
            "applicable_profile": self.applicable_profile,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "last_used": self.last_used,
            "source": self.source,
            "node_id": self.node_id,
            "severity": self.severity,
            "keywords": self.keywords,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperienceRecord":
        return cls(
            record_id=data["record_id"],
            problem=data.get("problem", ""),
            cause=data.get("cause", ""),
            context=data.get("context", ""),
            solution=data.get("solution", ""),
            applicable_profile=data.get("applicable_profile", ""),
            success_rate=data.get("success_rate", 0.0),
            usage_count=data.get("usage_count", 0),
            last_used=data.get("last_used", ""),
            source=data.get("source", "unknown"),
            node_id=data.get("node_id", ""),
            severity=data.get("severity", "MEDIUM"),
            keywords=data.get("keywords", []),
            created_at=data.get("created_at", ""),
        )


# ──────────────────────────────────────────────
# 存储层
# ──────────────────────────────────────────────

class ExperienceMemoryStore:
    """
    Agent 经验库.

    存储路径: storage/memory/experience/records.json

    使用:
        store = ExperienceMemoryStore()
        store.add_lesson(
            problem="闭包概念过载",
            cause="一节引入 5 个新概念",
            context="node-1 / python_beginner",
            solution="拆分为 3 节, 每节 ≤ 3 概念",
            source="usersim",
        )
        results = store.search_similar("概念密度过高")
        relevant = store.get_relevant_lessons("closures", "python_beginner")
    """

    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir:
            self._dir = Path(storage_dir)
        else:
            base = Path(__file__).resolve().parent.parent.parent
            self._dir = base / "storage" / "memory" / "experience"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._file = self._dir / "records.json"
        self._records: Dict[str, ExperienceRecord] = {}
        self._load()

    def _load(self) -> None:
        if self._file.exists():
            raw = json.loads(self._file.read_text())
            self._records = {
                rid: ExperienceRecord.from_dict(r)
                for rid, r in raw.items()
            }

    def _save(self) -> None:
        data = {rid: r.to_dict() for rid, r in self._records.items()}
        self._file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    # ── 增删查 ────────────────────────────

    def add_lesson(
        self,
        problem: str,
        cause: str,
        context: str,
        solution: str,
        source: str = "unknown",
        node_id: str = "",
        applicable_profile: str = "",
        severity: str = "MEDIUM",
        keywords: Optional[List[str]] = None,
    ) -> ExperienceRecord:
        """
        添加一条经验教训.

        Args:
            problem: 问题摘要
            cause: 根因
            context: 情境描述
            solution: 解决方案
            source: 来源 (usersim/reviewgate/metareflector)
        """
        # 去重 — 相同问题+相同根因
        for rid, existing in self._records.items():
            if (existing.problem == problem and existing.cause == cause):
                existing.usage_count += 1
                existing.last_used = datetime.now(timezone.utc).isoformat()
                self._save()
                return existing

        # 自动提取关键词
        if keywords is None:
            keywords = self._extract_keywords(f"{problem} {cause} {solution}")

        rid = f"exp_{len(self._records) + 1:04d}"
        record = ExperienceRecord(
            record_id=rid,
            problem=problem,
            cause=cause,
            context=context,
            solution=solution,
            applicable_profile=applicable_profile,
            source=source,
            node_id=node_id,
            severity=severity,
            keywords=keywords,
            usage_count=1,
        )
        self._records[rid] = record
        self._save()
        return record

    def get_lesson(self, record_id: str) -> Optional[ExperienceRecord]:
        return self._records.get(record_id)

    # ── 搜索 ──────────────────────────────

    def search_similar(
        self,
        query: str,
        limit: int = 5,
        source_filter: Optional[str] = None,
    ) -> List[ExperienceRecord]:
        """
        关键词搜索相似经验.

        Args:
            query: 搜索查询
            limit: 返回数量
            source_filter: 按来源过滤

        Returns:
            匹配的经验记录列表 (按相关度排序)
        """
        query_lower = query.lower()
        scored: List[tuple[int, ExperienceRecord]] = []

        for record in self._records.values():
            if source_filter and record.source != source_filter:
                continue

            # 计算匹配分
            score = 0
            search_text = (
                f"{record.problem} {record.cause} "
                f"{record.context} {record.solution} "
                f"{' '.join(record.keywords)}"
            ).lower()

            # 查询词命中
            for word in query_lower.split():
                if word in search_text:
                    score += 2
                # 子串匹配
                for kw in record.keywords:
                    if word in kw.lower() or kw.lower() in word:
                        score += 1

            # 成功率高 + 使用多的加权
            score += int(record.success_rate * 5)
            score += min(record.usage_count, 5)

            if score > 0:
                scored.append((score, record))

        scored.sort(key=lambda x: -x[0])
        return [r for _, r in scored[:limit]]

    def get_relevant_lessons(
        self,
        node_id: str = "",
        profile_type: str = "",
        limit: int = 3,
    ) -> List[ExperienceRecord]:
        """
        获取与特定节点/画像相关的经验.

        优先匹配:
          1. 相同 node_id
          2. 匹配画像类型
          3. 最近添加的
        """
        candidates: List[tuple[int, ExperienceRecord]] = []

        for record in self._records.values():
            score = 0
            if node_id and record.node_id == node_id:
                score += 10
            if profile_type and profile_type in record.applicable_profile:
                score += 5
            if profile_type and profile_type in record.context:
                score += 3
            # 最近使用的加分
            if record.last_used:
                score += min(record.usage_count, 3)

            if score > 0 or not node_id:  # 无 node_id 时返回所有
                candidates.append((score, record))

        candidates.sort(key=lambda x: -x[0])
        return [r for _, r in candidates[:limit]]

    # ── 反馈更新 ──────────────────────────

    def update_success_rate(
        self,
        record_id: str,
        was_successful: bool,
    ) -> None:
        """更新方案成功率"""
        record = self._records.get(record_id)
        if not record:
            return
        # 指数移动加权平均
        delta = 0.3 if was_successful else -0.1
        new_rate = max(0.0, min(1.0, record.success_rate * 0.7 + 0.5 * (0.3 if was_successful else 0)))
        record.success_rate = round(new_rate, 2)
        record.usage_count += 1
        record.last_used = datetime.now(timezone.utc).isoformat()
        self._save()

    # ── 批量导入 ──────────────────────────

    def seed_default_lessons(self) -> None:
        """预置通用经验教训"""
        defaults = [
            {
                "problem": "概念密度过高, 学生认知过载",
                "cause": "一节引入超过 3 个新概念, 初学者无法消化",
                "context": "任意课程 / 初学者画像",
                "solution": "将大节拆为小节, 每节 ≤ 3 个新概念, 用比喻引入",
                "source": "usersim",
                "severity": "HIGH",
            },
            {
                "problem": "学院派定义让学生失去兴趣",
                "cause": "使用了'是由...组成的实体'等教科书式表述",
                "context": "python_beginner_hates_theory 画像",
                "solution": "用 ❌ vs ✅ 对比块替代定义, 先展示问题再给方案",
                "source": "usersim",
                "severity": "MEDIUM",
            },
            {
                "problem": "缺少视觉辅助, visual_learner 理解困难",
                "cause": "未使用 ASCII 图/Mermaid 拓扑展示底层结构",
                "context": "visual_learner_hates_magic 画像",
                "solution": "每个关键概念配 ASCII 字符画或 Mermaid 图",
                "source": "usersim",
                "severity": "MEDIUM",
            },
            {
                "problem": "代码缺少类型注解, AST Gate 拒绝",
                "cause": "LLM 倾向省略类型注解",
                "context": "任意 / AST Gate 检查",
                "solution": "所有函数必须含完整类型注解, ≥50% 函数有注解",
                "source": "reviewgate",
                "severity": "HIGH",
            },
            {
                "problem": "练习题与讲义存在知识断层",
                "cause": "练习题使用了讲义未教的概念 (*args, @wraps 等)",
                "context": "任意 / UserSim mind-gap 分析",
                "solution": "生成练习题前检查: 所需概念 ⊆ 讲义已教概念",
                "source": "metareflector",
                "severity": "HIGH",
            },
        ]
        for d in defaults:
            self.add_lesson(**d)

    # ── 统计 ──────────────────────────────

    def stats(self) -> Dict[str, Any]:
        return {
            "total_lessons": len(self._records),
            "by_source": self._count_by("source"),
            "by_severity": self._count_by("severity"),
            "avg_success_rate": round(
                sum(r.success_rate for r in self._records.values())
                / max(len(self._records), 1), 2
            ),
        }

    def _count_by(self, field: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for r in self._records.values():
            val = getattr(r, field, "unknown")
            counts[val] = counts.get(val, 0) + 1
        return counts

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """简单关键词提取"""
        # 中文按常见分隔切分
        words = re.split(r"[，。,\s]+", text)
        # 过滤短词
        return [w.strip() for w in words if len(w.strip()) >= 2][:10]
