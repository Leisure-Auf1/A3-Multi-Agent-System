"""
Phase 4 HITL — 升级结构化契约库
FuseReport: 工单状态追溯 + 犯罪现场 MD5 账本
FailurePatternLesson: 增加 source 字段 (agent/human) + FileMetadata
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class FileMetadata:
    """文件元数据 — MD5 哈希账本"""
    file_path: str
    md5_hash: str
    file_size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "md5_hash": self.md5_hash,
            "file_size_bytes": self.file_size_bytes,
        }


@dataclass
class FuseReport:
    """熔断工单 — 犯罪现场完整追溯"""
    ticket_id: str
    node_id: str
    timestamp: str = ""
    final_score: float = 0.0
    exhausted_rounds: int = 3
    failure_stage: str = "UNKNOWN"  # AST_GATE | PYTEST_GATE | USER_SIM
    raw_error_traceback: str = ""
    agent_cognitive_blindspot: str = ""
    frozen_assets: List[FileMetadata] = field(default_factory=list)
    transaction_status: str = "PENDING_HITL"  # PENDING_HITL | RESOLVED_BY_HUMAN
    resolution_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "node_id": self.node_id,
            "timestamp": self.timestamp,
            "final_score": self.final_score,
            "exhausted_rounds": self.exhausted_rounds,
            "failure_stage": self.failure_stage,
            "raw_error_traceback": self.raw_error_traceback,
            "agent_cognitive_blindspot": self.agent_cognitive_blindspot,
            "frozen_assets": [fa.to_dict() for fa in self.frozen_assets],
            "transaction_status": self.transaction_status,
            "resolution_timestamp": self.resolution_timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FuseReport":
        assets = [FileMetadata(**fa) for fa in data.get("frozen_assets", [])]
        return cls(
            ticket_id=data["ticket_id"],
            node_id=data["node_id"],
            timestamp=data.get("timestamp", ""),
            final_score=data.get("final_score", 0.0),
            exhausted_rounds=data.get("exhausted_rounds", 3),
            failure_stage=data.get("failure_stage", "UNKNOWN"),
            raw_error_traceback=data.get("raw_error_traceback", ""),
            agent_cognitive_blindspot=data.get("agent_cognitive_blindspot", ""),
            frozen_assets=assets,
            transaction_status=data.get("transaction_status", "PENDING_HITL"),
            resolution_timestamp=data.get("resolution_timestamp", ""),
        )


@dataclass
class FailurePatternLesson:
    """结构化教训 — 支持 agent 自愈 / human 仲裁 双源"""
    error_type: str
    problem_context: str
    root_cause_analysis: str
    anti_pattern_code: str
    golden_patch_code: str
    abstract_lint_rule: str
    source: str = "agent"  # agent | human
    node_id: str = ""
    severity: str = "HIGH"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "problem_context": self.problem_context,
            "root_cause_analysis": self.root_cause_analysis,
            "anti_pattern_code": self.anti_pattern_code,
            "golden_patch_code": self.golden_patch_code,
            "abstract_lint_rule": self.abstract_lint_rule,
            "source": self.source,
            "node_id": self.node_id,
            "severity": self.severity,
            "created_at": self.created_at,
            "tags": self.tags,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FailurePatternLesson":
        return cls(
            error_type=data["error_type"],
            problem_context=data["problem_context"],
            root_cause_analysis=data["root_cause_analysis"],
            anti_pattern_code=data["anti_pattern_code"],
            golden_patch_code=data["golden_patch_code"],
            abstract_lint_rule=data["abstract_lint_rule"],
            source=data.get("source", "agent"),
            node_id=data.get("node_id", ""),
            severity=data.get("severity", "HIGH"),
            created_at=data.get("created_at", ""),
            tags=data.get("tags", []),
        )

    @classmethod
    def from_json(cls, raw: str) -> "FailurePatternLesson":
        return cls.from_dict(json.loads(raw))

    def semantic_anchor(self) -> str:
        return (
            f"[{self.source.upper()}] Error: {self.error_type}. "
            f"Context: {self.problem_context}. Rule: {self.abstract_lint_rule}"
        )


@dataclass
class FeedbackRecord:
    """反馈闭环记录 — 串联 UserSim → MetaReflector → Prompt 优化"""
    record_id: str
    node_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # 来源: UserSimulation
    sim_score: int = 0                               # UserSim 评分 (0-100)
    would_drop_out: bool = False                      # 是否会弃课
    revision_required: bool = False                   # 是否需要修改
    top_issues: List[str] = field(default_factory=list)  # top 问题列表

    # 来源: MetaReflector
    recalled_lessons: List[Dict[str, Any]] = field(default_factory=list)  # 召回教训
    prompt_refinement: str = ""                       # 优化后的 Prompt 片段
    refinement_rationale: str = ""                    # 优化理由

    # 元数据
    cycle_number: int = 0                             # 第几轮反馈循环
    effect_delta: Optional[int] = None                # 优化后评分变化
    status: str = "PENDING"                           # PENDING | OPTIMIZED | APPLIED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "node_id": self.node_id,
            "timestamp": self.timestamp,
            "sim_score": self.sim_score,
            "would_drop_out": self.would_drop_out,
            "revision_required": self.revision_required,
            "top_issues": self.top_issues,
            "recalled_lessons": self.recalled_lessons,
            "prompt_refinement": self.prompt_refinement,
            "refinement_rationale": self.refinement_rationale,
            "cycle_number": self.cycle_number,
            "effect_delta": self.effect_delta,
            "status": self.status,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeedbackRecord":
        return cls(
            record_id=data["record_id"],
            node_id=data.get("node_id", ""),
            timestamp=data.get("timestamp", ""),
            sim_score=data.get("sim_score", 0),
            would_drop_out=data.get("would_drop_out", False),
            revision_required=data.get("revision_required", False),
            top_issues=data.get("top_issues", []),
            recalled_lessons=data.get("recalled_lessons", []),
            prompt_refinement=data.get("prompt_refinement", ""),
            refinement_rationale=data.get("refinement_rationale", ""),
            cycle_number=data.get("cycle_number", 0),
            effect_delta=data.get("effect_delta"),
            status=data.get("status", "PENDING"),
        )


BUILTIN_LESSONS: List[FailurePatternLesson] = [
    FailurePatternLesson(
        source="agent",
        error_type="CognitiveOverload",
        problem_context="Node 1: 单节10概念超过学生认知上限3",
        root_cause_analysis="大模型低估初学者认知负荷——知识诅咒",
        anti_pattern_code="# 整节堆10个概念\n## 全部概念\n- 闭包 - 高阶函数 - 装饰器 - ...",
        golden_patch_code="## §1.1 函数是对象 (3概念)\n## §1.2 闭包 (3概念)\n## §1.3 装饰器 (4概念)",
        abstract_lint_rule="每节新概念 ≤ 3, 用比喻引入",
        node_id="node-1", severity="CRITICAL", tags=["cognitive-load"],
    ),
    FailurePatternLesson(
        source="agent",
        error_type="TypeAnnotationMissing",
        problem_context="Node 2: AST Gate 拒绝—类型注解0%",
        root_cause_analysis="LLM生成代码倾向省略类型注解",
        anti_pattern_code="def retry(max_tries=3):\n    def decorator(func): ...",
        golden_patch_code="def retry(max_tries:int=3)->Callable:\n    def decorator(func:Callable)->Callable: ...",
        abstract_lint_rule="生成函数必须含完整类型注解 ≥50%",
        node_id="node-2", severity="HIGH", tags=["type-hints"],
    ),
    FailurePatternLesson(
        source="agent",
        error_type="ProbeDetectionFalseNegative",
        problem_context="Node 1: get_logger返回空壳导致AttributeError",
        root_cause_analysis="空壳函数有名字但无实现, 名字检查通过但装饰器返回None",
        anti_pattern_code="if logger_func.__name__ != 'logger': ...  # 空壳pass有名字!",
        golden_patch_code="try:\n  @logger_func\n  def _probe():return 42\n  if _probe()==42:return logger_func\nexcept:pass\nreturn test_solution_logger()",
        abstract_lint_rule="学生代码加载器必须用probe实际装饰验证, 不能仅检查函数名",
        node_id="node-1", severity="HIGH", tags=["probe"],
    ),
    FailurePatternLesson(
        source="agent",
        error_type="BackwardValidationBypass",
        problem_context="Node 2: Gate反向验证被probe自动兜底绕过",
        root_cause_analysis="Probe与Gate反向验证冲突—fallback绕过骨架失败约束",
        anti_pattern_code="# Gate直接跑含probe的原始测试文件\nsubprocess.run(['pytest','test_case.py'])",
        golden_patch_code="# Gate用剥壳测试(无fallback)\nstripped='from exercise import retry\\ndef test():...'\nsubprocess.run(['pytest',tmp_test])",
        abstract_lint_rule="Gate反向验证必须用无fallback的剥壳测试",
        node_id="node-2", severity="HIGH", tags=["review-gate"],
    ),
    FailurePatternLesson(
        source="agent",
        error_type="PropertySetterExtractorGap",
        problem_context="Node 3: UserSim误报'property setter'未教",
        root_cause_analysis="概念提取器字符串匹配, 未识别.setter等价于property setter",
        anti_pattern_code="if 'property setter' not in taught_concepts: gaps.append(...)",
        golden_patch_code="code_patterns={'property setter':r'\\.setter'}\nif re.search(code_patterns['property setter'],lecture_text): taught_concepts.append('property setter')",
        abstract_lint_rule="概念匹配需三管齐下: 名称/代码模式/上下文别名",
        node_id="node-3", severity="MEDIUM", tags=["extractor"],
    ),
]
