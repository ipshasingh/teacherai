"""
Tests for knowledge/gaps.py. Fully deterministic — no LLM.
"""

from knowledge.gaps import detect_gaps
from schemas.knowledge import (
    Contradiction,
    KnowledgeEdge,
    KnowledgeNode,
    NodeStatus,
    QuestionCategory,
    RelationType,
    SessionState,
)


def test_no_gaps_on_empty_session():
    state = SessionState(topic="Topic")
    assert detect_gaps(state) == []


def test_unresolved_contradiction_produces_gap():
    state = SessionState(topic="Topic")
    a = KnowledgeNode(concept="A", status=NodeStatus.CONTRADICTORY)
    b = KnowledgeNode(concept="A (revised)", status=NodeStatus.CONTRADICTORY)
    state.nodes[a.id] = a
    state.nodes[b.id] = b
    state.contradictions.append(
        Contradiction(node_a_id=a.id, node_b_id=b.id, description="conflict")
    )

    gaps = detect_gaps(state)
    contradiction_gaps = [g for g in gaps if g.category == QuestionCategory.CONTRADICTION_RESOLUTION]
    assert len(contradiction_gaps) == 1
    assert set(contradiction_gaps[0].node_ids) == {a.id, b.id}


def test_resolved_contradiction_produces_no_gap():
    state = SessionState(topic="Topic")
    a = KnowledgeNode(concept="A", status=NodeStatus.CORRECTED)
    b = KnowledgeNode(concept="A (revised)", status=NodeStatus.CORRECTED)
    state.nodes[a.id] = a
    state.nodes[b.id] = b
    state.contradictions.append(
        Contradiction(node_a_id=a.id, node_b_id=b.id, description="conflict", resolved=True)
    )

    gaps = detect_gaps(state)
    assert not any(g.category == QuestionCategory.CONTRADICTION_RESOLUTION for g in gaps)


def test_unknown_node_with_edge_produces_prerequisite_gap():
    state = SessionState(topic="Topic")
    known = KnowledgeNode(concept="Photosynthesis", status=NodeStatus.KNOWN, description="x")
    stub = KnowledgeNode(concept="Chlorophyll", status=NodeStatus.UNKNOWN)
    state.nodes[known.id] = known
    state.nodes[stub.id] = stub
    state.edges.append(
        KnowledgeEdge(
            source_node_id=known.id, target_node_id=stub.id, relation_type=RelationType.RELATES_TO
        )
    )

    gaps = detect_gaps(state)
    prereq_gaps = [g for g in gaps if g.category == QuestionCategory.PREREQUISITE]
    assert len(prereq_gaps) == 1
    assert prereq_gaps[0].node_ids == [stub.id]


def test_unknown_node_without_edge_produces_no_prerequisite_gap():
    state = SessionState(topic="Topic")
    stub = KnowledgeNode(concept="Isolated", status=NodeStatus.UNKNOWN)
    state.nodes[stub.id] = stub

    gaps = detect_gaps(state)
    assert not any(g.category == QuestionCategory.PREREQUISITE for g in gaps)


def test_uncertain_node_produces_clarification_gap():
    state = SessionState(topic="Topic")
    node = KnowledgeNode(concept="AVL Tree", status=NodeStatus.UNCERTAIN, description="maybe balanced")
    state.nodes[node.id] = node

    gaps = detect_gaps(state)
    clarif = [g for g in gaps if g.category == QuestionCategory.CLARIFICATION]
    assert len(clarif) == 1
    assert clarif[0].node_ids == [node.id]


def test_thin_description_produces_definition_gap():
    state = SessionState(topic="Topic")
    node = KnowledgeNode(concept="Recursion", status=NodeStatus.KNOWN, description="calls itself")
    state.nodes[node.id] = node

    gaps = detect_gaps(state)
    defn = [g for g in gaps if g.category == QuestionCategory.DEFINITION]
    assert len(defn) == 1


def test_full_description_produces_no_definition_gap():
    state = SessionState(topic="Topic")
    node = KnowledgeNode(
        concept="Recursion",
        status=NodeStatus.KNOWN,
        description="A function that calls itself to solve smaller instances of the same problem.",
    )
    state.nodes[node.id] = node

    gaps = detect_gaps(state)
    assert not any(g.category == QuestionCategory.DEFINITION for g in gaps)


def test_description_without_examples_produces_example_gap():
    state = SessionState(topic="Topic")
    node = KnowledgeNode(
        concept="Stack", status=NodeStatus.KNOWN, description="A LIFO data structure used everywhere."
    )
    state.nodes[node.id] = node

    gaps = detect_gaps(state)
    ex = [g for g in gaps if g.category == QuestionCategory.EXAMPLE]
    assert len(ex) == 1


def test_isolated_node_produces_relationship_gap_when_multiple_nodes_exist():
    state = SessionState(topic="Topic")
    a = KnowledgeNode(concept="A", status=NodeStatus.KNOWN, description="something about a thing")
    b = KnowledgeNode(concept="B", status=NodeStatus.KNOWN, description="something about b thing")
    state.nodes[a.id] = a
    state.nodes[b.id] = b
    # no edges between them

    gaps = detect_gaps(state)
    rel_gaps = [g for g in gaps if g.category == QuestionCategory.RELATIONSHIP]
    assert len(rel_gaps) == 2  # both isolated


def test_single_node_produces_no_relationship_gap():
    state = SessionState(topic="Topic")
    node = KnowledgeNode(concept="A", status=NodeStatus.KNOWN, description="something about a thing")
    state.nodes[node.id] = node

    gaps = detect_gaps(state)
    assert not any(g.category == QuestionCategory.RELATIONSHIP for g in gaps)


def test_thin_causal_edge_produces_mechanism_gap():
    state = SessionState(topic="Topic")
    a = KnowledgeNode(concept="Light energy", status=NodeStatus.KNOWN, description="energy from light source")
    b = KnowledgeNode(concept="Chemical energy", status=NodeStatus.KNOWN, description="energy in chemical bonds")
    state.nodes[a.id] = a
    state.nodes[b.id] = b
    state.edges.append(
        KnowledgeEdge(
            source_node_id=a.id,
            target_node_id=b.id,
            relation_type=RelationType.CAUSES,
            description="converted",  # thin, < 6 words
        )
    )

    gaps = detect_gaps(state)
    mech = [g for g in gaps if g.category == QuestionCategory.MECHANISM]
    assert len(mech) == 1
    assert set(mech[0].node_ids) == {a.id, b.id}


def test_detailed_causal_edge_produces_no_mechanism_gap():
    state = SessionState(topic="Topic")
    a = KnowledgeNode(concept="Light energy", status=NodeStatus.KNOWN, description="x")
    b = KnowledgeNode(concept="Chemical energy", status=NodeStatus.KNOWN, description="x")
    state.nodes[a.id] = a
    state.nodes[b.id] = b
    state.edges.append(
        KnowledgeEdge(
            source_node_id=a.id,
            target_node_id=b.id,
            relation_type=RelationType.CAUSES,
            description="light energy is absorbed by chlorophyll and converted through a chain of reactions",
        )
    )

    gaps = detect_gaps(state)
    assert not any(g.category == QuestionCategory.MECHANISM for g in gaps)