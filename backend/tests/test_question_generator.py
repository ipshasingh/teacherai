"""
Tests for agents/question_generator.py.

Uses FakeLLMClient for phrasing (deterministic, no network). Gap detection
and ranking are already covered in test_gaps.py — these tests focus on
the ranking/redundancy/phrasing/grounding pipeline end to end.
"""

from agents.question_generator import generate_question
from schemas.knowledge import (
    CandidateQuestion,
    KnowledgeEdge,
    KnowledgeNode,
    NodeStatus,
    QuestionCategory,
    RelationType,
    SessionState,
)


class FakeLLMClient:
    """Returns one phrased question per gap it's given, echoing a counter
    into the text so tests can tell which gap produced which question."""

    def complete_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.2):
        # crude but sufficient: count how many "Category:" lines are in the
        # prompt to know how many questions to return
        n = user_prompt.count("Category:")
        return {"questions": [{"text": f"Generated question #{i + 1}?"} for i in range(n)]}


class EmptyLLMClient:
    def complete_json(self, *args, **kwargs):
        return {"questions": []}


def test_no_gaps_returns_none():
    state = SessionState(topic="Topic")
    result = generate_question(FakeLLMClient(), state)
    assert result is None


def test_generates_question_for_uncertain_node():
    state = SessionState(topic="Topic")
    node = KnowledgeNode(concept="AVL Tree", status=NodeStatus.UNCERTAIN, description="maybe balanced")
    state.nodes[node.id] = node

    result = generate_question(FakeLLMClient(), state)
    assert result is not None
    assert result.category == QuestionCategory.CLARIFICATION
    assert result.referenced_node_ids == [node.id]
    assert "Generated question" in result.text


def test_contradiction_gap_is_prioritized_over_others():
    state = SessionState(topic="Topic")
    # a lower-priority definition gap
    thin = KnowledgeNode(concept="Thin", status=NodeStatus.KNOWN, description="short desc")
    state.nodes[thin.id] = thin

    # a higher-priority contradiction
    a = KnowledgeNode(concept="A", status=NodeStatus.CONTRADICTORY)
    b = KnowledgeNode(concept="A (revised)", status=NodeStatus.CONTRADICTORY)
    state.nodes[a.id] = a
    state.nodes[b.id] = b
    from schemas.knowledge import Contradiction
    state.contradictions.append(Contradiction(node_a_id=a.id, node_b_id=b.id, description="conflict"))

    result = generate_question(FakeLLMClient(), state)
    assert result is not None
    assert result.category == QuestionCategory.CONTRADICTION_RESOLUTION

def test_prerequisite_question_on_unknown_node_is_allowed():
    """This is the case that required the grounding refinement: a node
    named by the user but not yet described must still be askable."""
    state = SessionState(topic="Topic")
    known = KnowledgeNode(
        concept="Photosynthesis",
        status=NodeStatus.KNOWN,
        description="Converts light energy into chemical energy inside plant cells.",
        examples=["happens in leaves"],
    )
    stub = KnowledgeNode(concept="Chlorophyll", status=NodeStatus.UNKNOWN)
    state.nodes[known.id] = known
    state.nodes[stub.id] = stub
    state.edges.append(
        KnowledgeEdge(
            source_node_id=known.id, target_node_id=stub.id, relation_type=RelationType.RELATES_TO
        )
    )

    result = generate_question(FakeLLMClient(), state)
    assert result is not None
    assert result.category == QuestionCategory.PREREQUISITE
    assert result.grounding_status is not None
    assert result.grounding_status.value != "unsupported"

def test_already_asked_gap_is_not_regenerated():
    state = SessionState(topic="Topic")
    node = KnowledgeNode(concept="AVL Tree", status=NodeStatus.UNCERTAIN, description="maybe balanced")
    state.nodes[node.id] = node

    # simulate having already asked the exact clarification question about this node
    state.questions_asked.append(
        CandidateQuestion(
            text="Already asked this",
            category=QuestionCategory.CLARIFICATION,
            referenced_node_ids=[node.id],
            total_score=0.7,
        )
    )

    result = generate_question(FakeLLMClient(), state)
    assert result is None  # nothing left to ask


def test_llm_returning_no_questions_yields_none():
    state = SessionState(topic="Topic")
    node = KnowledgeNode(concept="AVL Tree", status=NodeStatus.UNCERTAIN, description="maybe balanced")
    state.nodes[node.id] = node

    result = generate_question(EmptyLLMClient(), state)
    assert result is None


def test_generated_question_is_added_to_state_by_caller_not_generator():
    """generate_question should NOT mutate state.questions_asked itself —
    that's the novice reasoning engine's job once the question is actually
    sent to the user (it might be discarded/regenerated first)."""
    state = SessionState(topic="Topic")
    node = KnowledgeNode(concept="AVL Tree", status=NodeStatus.UNCERTAIN, description="maybe balanced")
    state.nodes[node.id] = node

    generate_question(FakeLLMClient(), state)
    assert len(state.questions_asked) == 0