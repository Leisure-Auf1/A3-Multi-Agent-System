"""
A3 v4 — Knowledge Graph: 知识点数据结构

知识图谱核心数据模型:
  KnowledgeNode — 知识节点 (概念/技能/方法/原理/工具)
  KnowledgeEdge — 依赖关系边 (PREREQ_OF / RELATED_TO / ASSESSED_BY / TAUGHT_BY)
  KnowledgeGraph — 完整知识图谱
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class ConceptType(str, Enum):
    CONCEPT = "concept"        # 概念型: "向量嵌入"
    SKILL = "skill"            # 技能型: "Python 编码"
    METHOD = "method"          # 方法型: "反向传播"
    PRINCIPLE = "principle"    # 原理型: "注意力机制原理"
    TOOL = "tool"              # 工具型: "LangChain 框架"


class EdgeType(str, Enum):
    PREREQ_OF = "PREREQ_OF"           # A 是 B 的前置知识
    STRONG_RELATED = "STRONG_RELATED_TO"
    WEAK_RELATED = "WEAK_RELATED_TO"
    ASSESSED_BY = "ASSESSED_BY"       # 该概念可通过某习题评估
    TAUGHT_BY = "TAUGHT_BY"           # 该概念可由某资源教学


@dataclass
class KnowledgeNode:
    """知识图谱节点 — 单个知识点"""
    concept_id: str = ""              # 唯一标识: "kg:ma:agent_communication"
    concept_name: str = ""            # 知识点名称: "Agent 通信协议"
    concept_type: ConceptType = ConceptType.CONCEPT
    description: str = ""
    difficulty: float = 0.5           # 0.0-1.0
    chapter: str = ""                 # 所属章节
    prerequisites: List[str] = field(default_factory=list)  # 前置知识 concept_id 列表
    related_resources: List[str] = field(default_factory=list)  # 关联资源 ID
    mastery_threshold: float = 0.8    # 掌握阈值 (≥此值视为已掌握)
    estimated_minutes: int = 15       # 预估学习时间
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "concept_name": self.concept_name,
            "concept_type": self.concept_type.value,
            "description": self.description,
            "difficulty": self.difficulty,
            "chapter": self.chapter,
            "prerequisites": self.prerequisites,
            "related_resources": self.related_resources,
            "mastery_threshold": self.mastery_threshold,
            "estimated_minutes": self.estimated_minutes,
            "keywords": self.keywords,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeNode":
        ct = data.get("concept_type", "concept")
        if isinstance(ct, str):
            ct = ConceptType(ct)
        return cls(
            concept_id=data.get("concept_id", ""),
            concept_name=data.get("concept_name", ""),
            concept_type=ct,
            description=data.get("description", ""),
            difficulty=data.get("difficulty", 0.5),
            chapter=data.get("chapter", ""),
            prerequisites=data.get("prerequisites", []),
            related_resources=data.get("related_resources", []),
            mastery_threshold=data.get("mastery_threshold", 0.8),
            estimated_minutes=data.get("estimated_minutes", 15),
            keywords=data.get("keywords", []),
        )


@dataclass
class KnowledgeEdge:
    """知识图谱边 — 知识点间关系"""
    source_id: str                    # 前置知识
    target_id: str                    # 后继知识
    edge_type: EdgeType = EdgeType.PREREQ_OF
    weight: float = 1.0               # 关系强度 / 学习难度代价
    rationale: str = ""               # 建立此关系的依据

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value,
            "weight": self.weight,
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeEdge":
        et = data.get("edge_type", "PREREQ_OF")
        if isinstance(et, str):
            et = EdgeType(et)
        return cls(
            source_id=data.get("source_id", ""),
            target_id=data.get("target_id", ""),
            edge_type=et,
            weight=data.get("weight", 1.0),
            rationale=data.get("rationale", ""),
        )


@dataclass
class KnowledgeGraph:
    """完整知识图谱"""
    nodes: Dict[str, KnowledgeNode] = field(default_factory=dict)
    edges: List[KnowledgeEdge] = field(default_factory=list)
    course_name: str = ""
    version: str = "1.0"

    def add_node(self, node: KnowledgeNode) -> None:
        self.nodes[node.concept_id] = node

    def add_edge(self, edge: KnowledgeEdge) -> None:
        self.edges.append(edge)

    def get_prerequisites(self, concept_id: str) -> List[KnowledgeNode]:
        """获取直接前置知识列表。"""
        prereqs = []
        for edge in self.edges:
            if edge.target_id == concept_id and edge.edge_type == EdgeType.PREREQ_OF:
                if edge.source_id in self.nodes:
                    prereqs.append(self.nodes[edge.source_id])
        return prereqs

    def get_all_prerequisites(self, concept_id: str, visited: Optional[Set[str]] = None) -> List[KnowledgeNode]:
        """递归获取所有传递前置知识。"""
        if visited is None:
            visited = set()
        if concept_id in visited:
            return []
        visited.add(concept_id)
        result: List[KnowledgeNode] = []
        for prereq in self.get_prerequisites(concept_id):
            result.append(prereq)
            result.extend(self.get_all_prerequisites(prereq.concept_id, visited))
        return result

    def get_dependents(self, concept_id: str) -> List[KnowledgeNode]:
        """获取依赖此概念的后继知识列表。"""
        deps = []
        for edge in self.edges:
            if edge.source_id == concept_id and edge.edge_type == EdgeType.PREREQ_OF:
                if edge.target_id in self.nodes:
                    deps.append(self.nodes[edge.target_id])
        return deps

    def to_dict(self) -> Dict[str, Any]:
        return {
            "course_name": self.course_name,
            "version": self.version,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeGraph":
        kg = cls(
            course_name=data.get("course_name", ""),
            version=data.get("version", "1.0"),
        )
        for nd in data.get("nodes", []):
            node = KnowledgeNode.from_dict(nd)
            kg.add_node(node)
        for ed in data.get("edges", []):
            edge = KnowledgeEdge.from_dict(ed)
            kg.add_edge(edge)
        return kg


@dataclass
class KnowledgeGap:
    """知识缺口诊断结果"""
    target_concept: str                     # 目标概念
    mastered_concepts: List[str] = field(default_factory=list)     # 已掌握
    missing_prerequisites: List[str] = field(default_factory=list)  # 缺失前置
    weak_concepts: List[str] = field(default_factory=list)         # 薄弱 (< 0.5)
    ready_concepts: List[str] = field(default_factory=list)        # 可立即学习
    recommended_sequence: List[str] = field(default_factory=list)  # 推荐学习路径


@dataclass
class PathResult:
    """最优学习路径规划结果"""
    ordered_nodes: List[str] = field(default_factory=list)         # 拓扑排序序列
    total_minutes: int = 0
    critical_path: List[str] = field(default_factory=list)         # 关键路径 (最长依赖链)
    skipped_nodes: List[str] = field(default_factory=list)         # 已掌握跳过
    boosted_nodes: List[str] = field(default_factory=list)         # 薄弱加强
    alternative_paths: List[List[str]] = field(default_factory=list)  # 替代路径

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ordered_nodes": self.ordered_nodes,
            "total_minutes": self.total_minutes,
            "critical_path": self.critical_path,
            "skipped_nodes": self.skipped_nodes,
            "boosted_nodes": self.boosted_nodes,
            "alternative_paths": self.alternative_paths,
        }
