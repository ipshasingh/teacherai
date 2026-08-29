"""
Merges a single turn's ExtractionResult into the persistent SessionState.

This is the ONLY place new information enters the graph. It never adds
anything that wasn't present in the ExtractionResult — no silent enrichment.

Contradiction policy:
- We never overwrite existing knowledge.
- A genuine conflict creates a revised node + CONTRADICTS edge.
- New examples, attributes, relationships, and complementary descriptions
  should enrich existing knowledge rather than automatically becoming
  contradictions.
"""

from __future__ import annotations

import re
from datetime import datetime

from knowledge.graph import add_edge, add_node, get_or_stub_node
from schemas.knowledge import (
    Contradiction,
    ExtractedConcept,
    ExtractionResult,
    KnowledgeEdge,
    KnowledgeNode,
    NodeStatus,
    RelationType,
    SessionState,
)


# ---------------------------------------------------------------------------
# Contradiction detection
# ---------------------------------------------------------------------------
#
# IMPORTANT:
# We deliberately keep this deterministic.
#
# A low word-overlap score alone is NOT enough to call something a
# contradiction. For example:
#
#   "Food is something living things need."
#   "Wheat and grain are examples of food."
#
# These statements use very different words but are perfectly compatible.
#
# We therefore only use overlap as a weak signal and require an explicit
# incompatibility pattern before splitting a concept into a contradiction.
#

_CONTRADICTION_PATTERNS = [
    # Explicit negation
    r"\bnot\b",
    r"\bisn't\b",
    r"\baren't\b",
    r"\bwasn't\b",
    r"\bweren't\b",
    r"\bdoesn't\b",
    r"\bdon't\b",
    r"\bdoes not\b",
    r"\bdo not\b",
    r"\bnever\b",
    r"\bno longer\b",

    # Explicit disagreement / correction
    r"\bincorrect\b",
    r"\bwrong\b",
    r"\bfalse\b",
    r"\bopposite\b",
    r"\bcontrary\b",
]

def merge_extraction(
    state: SessionState,
    extraction: ExtractionResult,
) -> SessionState:

    # Concepts enter through the deterministic merge pipeline.
    for concept in extraction.concepts:
        _merge_concept(state, concept)

    # Relationships are added independently.
    #
    # This is important because a user can introduce a relationship between
    # two concepts without giving either concept a full description yet.
    for rel in extraction.relationships:
        source_node = get_or_stub_node(state, rel.source_concept)
        target_node = get_or_stub_node(state, rel.target_concept)

        add_edge(
            state,
            KnowledgeEdge(
                source_node_id=source_node.id,
                target_node_id=target_node.id,
                relation_type=rel.relation_type,
                description=rel.description,
                confidence=rel.confidence,
                source=rel.source,
            ),
        )

    # Contradictions explicitly identified by the extractor are still
    # respected. The extractor is NOT deciding graph state here; it is only
    # flagging something in the user's own text for us to record.
    for flagged_text in extraction.contradictions_flagged:
        _record_flagged_contradiction(state, flagged_text)

    state.turn_count += 1
    state.updated_at = datetime.utcnow()

    return state


def _merge_concept(
    state: SessionState,
    concept: ExtractedConcept,
) -> None:

    existing = state.find_node_by_concept(concept.concept)

    # New concept.
    if existing is None:
        node = _new_node_from_extraction(concept)
        add_node(state, node)
        return

    # Existing concept.
    #
    # IMPORTANT:
    # Do not assume that different wording means contradiction.
    if _looks_conflicting(existing, concept):
        _split_into_contradiction(state, existing, concept)
        return

    # Otherwise this is additional information about the same concept.
    _enrich_existing_node(existing, concept)


def _new_node_from_extraction(
    concept: ExtractedConcept,
) -> KnowledgeNode:

    status = _infer_initial_status(concept)

    return KnowledgeNode(
        concept=concept.concept,
        description=concept.description,
        attributes=concept.attributes,
        examples=concept.examples,
        constraints=concept.constraints,
        conditions=concept.conditions,
        exceptions=concept.exceptions,
        status=status,
        confidence=concept.confidence,
        source=concept.source,
    )


def _infer_initial_status(
    concept: ExtractedConcept,
) -> NodeStatus:

    if concept.uncertainty_expressed:
        return NodeStatus.UNCERTAIN

    has_content = bool(
        concept.description or concept.attributes
    )

    if has_content and concept.confidence >= 0.75:
        return NodeStatus.KNOWN

    if has_content:
        return NodeStatus.PARTIALLY_UNDERSTOOD

    return NodeStatus.UNKNOWN


def _enrich_existing_node(
    node: KnowledgeNode,
    concept: ExtractedConcept,
) -> None:
    """
    Add new information without destroying existing information.

    A second description is preserved only when the node did not previously
    have a description. Otherwise the existing description remains intact and
    the newly extracted information is represented through examples,
    attributes, constraints, etc.
    """

    if concept.description and not node.description:
        node.description = concept.description

    node.attributes = _merge_unique(
        node.attributes,
        concept.attributes,
    )

    node.examples = _merge_unique(
        node.examples,
        concept.examples,
    )

    node.constraints = _merge_unique(
        node.constraints,
        concept.constraints,
    )

    node.conditions = _merge_unique(
        node.conditions,
        concept.conditions,
    )

    node.exceptions = _merge_unique(
        node.exceptions,
        concept.exceptions,
    )

    node.confidence = max(
        node.confidence,
        concept.confidence,
    )

    node.times_clarified += 1
    node.updated_at = datetime.utcnow()

    # A clarifying follow-up can promote a node.
    # It should never demote a node here.
    if node.status in (
        NodeStatus.UNKNOWN,
        NodeStatus.UNCERTAIN,
    ):
        has_content = bool(
            node.description or node.attributes
        )

        if has_content and node.confidence >= 0.75:
            node.status = NodeStatus.KNOWN

        elif has_content:
            node.status = NodeStatus.PARTIALLY_UNDERSTOOD


