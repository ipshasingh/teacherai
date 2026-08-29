"""
Deterministic gap detector.

Scans SessionState and produces GapSignal objects describing concrete,
inspectable gaps in the knowledge graph. No LLM here — this keeps "what
needs to be asked about, and why" fully deterministic and reproducible.
The LLM's only job (agents/question_generator.py) is turning a GapSignal
into natural question phrasing.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from knowledge.graph import get_edges_for_node, nodes_by_status
from schemas.knowledge import NodeStatus, QuestionCategory, RelationType, SessionState

_THIN_DESCRIPTION_WORD_COUNT = 6


class GapSignal(BaseModel):
    category: QuestionCategory
    node_ids: list[str]
    importance_score: float = Field(ge=0.0, le=1.0)
    gap_score: float = Field(ge=0.0, le=1.0)
    context: str  # deterministic description handed to the LLM for phrasing


def detect_gaps(state: SessionState) -> list[GapSignal]:
    gaps: list[GapSignal] = []
    gaps.extend(_contradiction_gaps(state))
    gaps.extend(_prerequisite_gaps(state))
    gaps.extend(_clarification_gaps(state))
    gaps.extend(_definition_gaps(state))
    gaps.extend(_example_gaps(state))
    gaps.extend(_relationship_gaps(state))
    gaps.extend(_mechanism_gaps(state))
    return gaps


def _contradiction_gaps(state: SessionState) -> list[GapSignal]:
    gaps = []
    for c in state.contradictions:
        if c.resolved:
            continue
        gaps.append(
            GapSignal(
                category=QuestionCategory.CONTRADICTION_RESOLUTION,
                node_ids=[c.node_a_id, c.node_b_id],
                importance_score=1.0,
                gap_score=1.0,
                context=c.description,
            )
        )
    return gaps


def _prerequisite_gaps(state: SessionState) -> list[GapSignal]:
    gaps = []
    for node in nodes_by_status(state, NodeStatus.UNKNOWN):
        edges = get_edges_for_node(state, node.id)
        if not edges:
            continue  # not referenced by anything yet, nothing to ask about
        importance = min(1.0, 0.5 + 0.1 * len(edges))
        gaps.append(
            GapSignal(
                category=QuestionCategory.PREREQUISITE,
                node_ids=[node.id],
                importance_score=importance,
                gap_score=0.8,
                context=(
                    f"The user mentioned '{node.concept}' while explaining something else, "
                    f"but hasn't described what it actually is."
                ),
            )
        )
    return gaps


def _clarification_gaps(state: SessionState) -> list[GapSignal]:
    gaps = []
    for node in nodes_by_status(state, NodeStatus.UNCERTAIN):
        gaps.append(
            GapSignal(
                category=QuestionCategory.CLARIFICATION,
                node_ids=[node.id],
                importance_score=0.6,
                gap_score=0.7,
                context=(
                    f"The user expressed uncertainty about '{node.concept}' "
                    f"(their description: \"{node.description or 'none given'}\")."
                ),
            )
        )
    return gaps


def _definition_gaps(state: SessionState) -> list[GapSignal]:
    gaps = []
    for node in state.nodes.values():
        if node.status not in (NodeStatus.PARTIALLY_UNDERSTOOD, NodeStatus.KNOWN):
            continue
        word_count = len((node.description or "").split())
        if word_count < _THIN_DESCRIPTION_WORD_COUNT:
            gaps.append(
                GapSignal(
                    category=QuestionCategory.DEFINITION,
                    node_ids=[node.id],
                    importance_score=0.5,
                    gap_score=0.6,
                    context=(
                        f"'{node.concept}' was only briefly described as "
                        f"\"{node.description or '(no description)'}\" — the definition is thin."
                    ),
                )
            )
    return gaps


def _example_gaps(state: SessionState) -> list[GapSignal]:
    gaps = []
    for node in state.nodes.values():
        if node.status not in (NodeStatus.KNOWN, NodeStatus.PARTIALLY_UNDERSTOOD):
            continue
        if node.description and not node.examples:
            gaps.append(
                GapSignal(
                    category=QuestionCategory.EXAMPLE,
                    node_ids=[node.id],
                    importance_score=0.4,
                    gap_score=0.5,
                    context=f"'{node.concept}' has a description but no concrete example yet.",
                )
            )
    return gaps


def _relationship_gaps(state: SessionState) -> list[GapSignal]:
    gaps = []
    if len(state.nodes) < 2:
        return gaps
    for node in state.nodes.values():
        if node.status not in (NodeStatus.KNOWN, NodeStatus.PARTIALLY_UNDERSTOOD):
            continue
        if not get_edges_for_node(state, node.id):
            gaps.append(
                GapSignal(
                    category=QuestionCategory.RELATIONSHIP,
                    node_ids=[node.id],
                    importance_score=0.5,
                    gap_score=0.6,
                    context=(
                        f"'{node.concept}' hasn't been connected to any other "
                        f"concept taught so far."
                    ),
                )
            )
    return gaps


def _mechanism_gaps(state: SessionState) -> list[GapSignal]:
    gaps = []
    for edge in state.edges:
        if edge.relation_type != RelationType.CAUSES:
            continue
        source = state.nodes.get(edge.source_node_id)
        target = state.nodes.get(edge.target_node_id)
        if source is None or target is None:
            continue
        edge_word_count = len((edge.description or "").split())
        if edge_word_count < _THIN_DESCRIPTION_WORD_COUNT:
            gaps.append(
                GapSignal(
                    category=QuestionCategory.MECHANISM,
                    node_ids=[source.id, target.id],
                    importance_score=0.6,
                    gap_score=0.7,
                    context=(
                        f"The user said '{source.concept}' causes '{target.concept}' "
                        f"but didn't explain how or why that happens."
                    ),
                )
            )
    return gaps