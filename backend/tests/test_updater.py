"""
Tests for knowledge/updater.py — the merge logic between ExtractionResult
and SessionState. This is the trickiest logic in the system, so we cover:
  - creating a brand new concept
  - enriching an existing concept (non-conflicting update)
  - splitting into a contradiction (conflicting update)
  - relationships creating stub nodes when needed
  - turn_count incrementing
"""

from knowledge.updater import merge_extraction
from schemas.knowledge import (
    ExtractedConcept,
    ExtractedRelationship,
    ExtractionResult,
    NodeStatus,
    RelationType,
    SessionState,
)


def make_state() -> SessionState:
    return SessionState(topic="Binary Search Trees")


def test_new_concept_creates_known_node_with_high_confidence():
    state = make_state()
    extraction = ExtractionResult(
        raw_text="A BST is a binary tree where left children are smaller.",
        concepts=[
            ExtractedConcept(
                concept="Binary Search Tree",
                description="A binary tree where left children are smaller.",
                attributes=["ordered"],
                confidence=0.9,
            )
        ],
    )

    merge_extraction(state, extraction)

    node = state.find_node_by_concept("Binary Search Tree")
    assert node is not None
    assert node.status == NodeStatus.KNOWN
    assert node.attributes == ["ordered"]
    assert state.turn_count == 1


def test_new_concept_with_low_confidence_is_partially_understood():
    state = make_state()
    extraction = ExtractionResult(
        raw_text="...",
        concepts=[
            ExtractedConcept(
                concept="Rotation",
                description="Something to do with rebalancing.",
                confidence=0.4,
            )
        ],
    )

    merge_extraction(state, extraction)

    node = state.find_node_by_concept("Rotation")
    assert node.status == NodeStatus.PARTIALLY_UNDERSTOOD


def test_concept_with_no_content_is_unknown():
    state = make_state()
    extraction = ExtractionResult(
        raw_text="...",
        concepts=[ExtractedConcept(concept="Balancing")],
    )

    merge_extraction(state, extraction)

    node = state.find_node_by_concept("Balancing")
    assert node.status == NodeStatus.UNKNOWN


def test_uncertainty_expressed_sets_uncertain_status():
    state = make_state()
    extraction = ExtractionResult(
        raw_text="...",
        concepts=[
            ExtractedConcept(
                concept="AVL Tree",
                description="I think it's a self-balancing tree.",
                uncertainty_expressed=True,
                confidence=0.9,
            )
        ],
    )

    merge_extraction(state, extraction)

    node = state.find_node_by_concept("AVL Tree")
    assert node.status == NodeStatus.UNCERTAIN


def test_enrichment_adds_new_attributes_without_losing_old_ones():
    state = make_state()
    first = ExtractionResult(
        raw_text="...",
        concepts=[
            ExtractedConcept(
                concept="Binary Search Tree",
                description="A binary tree where left children are smaller.",
                attributes=["ordered"],
                confidence=0.9,
            )
        ],
    )
    merge_extraction(state, first)

    second = ExtractionResult(
        raw_text="...",
        concepts=[
            ExtractedConcept(
                concept="Binary Search Tree",
                attributes=["allows O(log n) search"],
                examples=["used in dictionaries"],
                confidence=0.85,
            )
        ],
    )
    merge_extraction(state, second)

    node = state.find_node_by_concept("Binary Search Tree")
    assert node.attributes == ["ordered", "allows O(log n) search"]
    assert node.examples == ["used in dictionaries"]
    assert node.times_clarified == 1
    assert state.turn_count == 2
    # description preserved, not overwritten
    assert node.description == "A binary tree where left children are smaller."


def test_enrichment_does_not_duplicate_existing_attributes():
    state = make_state()
    extraction = ExtractionResult(
        raw_text="...",
        concepts=[
            ExtractedConcept(
                concept="Stack",
                description="A LIFO data structure.",
                attributes=["push", "pop"],
                confidence=0.9,
            )
        ],
    )
    merge_extraction(state, extraction)
    merge_extraction(
        state,
        ExtractionResult(
            raw_text="...",
            concepts=[
                ExtractedConcept(concept="Stack", attributes=["push", "peek"], confidence=0.9)
            ],
        ),
    )

    node = state.find_node_by_concept("Stack")
    assert node.attributes == ["push", "pop", "peek"]


def test_conflicting_description_splits_into_contradiction():
    state = make_state()
    first = ExtractionResult(
        raw_text="...",
        concepts=[
            ExtractedConcept(
                concept="Mitochondria",
                description="The powerhouse that produces energy for the cell.",
                confidence=0.9,
            )
        ],
    )
    merge_extraction(state, first)

    second = ExtractionResult(
        raw_text="...",
        concepts=[
            ExtractedConcept(
                concept="Mitochondria",
                description="A storage unit that holds waste materials only.",
                confidence=0.9,
            )
        ],
    )
    merge_extraction(state, second)

    original = state.find_node_by_concept("Mitochondria")
    revised = state.find_node_by_concept("Mitochondria (revised)")

    assert original is not None
    assert revised is not None
    assert original.status == NodeStatus.CONTRADICTORY
    assert revised.status == NodeStatus.CONTRADICTORY
    # original description preserved, not overwritten
    assert original.description == "The powerhouse that produces energy for the cell."
    assert revised.description == "A storage unit that holds waste materials only."

    assert len(state.contradictions) == 1
    contradiction = state.contradictions[0]
    assert contradiction.node_a_id == original.id
    assert contradiction.node_b_id == revised.id
    assert contradiction.resolved is False

    # a CONTRADICTS edge should link them
    contradicts_edges = [
        e for e in state.edges if e.relation_type == RelationType.CONTRADICTS
    ]
    assert len(contradicts_edges) == 1
    assert {contradicts_edges[0].source_node_id, contradicts_edges[0].target_node_id} == {
        original.id,
        revised.id,
    }


