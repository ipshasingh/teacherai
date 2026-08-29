from knowledge.state import summarize
from schemas.knowledge import SessionState
from schemas.knowledge import (
    KnowledgeEdge,
    KnowledgeNode,
    NodeStatus,
    RelationType,
    SessionState,
)

def test_summary_empty_session():
    state = SessionState(topic="Photosynthesis")

    summary = summarize(state)

    assert summary.topic == "Photosynthesis"
    assert summary.known_concepts == []
    assert summary.uncertain_concepts == []
    assert summary.partially_understood_concepts == []
    assert summary.contradictory_concepts == []
    assert summary.corrected_concepts == []
    assert summary.learned_relationships == []
    assert summary.total_concepts == 0
    assert summary.total_relationships == 0
    assert summary.turn_count == 0
    assert summary.questions_asked_count == 0
    assert summary.unresolved_contradiction_count == 0
    assert summary.knowledge_leakage_events == 0

def test_summary_includes_learned_relationships():
    sunlight = KnowledgeNode(
        id="sunlight",
        concept="Sunlight",
        description="Provides energy for photosynthesis",
        status=NodeStatus.KNOWN,
    )

    photosynthesis = KnowledgeNode(
        id="photosynthesis",
        concept="Photosynthesis",
        description="A process used by plants",
        status=NodeStatus.KNOWN,
    )

    edge = KnowledgeEdge(
        source_node_id="sunlight",
        target_node_id="photosynthesis",
        relation_type=RelationType.CAUSES,
        description="Sunlight provides energy needed for photosynthesis",
    )

    state = SessionState(
        topic="Photosynthesis",
        nodes={
            sunlight.id: sunlight,
            photosynthesis.id: photosynthesis,
        },
        edges=[edge],
    )

    summary = summarize(state)

    assert summary.total_relationships == 1
    assert len(summary.learned_relationships) == 1

    relationship = summary.learned_relationships[0]

    assert relationship.source_concept == "Sunlight"
    assert relationship.target_concept == "Photosynthesis"
    assert relationship.relation_type == "causes"
    assert relationship.description == (
        "Sunlight provides energy needed for photosynthesis"
    )

def test_summary_includes_corrected_concepts():
    state = SessionState(
        topic="Photosynthesis",
        nodes={
            "1": KnowledgeNode(
                id="1",
                concept="Chlorophyll",
                description="A corrected explanation",
                status=NodeStatus.CORRECTED,
            )
        },
    )

    summary = summarize(state)

    assert summary.corrected_concepts == ["Chlorophyll"]

def test_summary_ignores_orphaned_relationship():
    state = SessionState(
        topic="Photosynthesis",
        nodes={
            "1": KnowledgeNode(
                id="1",
                concept="Sunlight",
                status=NodeStatus.KNOWN,
            )
        },
        edges=[
            KnowledgeEdge(
                source_node_id="1",
                target_node_id="does-not-exist",
                relation_type=RelationType.CAUSES,
            )
        ],
    )

    summary = summarize(state)

    assert summary.learned_relationships == []
    assert summary.total_relationships == 0