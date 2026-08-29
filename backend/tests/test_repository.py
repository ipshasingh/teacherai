"""
Tests for database/repository.py.

Uses an isolated in-memory SQLite DB per test (not the real feynman.db),
so this is safe to run repeatedly and never touches real session data.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base
from database.repository import SessionRepository
from schemas.knowledge import (
    KnowledgeEdge,
    KnowledgeNode,
    NodeStatus,
    ProvenanceSource,
    RelationType,
    CandidateQuestion,
    QuestionCategory,
    Contradiction,
)


@pytest.fixture()
def db_session():
    """Fresh in-memory SQLite DB, one per test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_create_and_load_empty_session(db_session):
    repo = SessionRepository(db_session)
    state = repo.create_session(topic="Binary Search Trees")

    assert state.topic == "Binary Search Trees"
    assert state.nodes == {}
    assert state.turn_count == 0

    loaded = repo.load_session(state.session_id)
    assert loaded is not None
    assert loaded.session_id == state.session_id
    assert loaded.topic == "Binary Search Trees"
    assert loaded.nodes == {}


def test_load_nonexistent_session_returns_none(db_session):
    repo = SessionRepository(db_session)
    assert repo.load_session("does-not-exist") is None


def test_add_node_save_and_reload(db_session):
    repo = SessionRepository(db_session)
    state = repo.create_session(topic="Photosynthesis")

    node = KnowledgeNode(
        concept="Chlorophyll",
        description="A pigment involved in photosynthesis.",
        attributes=["green", "absorbs light"],
        examples=["found in plant leaves"],
        status=NodeStatus.KNOWN,
        confidence=0.85,
        source=ProvenanceSource.USER,
    )
    state.nodes[node.id] = node
    state.turn_count = 1

    repo.save_session(state)

    reloaded = repo.load_session(state.session_id)
    assert reloaded.turn_count == 1
    assert len(reloaded.nodes) == 1

    reloaded_node = reloaded.find_node_by_concept("Chlorophyll")
    assert reloaded_node is not None
    assert reloaded_node.description == "A pigment involved in photosynthesis."
    assert reloaded_node.attributes == ["green", "absorbs light"]
    assert reloaded_node.examples == ["found in plant leaves"]
    assert reloaded_node.status == NodeStatus.KNOWN
    assert reloaded_node.confidence == pytest.approx(0.85)
    assert reloaded_node.source == ProvenanceSource.USER


def test_add_edge_and_reload(db_session):
    repo = SessionRepository(db_session)
    state = repo.create_session(topic="Photosynthesis")

    light = KnowledgeNode(concept="Light energy", status=NodeStatus.KNOWN)
    chemical = KnowledgeNode(concept="Chemical energy", status=NodeStatus.KNOWN)
    state.nodes[light.id] = light
    state.nodes[chemical.id] = chemical

    edge = KnowledgeEdge(
        source_node_id=light.id,
        target_node_id=chemical.id,
        relation_type=RelationType.CAUSES,
        description="Light energy is converted into chemical energy.",
        confidence=0.9,
    )
    state.edges.append(edge)

    repo.save_session(state)
    reloaded = repo.load_session(state.session_id)

    assert len(reloaded.edges) == 1
    reloaded_edge = reloaded.edges[0]
    assert reloaded_edge.source_node_id == light.id
    assert reloaded_edge.target_node_id == chemical.id
    assert reloaded_edge.relation_type == RelationType.CAUSES


def test_contradiction_and_question_round_trip(db_session):
    repo = SessionRepository(db_session)
    state = repo.create_session(topic="Physics")

    node_a = KnowledgeNode(concept="Force", status=NodeStatus.CONTRADICTORY)
    node_b = KnowledgeNode(concept="Mass", status=NodeStatus.KNOWN)
    state.nodes[node_a.id] = node_a
    state.nodes[node_b.id] = node_b

    state.contradictions.append(
        Contradiction(
            node_a_id=node_a.id,
            node_b_id=node_b.id,
            description="User gave two different definitions of Force.",
        )
    )

    state.questions_asked.append(
        CandidateQuestion(
            text="What causes the change from rest to motion?",
            category=QuestionCategory.MECHANISM,
            referenced_node_ids=[node_a.id],
            total_score=0.82,
        )
    )

    repo.save_session(state)
    reloaded = repo.load_session(state.session_id)

    assert len(reloaded.contradictions) == 1
    assert reloaded.contradictions[0].description == "User gave two different definitions of Force."
    assert reloaded.contradictions[0].resolved is False

    assert len(reloaded.questions_asked) == 1
    assert reloaded.questions_asked[0].category == QuestionCategory.MECHANISM
    assert reloaded.questions_asked[0].referenced_node_ids == [node_a.id]
    assert reloaded.questions_asked[0].total_score == pytest.approx(0.82)


def test_save_overwrites_previous_nodes_on_resave(db_session):
    """save_session does a full child-row replace — verify stale rows don't linger."""
    repo = SessionRepository(db_session)
    state = repo.create_session(topic="Recursion")

    node1 = KnowledgeNode(concept="Base case", status=NodeStatus.KNOWN)
    state.nodes[node1.id] = node1
    repo.save_session(state)

    # Reload, remove the node, add a different one, save again
    state = repo.load_session(state.session_id)
    state.nodes.clear()
    node2 = KnowledgeNode(concept="Recursive case", status=NodeStatus.UNCERTAIN)
    state.nodes[node2.id] = node2
    repo.save_session(state)

    reloaded = repo.load_session(state.session_id)
    assert len(reloaded.nodes) == 1
    assert reloaded.find_node_by_concept("Base case") is None
    assert reloaded.find_node_by_concept("Recursive case") is not None


def test_list_sessions(db_session):
    repo = SessionRepository(db_session)
    repo.create_session(topic="Topic A")
    repo.create_session(topic="Topic B")

    sessions = repo.list_sessions()
    assert len(sessions) == 2
    topics = {s["topic"] for s in sessions}
    assert topics == {"Topic A", "Topic B"}


def test_create_session_defaults_subject_to_general(db_session):
    repo = SessionRepository(db_session)
    state = repo.create_session(topic="Photosynthesis")
    assert state.subject == "General"

    reloaded = repo.load_session(state.session_id)
    assert reloaded.subject == "General"


def test_create_session_with_explicit_subject(db_session):
    repo = SessionRepository(db_session)
    state = repo.create_session(topic="Photosynthesis", subject="Biology")
    assert state.subject == "Biology"

    reloaded = repo.load_session(state.session_id)
    assert reloaded.subject == "Biology"


def test_list_sessions_includes_subject(db_session):
    repo = SessionRepository(db_session)
    repo.create_session(topic="Photosynthesis", subject="Biology")
    repo.create_session(topic="Fractions", subject="Math")

    sessions = repo.list_sessions()
    subjects = {s["subject"] for s in sessions}
    assert subjects == {"Biology", "Math"}


def test_list_sessions_includes_total_concepts(db_session):
    from schemas.knowledge import KnowledgeNode, NodeStatus

    repo = SessionRepository(db_session)
    state = repo.create_session(topic="Photosynthesis")
    node = KnowledgeNode(concept="Chlorophyll", status=NodeStatus.KNOWN)
    state.nodes[node.id] = node
    repo.save_session(state)

    sessions = repo.list_sessions()
    match = next(s for s in sessions if s["session_id"] == state.session_id)
    assert match["total_concepts"] == 1