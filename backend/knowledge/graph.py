"""
Low-level, pure operations on the knowledge graph held inside a SessionState.

No LLM calls here. No merge/contradiction logic here (see updater.py).
This file only knows how to read/write nodes and edges.
"""

from __future__ import annotations

from schemas.knowledge import (
    KnowledgeEdge,
    KnowledgeNode,
    NodeStatus,
    RelationType,
    SessionState,
)


def add_node(state: SessionState, node: KnowledgeNode) -> None:
    state.nodes[node.id] = node


def get_node(state: SessionState, node_id: str) -> KnowledgeNode | None:
    return state.nodes.get(node_id)


def get_or_stub_node(state: SessionState, concept: str) -> KnowledgeNode:
    """
    Find a node by concept name, or create a bare UNKNOWN stub if it doesn't
    exist yet. Used when a relationship references a concept the user has
    named but not yet described — the name itself is user-sourced, so
    creating a placeholder node is not "leakage," it just has no content yet.
    """
    existing = state.find_node_by_concept(concept)
    if existing:
        return existing
    node = KnowledgeNode(concept=concept, status=NodeStatus.UNKNOWN, confidence=0.2)
    add_node(state, node)
    return node


def add_edge(state: SessionState, edge: KnowledgeEdge) -> None:
    state.edges.append(edge)


def get_edges_for_node(state: SessionState, node_id: str) -> list[KnowledgeEdge]:
    return [
        e for e in state.edges if e.source_node_id == node_id or e.target_node_id == node_id
    ]


def get_neighbors(state: SessionState, node_id: str) -> list[KnowledgeNode]:
    neighbor_ids: set[str] = set()
    for e in state.edges:
        if e.source_node_id == node_id:
            neighbor_ids.add(e.target_node_id)
        elif e.target_node_id == node_id:
            neighbor_ids.add(e.source_node_id)
    return [state.nodes[nid] for nid in neighbor_ids if nid in state.nodes]


def nodes_by_status(state: SessionState, status: NodeStatus) -> list[KnowledgeNode]:
    return [n for n in state.nodes.values() if n.status == status]


def edges_by_relation(state: SessionState, relation: RelationType) -> list[KnowledgeEdge]:
    return [e for e in state.edges if e.relation_type == relation]


def has_edge(
    state: SessionState, source_id: str, target_id: str, relation: RelationType
) -> bool:
    return any(
        e.source_node_id == source_id
        and e.target_node_id == target_id
        and e.relation_type == relation
        for e in state.edges
    )