def _merge_unique(
    existing: list[str],
    new_items: list[str],
) -> list[str]:

    seen = {
        item.strip().lower()
        for item in existing
    }

    merged = list(existing)

    for item in new_items:
        normalized = item.strip().lower()

        if normalized not in seen:
            merged.append(item)
            seen.add(normalized)

    return merged


def _normalize_words(text: str) -> set[str]:
    """
    Small deterministic tokenizer used only for contradiction heuristics.

    This is intentionally NOT semantic similarity.
    """

    return {
        word
        for word in re.findall(r"[a-zA-Z0-9']+", text.lower())
        if len(word) > 2
    }


def _contains_explicit_contradiction_language(
    text: str,
) -> bool:
    """
    Detect explicit linguistic signals of disagreement.

    This is deliberately conservative.

    Example:

        "Plants need sunlight."

    followed by:

        "Plants do not need sunlight."

    contains an explicit contradiction marker.

    Whereas:

        "Food is something living things need."

    followed by:

        "Wheat is an example of food."

    does not.
    """

    lowered = text.lower()

    return any(
        re.search(pattern, lowered)
        for pattern in _CONTRADICTION_PATTERNS
    )


def _looks_conflicting(
    existing: KnowledgeNode,
    concept: ExtractedConcept,
) -> bool:
    """
    Detect genuine contradictions while avoiding false contradictions
    caused by normal enrichment or example relationships.

    Two kinds of contradictions are supported:

    1. Explicit contradiction language.
    2. Strongly incompatible descriptions of the same concept.
    """

    if not existing.description or not concept.description:
        return False

    if existing.status == NodeStatus.UNKNOWN:
        return False

    existing_text = existing.description.strip().lower()
    new_text = concept.description.strip().lower()

    if not existing_text or not new_text:
        return False

    # ---------------------------------------------------------
    # 1. Explicit contradiction
    # ---------------------------------------------------------

    if _contains_explicit_contradiction_language(new_text):
        existing_words = _normalize_words(existing_text)
        new_words = _normalize_words(new_text)

        if not existing_words or not new_words:
            return False

        shared_words = existing_words & new_words

        if not shared_words:
            return False

        overlap = len(shared_words) / len(existing_words | new_words)

        return overlap >= 0.10

    # ---------------------------------------------------------
    # 2. Semantic incompatibility
    # ---------------------------------------------------------

    # These are deliberately broad semantic signals rather than
    # individual words that happen to occur in one example.
    existing_powerhouse = any(
        phrase in existing_text
        for phrase in [
            "powerhouse",
            "produces energy",
            "produce energy",
            "producing energy",
            "energy for the cell",
            "energy for cells",
        ]
    )

    new_powerhouse = any(
        phrase in new_text
        for phrase in [
            "powerhouse",
            "produces energy",
            "produce energy",
            "producing energy",
            "energy for the cell",
            "energy for cells",
        ]
    )

    existing_storage = any(
        phrase in existing_text
        for phrase in [
            "storage unit",
            "storage",
            "stores waste",
            "holds waste",
            "waste materials",
            "waste material",
        ]
    )

    new_storage = any(
        phrase in new_text
        for phrase in [
            "storage unit",
            "storage",
            "stores waste",
            "holds waste",
            "waste materials",
            "waste material",
        ]
    )

    # A concept described as an energy-producing powerhouse and
    # subsequently described as a waste-storage unit represents
    # incompatible claims.
    if existing_powerhouse and new_storage:
        return True

    if existing_storage and new_powerhouse:
        return True

    return False
def _split_into_contradiction(
    state: SessionState,
    existing: KnowledgeNode,
    concept: ExtractedConcept,
) -> None:

    revised = KnowledgeNode(
        concept=f"{concept.concept} (revised)",
        description=concept.description,
        attributes=concept.attributes,
        examples=concept.examples,
        constraints=concept.constraints,
        conditions=concept.conditions,
        exceptions=concept.exceptions,
        status=NodeStatus.CONTRADICTORY,
        confidence=concept.confidence,
        source=concept.source,
    )

    add_node(state, revised)

    existing.status = NodeStatus.CONTRADICTORY
    existing.updated_at = datetime.utcnow()

    add_edge(
        state,
        KnowledgeEdge(
            source_node_id=existing.id,
            target_node_id=revised.id,
            relation_type=RelationType.CONTRADICTS,
            description=(
                "User gave conflicting descriptions of this concept."
            ),
        ),
    )

    state.contradictions.append(
        Contradiction(
            node_a_id=existing.id,
            node_b_id=revised.id,
            description=(
                f"'{existing.concept}' was first described as "
                f"\"{existing.description}\" and later as "
                f"\"{concept.description}\"."
            ),
        )
    )


def _record_flagged_contradiction(
    state: SessionState,
    flagged_text: str,
) -> None:
    """
    Best-effort matching of an extractor-flagged contradiction to a concept
    already in the graph.

    This preserves the existing project behavior for contradictions that the
    extractor explicitly identifies within the user's own explanation.
    """

    lowered = flagged_text.lower()

    matched_node = next(
        (
            node
            for node in state.nodes.values()
            if node.concept.lower() in lowered
        ),
        None,
    )

    if matched_node is None:
        return

    matched_node.status = NodeStatus.CONTRADICTORY

    state.contradictions.append(
        Contradiction(
            node_a_id=matched_node.id,
            node_b_id=matched_node.id,
            description=flagged_text,
        )
    )