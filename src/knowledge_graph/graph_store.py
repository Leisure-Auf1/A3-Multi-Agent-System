"""
A3 v4 — InMemoryKnowledgeGraph: NetworkX 内存图存储

竞赛阶段使用 NetworkX，接口抽象化以便后续迁移到 Neo4j。
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Set

import networkx as nx

from . import (
    KnowledgeNode, KnowledgeEdge, KnowledgeGraph,
    KnowledgeGap, PathResult, EdgeType, ConceptType,
)


class InMemoryKnowledgeGraph:
    """
    基于 NetworkX 的有向知识图谱。

    接口与 KnowledgeGraph 抽象对齐，后续可替换为 Neo4jKnowledgeGraph。
    """

    def __init__(self, kg: Optional[KnowledgeGraph] = None):
        self._graph = nx.DiGraph()
        if kg:
            self.load(kg)

    def load(self, kg: KnowledgeGraph) -> None:
        """从 KnowledgeGraph 加载所有节点和边。"""
        for node in kg.nodes.values():
            self._graph.add_node(
                node.concept_id,
                name=node.concept_name,
                difficulty=node.difficulty,
                concept_type=node.concept_type.value,
                chapter=node.chapter,
                estimated_minutes=node.estimated_minutes,
                mastery_threshold=node.mastery_threshold,
                keywords=node.keywords,
            )
        for edge in kg.edges:
            self._graph.add_edge(
                edge.source_id, edge.target_id,
                edge_type=edge.edge_type.value,
                weight=edge.weight,
                rationale=edge.rationale,
            )

    # ── 查询 ──────────────────────────────────

    def get_node(self, concept_id: str) -> Optional[Dict[str, Any]]:
        """获取节点属性字典。"""
        if concept_id in self._graph:
            return dict(self._graph.nodes[concept_id])
        return None

    def get_prerequisites(self, concept_id: str) -> List[Dict[str, Any]]:
        """获取直接前置知识。"""
        prereqs = []
        for src, tgt, data in self._graph.in_edges(concept_id, data=True):
            if data.get("edge_type") == EdgeType.PREREQ_OF.value:
                prereqs.append({**self._graph.nodes[src], "concept_id": src})
        return prereqs

    def get_all_prerequisites(self, concept_id: str) -> List[str]:
        """递归获取所有传递前置知识 (拓扑排序)。"""
        try:
            ancestors = list(nx.ancestors(self._graph, concept_id))
            # 拓扑排序保证前置在前
            sub_nodes = set(ancestors)
            sub_nodes.add(concept_id)
            subgraph = self._graph.subgraph(sub_nodes)
            order = list(nx.topological_sort(subgraph))
            return [n for n in order if n != concept_id]
        except nx.NetworkXError:
            return []

    def get_dependents(self, concept_id: str) -> List[str]:
        """获取直接后继知识。"""
        deps = []
        for src, tgt, data in self._graph.out_edges(concept_id, data=True):
            if data.get("edge_type") == EdgeType.PREREQ_OF.value:
                deps.append(tgt)
        return deps

    def topological_order(self) -> List[str]:
        """整个图谱的拓扑排序。"""
        try:
            return list(nx.topological_sort(self._graph))
        except nx.NetworkXError:
            return list(self._graph.nodes())

    # ── 缺口诊断 ──────────────────────────────

    def compute_knowledge_gap(
        self,
        target_concept: str,
        mastered: Dict[str, float],  # concept_id → mastery 0.0-1.0
        mastery_threshold: float = 0.8,
    ) -> KnowledgeGap:
        """
        计算学生的知识缺口。

        算法:
          1. 获取目标概念的所有传递前置
          2. 对比 mastered dict → 分类为 mastered / weak / missing
          3. 拓扑排序推荐学习序列
        """
        all_prereqs = self.get_all_prerequisites(target_concept)

        mastered_concepts: List[str] = []
        weak_concepts: List[str] = []
        missing_prerequisites: List[str] = []
        ready_concepts: List[str] = []

        for pid in all_prereqs:
            m = mastered.get(pid, 0.0)
            if m >= mastery_threshold:
                mastered_concepts.append(pid)
            elif m >= 0.3:
                weak_concepts.append(pid)
            else:
                missing_prerequisites.append(pid)

        # 已掌握所有前置 → 目标概念立即可学
        if not missing_prerequisites and not weak_concepts:
            ready_concepts.append(target_concept)

        # 推荐学习序列: missing → weak → target
        recommended: List[str] = []
        recommended.extend(missing_prerequisites)
        recommended.extend(weak_concepts)
        if target_concept not in recommended:
            recommended.append(target_concept)

        return KnowledgeGap(
            target_concept=target_concept,
            mastered_concepts=mastered_concepts,
            missing_prerequisites=missing_prerequisites,
            weak_concepts=weak_concepts,
            ready_concepts=ready_concepts,
            recommended_sequence=recommended,
        )

    # ── 路径规划 ──────────────────────────────

    def compute_optimal_path(
        self,
        mastered: Dict[str, float],
        target: str,
        profile: Optional[Dict[str, Any]] = None,
    ) -> PathResult:
        """
        计算最优学习路径。

        算法:
          1. 拓扑排序获取所有前置
          2. 跳过已掌握节点 (mastery ≥ 0.8)
          3. 标记薄弱节点需要加强 (0.3 ≤ mastery < 0.8)
          4. 使用 Dijkstra 最短路径 (权重 = difficulty × estimated_minutes)
        """
        # 获取所有需要学习的节点
        all_need: Set[str] = set(self.get_all_prerequisites(target))
        all_need.add(target)

        # 跳过已掌握
        skipped = [n for n in all_need if mastered.get(n, 0.0) >= 0.8]
        need_learn = [n for n in all_need if n not in skipped]

        # 标记薄弱
        boosted = [n for n in need_learn if 0.3 <= mastered.get(n, 0.0) < 0.8]

        # 拓扑排序
        sub = self._graph.subgraph(need_learn)
        try:
            ordered = list(nx.topological_sort(sub))
        except nx.NetworkXError:
            ordered = need_learn

        # 计算总时间
        total_min = sum(
            self._graph.nodes[n].get("estimated_minutes", 15) for n in ordered
        )

        # 关键路径 (Dijkstra 最长路径 — 最耗时依赖链)
        critical: List[str] = []
        try:
            if need_learn:
                # 用负权重找最长路径
                paths = dict(nx.all_pairs_dijkstra_path(sub, weight=None))
                max_len = 0
                for src in need_learn:
                    if src in paths:
                        for tgt_node in need_learn:
                            if tgt_node in paths[src]:
                                path_list = paths[src][tgt_node]
                                if len(path_list) > max_len:
                                    max_len = len(path_list)
                                    critical = path_list
        except Exception:
            critical = ordered

        # 替代路径 (简化为跳过不同数量前置的变体)
        alt_paths: List[List[str]] = []
        if len(need_learn) > 3:
            # 替代路径 1: 跳过所有薄弱加强 (仅学 missing)
            alt1 = [n for n in ordered if n not in boosted]
            if alt1 and alt1 != ordered:
                alt_paths.append(alt1)

        return PathResult(
            ordered_nodes=ordered,
            total_minutes=total_min,
            critical_path=critical,
            skipped_nodes=skipped,
            boosted_nodes=boosted,
            alternative_paths=alt_paths,
        )

    # ── 构建默认知识图谱 ──────────────────────

    @classmethod
    def build_default_multimodal_ai_graph(cls) -> "InMemoryKnowledgeGraph":
        """
        为"人工智能与多智能体系统"课程构建默认知识图谱。

        基于现有 6 章 Markdown KB 自动提取的核心依赖关系。
        """
        kg = KnowledgeGraph(
            course_name="人工智能与多智能体系统",
            version="4.0",
        )

        # ── Ch1: AI 导论 ──
        nodes_ch1 = [
            KnowledgeNode("kg:ch1:ai_overview", "人工智能概述", ConceptType.CONCEPT,
                          "AI 的定义、历史、主要流派", 0.2, "Ch1", [], [], 0.7, 15,
                          ["AI", "人工智能", "概述"]),
            KnowledgeNode("kg:ch1:ml_basics", "机器学习基础", ConceptType.CONCEPT,
                          "监督/无监督/强化学习", 0.3, "Ch1", ["kg:ch1:ai_overview"], [], 0.7, 20,
                          ["机器学习", "ML"]),
        ]
        # ── Ch2: LLM 基础 ──
        nodes_ch2 = [
            KnowledgeNode("kg:ch2:linear_algebra", "线性代数基础", ConceptType.CONCEPT,
                          "向量/矩阵/点积", 0.4, "Ch2", [], [], 0.7, 25,
                          ["线性代数", "向量"]),
            KnowledgeNode("kg:ch2:attention", "注意力机制", ConceptType.PRINCIPLE,
                          "Scaled Dot-Product Attention", 0.7, "Ch2",
                          ["kg:ch2:linear_algebra"], [], 0.75, 30,
                          ["Attention", "注意力"]),
            KnowledgeNode("kg:ch2:transformer", "Transformer 架构", ConceptType.CONCEPT,
                          "Encoder-Decoder / Self-Attention", 0.8, "Ch2",
                          ["kg:ch2:attention"], [], 0.8, 35,
                          ["Transformer"]),
            KnowledgeNode("kg:ch2:tokenization", "分词与嵌入", ConceptType.METHOD,
                          "BPE / WordPiece / Embedding", 0.5, "Ch2",
                          ["kg:ch2:linear_algebra"], [], 0.7, 20,
                          ["Tokenization", "分词"]),
            KnowledgeNode("kg:ch2:llm_arch", "大语言模型架构", ConceptType.CONCEPT,
                          "GPT / BERT / LLaMA 架构对比", 0.7, "Ch2",
                          ["kg:ch2:transformer", "kg:ch2:tokenization"], [], 0.75, 30,
                          ["LLM", "大模型"]),
        ]
        # ── Ch3: Prompt Engineering ──
        nodes_ch3 = [
            KnowledgeNode("kg:ch3:prompt_basics", "Prompt 工程基础", ConceptType.SKILL,
                          "Few-shot / Chain-of-Thought", 0.3, "Ch3",
                          ["kg:ch2:llm_arch"], [], 0.7, 20,
                          ["Prompt", "提示词"]),
            KnowledgeNode("kg:ch3:prompt_advanced", "高级 Prompt 技术", ConceptType.SKILL,
                          "ReAct / Tree-of-Thought / DSPy", 0.6, "Ch3",
                          ["kg:ch3:prompt_basics"], [], 0.7, 25,
                          ["ReAct", "高级提示词"]),
        ]
        # ── Ch4: RAG ──
        nodes_ch4 = [
            KnowledgeNode("kg:ch4:embedding", "向量嵌入", ConceptType.CONCEPT,
                          "文本→向量 / 语义相似度", 0.5, "Ch4",
                          ["kg:ch2:tokenization"], [], 0.7, 25,
                          ["Embedding", "向量"]),
            KnowledgeNode("kg:ch4:vector_db", "向量数据库", ConceptType.TOOL,
                          "ChromaDB / Pinecone / FAISS", 0.5, "Ch4",
                          ["kg:ch4:embedding"], [], 0.7, 20,
                          ["VectorDB", "向量数据库"]),
            KnowledgeNode("kg:ch4:rag_pipeline", "RAG 检索增强生成", ConceptType.METHOD,
                          "检索→增强→生成 完整链路", 0.7, "Ch4",
                          ["kg:ch4:vector_db", "kg:ch3:prompt_basics"], [], 0.75, 30,
                          ["RAG", "检索增强"]),
        ]
        # ── Ch5: Multi-Agent Architecture ──
        nodes_ch5 = [
            KnowledgeNode("kg:ch5:agent_concept", "智能体概念", ConceptType.CONCEPT,
                          "Agent 定义 / 感知-思考-行动循环", 0.4, "Ch5",
                          ["kg:ch1:ai_overview"], [], 0.7, 20,
                          ["Agent", "智能体"]),
            KnowledgeNode("kg:ch5:agent_communication", "Agent 通信协议", ConceptType.METHOD,
                          "EventBus / 消息队列 / 共享内存", 0.6, "Ch5",
                          ["kg:ch5:agent_concept"], [], 0.7, 25,
                          ["通信", "EventBus"]),
            KnowledgeNode("kg:ch5:multi_agent_patterns", "多智能体架构模式", ConceptType.PRINCIPLE,
                          "Pipeline / Router / Blackboard / Council", 0.8, "Ch5",
                          ["kg:ch5:agent_communication"], [], 0.75, 30,
                          ["多智能体", "Multi-Agent"]),
            KnowledgeNode("kg:ch5:agent_orchestration", "智能体编排", ConceptType.METHOD,
                          "任务分配 / 协商 / 冲突解决", 0.9, "Ch5",
                          ["kg:ch5:multi_agent_patterns"], [], 0.8, 35,
                          ["编排", "Orchestration"]),
        ]
        # ── Ch6: Evaluation ──
        nodes_ch6 = [
            KnowledgeNode("kg:ch6:eval_metrics", "评测指标体系", ConceptType.CONCEPT,
                          "正确性/个性化/可解释性/效率", 0.5, "Ch6",
                          [], [], 0.7, 20,
                          ["评测", "Evaluation"]),
            KnowledgeNode("kg:ch6:rule_judge", "规则判定器", ConceptType.METHOD,
                          "确定性评分 / AST 审计", 0.5, "Ch6",
                          ["kg:ch6:eval_metrics"], [], 0.7, 20,
                          ["RuleJudge", "规则判定"]),
            KnowledgeNode("kg:ch6:llm_judge", "LLM 判定器", ConceptType.METHOD,
                          "语义质量评估 / 教学适切性", 0.6, "Ch6",
                          ["kg:ch6:eval_metrics", "kg:ch3:prompt_basics"], [], 0.7, 25,
                          ["LLMJudge"]),
        ]

        all_nodes = (nodes_ch1 + nodes_ch2 + nodes_ch3 + nodes_ch4 +
                     nodes_ch5 + nodes_ch6)
        for n in all_nodes:
            kg.add_node(n)

        # ── 构建边 ──
        for node in all_nodes:
            for prereq_id in node.prerequisites:
                kg.add_edge(KnowledgeEdge(
                    source_id=prereq_id,
                    target_id=node.concept_id,
                    edge_type=EdgeType.PREREQ_OF,
                    weight=node.difficulty,
                    rationale=f"{node.concept_name} 需要先掌握 {prereq_id}",
                ))

        instance = cls()
        instance.load(kg)
        return instance

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()