def test_similar_rephrasing_does_not_trigger_false_contradiction():
    """Two descriptions with meaningful word overlap should just enrich,
    not be treated as conflicting."""
    state = make_state()
    merge_extraction(
        state,
        ExtractionResult(
            raw_text="...",
            concepts=[
                ExtractedConcept(
                    concept="Recursion",
                    description="A function that calls itself to solve a smaller problem.",
                    confidence=0.9,
                )
            ],
        ),
    )
    merge_extraction(
        state,
        ExtractionResult(
            raw_text="...",
            concepts=[
                ExtractedConcept(
                    concept="Recursion",
                    description="A function that calls itself repeatedly to solve a problem.",
                    confidence=0.9,
                )
            ],
        ),
    )

    node = state.find_node_by_concept("Recursion")
    revised = state.find_node_by_concept("Recursion (revised)")
    assert node.status != NodeStatus.CONTRADICTORY
    assert revised is None
    assert len(state.contradictions) == 0


def test_relationship_creates_stub_nodes_for_unseen_concepts():
    state = make_state()
    extraction = ExtractionResult(
        raw_text="Light energy is converted into chemical energy.",
        relationships=[
            ExtractedRelationship(
                source_concept="Light energy",
                target_concept="Chemical energy",
                relation_type=RelationType.CAUSES,
                confidence=0.8,
            )
        ],
    )

    merge_extraction(state, extraction)

    source = state.find_node_by_concept("Light energy")
    target = state.find_node_by_concept("Chemical energy")
    assert source is not None
    assert target is not None
    assert source.status == NodeStatus.UNKNOWN  # named but not yet described
    assert len(state.edges) == 1
    assert state.edges[0].relation_type == RelationType.CAUSES


def test_relationship_reuses_existing_node_instead_of_duplicating():
    state = make_state()
    merge_extraction(
        state,
        ExtractionResult(
            raw_text="...",
            concepts=[
                ExtractedConcept(
                    concept="Photosynthesis",
                    description="Converts light into energy.",
                    confidence=0.9,
                )
            ],
        ),
    )
    merge_extraction(
        state,
        ExtractionResult(
            raw_text="...",
            relationships=[
                ExtractedRelationship(
                    source_concept="Photosynthesis",
                    target_concept="Glucose",
                    relation_type=RelationType.CAUSES,
                    confidence=0.8,
                )
            ],
        ),
    )

    # Should still be exactly one "Photosynthesis" node, not a duplicate stub
    matches = [n for n in state.nodes.values() if n.concept == "Photosynthesis"]
    assert len(matches) == 1
    assert matches[0].description == "Converts light into energy."


def test_flagged_contradiction_marks_matching_node():
    state = make_state()
    merge_extraction(
        state,
        ExtractionResult(
            raw_text="...",
            concepts=[
                ExtractedConcept(
                    concept="Force",
                    description="A push or pull on an object.",
                    confidence=0.9,
                )
            ],
        ),
    )

    merge_extraction(
        state,
        ExtractionResult(
            raw_text="...",
            contradictions_flagged=[
                "User said Force always causes motion, contradicting the earlier definition."
            ],
        ),
    )

    node = state.find_node_by_concept("Force")
    assert node.status == NodeStatus.CONTRADICTORY
    assert len(state.contradictions) == 1

def test_example_relationship_does_not_create_false_contradiction():
    state = SessionState(topic="Photosynthesis")

    first = ExtractionResult(
        raw_text="Food is something living things need.",
        concepts=[
            ExtractedConcept(
                concept="food",
                description="something living things need",
                confidence=0.95,
            )
        ],
        relationships=[],
        contradictions_flagged=[],
    )

    merge_extraction(state, first)

    second = ExtractionResult(
        raw_text="Wheat is an example of food.",
        concepts=[
            ExtractedConcept(
                concept="wheat",
                description="an example of food",
                confidence=0.95,
            )
        ],
        relationships=[
            ExtractedRelationship(
                source_concept="wheat",
                target_concept="food",
                relation_type=RelationType.EXAMPLE_OF,
                description="wheat is an example of food",
                confidence=0.95,
            )
        ],
        contradictions_flagged=[],
    )

    merge_extraction(state, second)

    assert len(state.contradictions) == 0
    assert not any(
        edge.relation_type == RelationType.CONTRADICTS
        for edge in state.edges
    )

def test_genuine_contradiction_still_creates_contradiction():
    state = SessionState(topic="Photosynthesis")

    first = ExtractionResult(
        raw_text="Plants need sunlight.",
        concepts=[
            ExtractedConcept(
                concept="plants",
                description="plants need sunlight",
                confidence=0.95,
            )
        ],
        relationships=[],
        contradictions_flagged=[],
    )

    merge_extraction(state, first)

    second = ExtractionResult(
        raw_text="Plants do not need sunlight.",
        concepts=[
            ExtractedConcept(
                concept="plants",
                description="plants do not need sunlight",
                confidence=0.95,
            )
        ],
        relationships=[],
        contradictions_flagged=[],
    )

    merge_extraction(state, second)

    assert len(state.contradictions) == 1

    assert any(
        edge.relation_type == RelationType.CONTRADICTS
        for edge in state.edges
    )