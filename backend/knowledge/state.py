"""
Read-only views over SessionState: the summaries the UI's "current knowledge"
panel and the evaluation layer need. No mutation happens here.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel
from knowledge.graph import nodes_by_status
from schemas.knowledge import NodeStatus, SessionState


# class SessionSummary(BaseModel):
#     session_id: str
#     topic: str
#     turn_count: int
#     known_concepts: list[str]
#     uncertain_concepts: list[str]
#     partially_understood_concepts: list[str]
#     contradictory_concepts: list[str]
#     unresolved_contradiction_count: int
#     questions_asked_count: int
#     total_concepts: int
#     knowledge_leakage_events: int

class LearnedRelationship(BaseModel):
    source_concept: str
    target_concept: str
    relation_type: str
    description: Optional[str] = None


class SessionSummary(BaseModel):
    session_id: str
    topic: str

    # Learner state
    known_concepts: list[str]
    uncertain_concepts: list[str]
    partially_understood_concepts: list[str]
    contradictory_concepts: list[str]
    corrected_concepts: list[str]

    # Knowledge graph
    learned_relationships: list[LearnedRelationship]

    # Session stats
    turn_count: int
    questions_asked_count: int
    total_concepts: int
    total_relationships: int
    unresolved_contradiction_count: int

    # Safety
     # Safety
    knowledge_leakage_events: int
    
def summarize(state: SessionState) -> SessionSummary:
    node_lookup = state.nodes

    learned_relationships = []

    for edge in state.edges:
        source_node = node_lookup.get(edge.source_node_id)
        target_node = node_lookup.get(edge.target_node_id)

        # Ignore malformed/orphaned edges rather than crashing the UI.
        if source_node is None or target_node is None:
            continue

        learned_relationships.append(
            LearnedRelationship(
                source_concept=source_node.concept,
                target_concept=target_node.concept,
                relation_type=edge.relation_type.value,
                description=edge.description,
            )
        )

    return SessionSummary(
        session_id=state.session_id,
        topic=state.topic,

        known_concepts=[
            n.concept
            for n in nodes_by_status(state, NodeStatus.KNOWN)
        ],

        uncertain_concepts=[
            n.concept
            for n in nodes_by_status(state, NodeStatus.UNCERTAIN)
        ],

        partially_understood_concepts=[
            n.concept
            for n in nodes_by_status(
                state,
                NodeStatus.PARTIALLY_UNDERSTOOD,
            )
        ],

        contradictory_concepts=[
            n.concept
            for n in nodes_by_status(
                state,
                NodeStatus.CONTRADICTORY,
            )
        ],

        corrected_concepts=[
            n.concept
            for n in nodes_by_status(
                state,
                NodeStatus.CORRECTED,
            )
        ],

        learned_relationships=learned_relationships,

        turn_count=state.turn_count,
        questions_asked_count=len(state.questions_asked),
        total_concepts=len(state.nodes),
        total_relationships=len(learned_relationships),

        unresolved_contradiction_count=sum(
            1
            for contradiction in state.contradictions
            if not contradiction.resolved
        ),

        knowledge_leakage_events=state.knowledge_leakage_events,
    )

def is_empty(state: SessionState) -> bool:
    """True at the very start of a session — used by the demo to show the
    empty-knowledge-state moment (section 18, step 2)."""
    return len(state.nodes) == 0 and len(state.edges) == 0

    knowledge_leakage_events: int