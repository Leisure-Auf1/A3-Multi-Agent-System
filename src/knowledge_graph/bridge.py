"""
Phase 8.3-D1 — Knowledge Graph Bridge

Connects existing InMemoryKnowledgeGraph to PlannerAgent / ContentGeneratorAgent / ErrorAnalysis.

Bridge functions:
  - Convert PlannerAgent dict format → KnowledgeGraph format
  - Wrap compute_optimal_path / compute_knowledge_gap with mastery_map
  - Build default KG for Multi-Agent AI course
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any

from . import (
    KnowledgeNode, KnowledgeEdge, KnowledgeGraph,
    KnowledgeGap, PathResult, EdgeType, ConceptType,
)
from .graph_store import InMemoryKnowledgeGraph


# --- Default Knowledge Graph (Multi-Agent AI course) ---

_DEFAULT_KG: Optional[InMemoryKnowledgeGraph] = None


def get_default_kg() -> InMemoryKnowledgeGraph:
    """Get or build the default Multi-Agent AI course knowledge graph."""
    global _DEFAULT_KG
    if _DEFAULT_KG is None:
        _DEFAULT_KG = InMemoryKnowledgeGraph.build_default_multimodal_ai_graph()
    return _DEFAULT_KG


# --- Bridge: PlannerAgent dict → KG ---

def build_kg_from_planner_graph(
    planner_graph: Dict[str, Dict[str, Any]],
    course_name: str = "Default Course",
) -> InMemoryKnowledgeGraph:
    """
    Convert PlannerAgent's DEFAULT_KNOWLEDGE_GRAPH dict to InMemoryKnowledgeGraph.

    PlannerAgent format:
      {course_id: {title: str, topics: [{id, title, concept, required, base_depth, base_minutes}]}}

    Result: InMemoryKnowledgeGraph with nodes for each topic + PREREQ_OF edges.
    """
    kg = KnowledgeGraph(course_name=course_name)
    all_nodes: List[KnowledgeNode] = []

    for course_id, course_data in planner_graph.items():
        topics = course_data.get("topics", [])
        for topic in topics:
            tid = topic.get("id", "")
            node = KnowledgeNode(
                concept_id=tid,
                concept_name=topic.get("title", tid),
                concept_type=ConceptType.CONCEPT,
                description=topic.get("concept", ""),
                difficulty=topic.get("base_depth", 2) / 3.0,
                chapter=course_id,
                prerequisites=topic.get("required", []),
                estimated_minutes=topic.get("base_minutes", 15),
                keywords=[tid, topic.get("title", "")],
            )
            all_nodes.append(node)
            kg.add_node(node)

    # Build edges from prerequisites
    for node in all_nodes:
        for prereq_id in node.prerequisites:
            kg.add_edge(KnowledgeEdge(
                source_id=prereq_id,
                target_id=node.concept_id,
                edge_type=EdgeType.PREREQ_OF,
                weight=node.difficulty,
                rationale=f"{node.concept_name} requires {prereq_id}",
            ))

    instance = InMemoryKnowledgeGraph()
    instance.load(kg)
    return instance


# --- Plan ordering via KG ---

def compute_plan_order(
    kg: InMemoryKnowledgeGraph,
    concept_ids: List[str],
    mastery_map: Dict[str, float],
    target: Optional[str] = None,
) -> PathResult:
    """
    Compute optimal learning order using the knowledge graph.

    Args:
        kg: The knowledge graph instance
        concept_ids: List of concept IDs to learn
        mastery_map: concept_id → mastery score (0.0-1.0)
        target: Optional target concept (if None, uses last concept_id)

    Returns:
        PathResult with ordered_nodes, skipped_nodes, boosted_nodes
    """
    if not target and concept_ids:
        target = concept_ids[-1]

    if not target or target not in kg._graph:
        # Fallback: just return original order
        return PathResult(
            ordered_nodes=concept_ids,
            total_minutes=0,
            skipped_nodes=[],
            boosted_nodes=[],
        )

    return kg.compute_optimal_path(mastery_map, target)


# --- Gap analysis for ErrorAnalysis ---

def compute_missing_prerequisites(
    kg: InMemoryKnowledgeGraph,
    concept_id: str,
    mastery_map: Dict[str, float],
) -> List[str]:
    """
    Find missing prerequisites for a concept.

    Args:
        kg: Knowledge graph
        concept_id: The concept the student got wrong
        mastery_map: concept_id → mastery score

    Returns:
        List of missing prerequisite concept_ids
    """
    gap = kg.compute_knowledge_gap(concept_id, mastery_map)
    return gap.missing_prerequisites


def compute_gap_for_concept(
    kg: InMemoryKnowledgeGraph,
    concept_id: str,
    mastery_map: Dict[str, float],
) -> KnowledgeGap:
    """Full gap analysis for a concept."""
    return kg.compute_knowledge_gap(concept_id, mastery_map)


# --- Concept mapping for ErrorAnalysis ---

def map_error_to_prerequisites(
    kg: InMemoryKnowledgeGraph,
    wrong_concept: str,
    mastery_map: Dict[str, float],
) -> Dict[str, Any]:
    """
    Given a wrong answer concept, find upstream prerequisites that might be the root cause.

    Returns dict with:
      - missing_prerequisites: [concept_ids that need to be learned first]
      - weak_concepts: [concept_ids that need review]
      - recommended_sequence: [ordered list of concepts to study]
    """
    gap = kg.compute_knowledge_gap(wrong_concept, mastery_map)
    return {
        "missing_prerequisites": gap.missing_prerequisites,
        "weak_concepts": gap.weak_concepts,
        "recommended_sequence": gap.recommended_sequence,
    }
