"""
Tests for agents/grounding.py.

No LLM, no fake client needed — grounding is pure graph lookup by design.
These tests are the closest thing this project has to a direct test of
the "knowledge boundary" itself.
"""

from agents.grounding import (
    classify_reference,
    grounding_score,
    leakage_check,
    overall_status,
    select_grounded_question,
    validate_candidate_question,
)
from schemas.knowledge import (
    CandidateQuestion,
    ClaimGroundingStatus,
    KnowledgeNode,
    NodeStatus,
    QuestionCategory,
    SessionState,
)


def make_state_with_node(status: NodeStatus, concept: str = "Chlorophyll") -> tuple[SessionState, str]:
    state = SessionState(topic="Photosynthesis")
    node = KnowledgeNode(concept=concept, description="a pigment", status=status)
    state.nodes[node.id] = node
    return state, node.id


# ---------------------------------------------------------------------------
# classify_reference
# ---------------------------------------------------------------------------

def test_known_node_is_supported():
    state, node_id = make_state_with_node(NodeStatus.KNOWN)
    assert classify_reference(node_id, state) == ClaimGroundingStatus.SUPPORTED


def test_partially_understood_node_is_supported():
    state, node_id = make_state_with_node(NodeStatus.PARTIALLY_UNDERSTOOD)
    assert classify_reference(node_id, state) == ClaimGroundingStatus.SUPPORTED


def test_uncertain_node_is_inferred():
    state, node_id = make_state_with_node(NodeStatus.UNCERTAIN)
    assert classify_reference(node_id, state) == ClaimGroundingStatus.INFERRED


def test_contradictory_node_is_supported_for_resolution():
    state, node_id = make_state_with_node(NodeStatus.CONTRADICTORY)
    assert classify_reference(node_id, state) == ClaimGroundingStatus.SUPPORTED


def test_unknown_status_node_is_inferred():
    """A node that exists (the user named the concept) but has no content
    yet is weakly grounded — enough to ask a PREREQUISITE question about,
    but not enough to assert anything about. True leakage is a node that
    doesn't exist in the graph at all (see test below)."""
    state, node_id = make_state_with_node(NodeStatus.UNKNOWN)
    assert classify_reference(node_id, state) == ClaimGroundingStatus.INFERRED

def test_nonexistent_node_id_is_unsupported():
    state = SessionState(topic="Photosynthesis")
    assert classify_reference("does-not-exist", state) == ClaimGroundingStatus.UNSUPPORTED


# ---------------------------------------------------------------------------
# overall_status — the classic "chlorophyll" example from the project doc
# ---------------------------------------------------------------------------

def test_question_about_taught_concept_is_supported():
    """'What do you mean by chemical energy?' — allowed, per doc example."""
    state, node_id = make_state_with_node(NodeStatus.KNOWN, concept="Chemical energy")
    assert overall_status([node_id], state) == ClaimGroundingStatus.SUPPORTED


def test_question_about_untaught_concept_is_rejected():
    """'What role does chlorophyll play?' when chlorophyll was never taught
    — must be rejected, per doc example in component 6."""
    state = SessionState(topic="Photosynthesis")  # empty — nothing taught
    assert overall_status(["some-untaught-node-id"], state) == ClaimGroundingStatus.UNSUPPORTED


def test_weakest_link_inferred_when_mixing_known_and_unknown_status():
    """A KNOWN node + a named-but-undescribed (UNKNOWN status) node are only
    as strong as the weakest reference: INFERRED, not rejected outright,
    since both were genuinely introduced by the user."""
    state = SessionState(topic="Photosynthesis")
    good_node = KnowledgeNode(concept="Light energy", status=NodeStatus.KNOWN)
    stub_node = KnowledgeNode(concept="Chlorophyll", status=NodeStatus.UNKNOWN)
    state.nodes[good_node.id] = good_node
    state.nodes[stub_node.id] = stub_node

    status = overall_status([good_node.id, stub_node.id], state)
    assert status == ClaimGroundingStatus.INFERRED


def test_weakest_link_unsupported_when_node_was_never_introduced():
    """True leakage: a node id that isn't in the graph at all (the user
    never named this concept) rejects the whole question."""
    state = SessionState(topic="Photosynthesis")
    good_node = KnowledgeNode(concept="Light energy", status=NodeStatus.KNOWN)
    state.nodes[good_node.id] = good_node

    status = overall_status([good_node.id, "never-mentioned-node-id"], state)
    assert status == ClaimGroundingStatus.UNSUPPORTED

def test_empty_reference_list_is_unsupported():
    state = SessionState(topic="Topic")
    assert overall_status([], state) == ClaimGroundingStatus.UNSUPPORTED


# ---------------------------------------------------------------------------
# grounding_score
# ---------------------------------------------------------------------------

def test_grounding_score_all_supported_is_one():
    state, node_id = make_state_with_node(NodeStatus.KNOWN)
    assert grounding_score([node_id], state) == 1.0


def test_grounding_score_mixed_references():
    state = SessionState(topic="Topic")
    known = KnowledgeNode(concept="A", status=NodeStatus.KNOWN)
    state.nodes[known.id] = known

    # one grounded reference, one reference to a node that was never introduced
    score = grounding_score([known.id, "does-not-exist"], state)
    assert score == 0.5

def test_grounding_score_empty_list_is_zero():
    state = SessionState(topic="Topic")
    assert grounding_score([], state) == 0.0


# ---------------------------------------------------------------------------
# validate_candidate_question
# ---------------------------------------------------------------------------

def test_validate_unsupported_question_gets_full_penalty():
    state = SessionState(topic="Topic")
    candidate = CandidateQuestion(
        text="What role does chlorophyll play?",
        category=QuestionCategory.MECHANISM,
        referenced_node_ids=["untaught-node"],
        total_score=0.8,
    )
    validated = validate_candidate_question(candidate, state)
    assert validated.grounding_status == ClaimGroundingStatus.UNSUPPORTED
    assert validated.total_score == 0.0  # 0.8 - 1.0 penalty, clamped at 0


def test_validate_supported_question_keeps_score():
    state, node_id = make_state_with_node(NodeStatus.KNOWN)
    candidate = CandidateQuestion(
        text="What do you mean by chlorophyll?",
        category=QuestionCategory.DEFINITION,
        referenced_node_ids=[node_id],
        total_score=0.8,
    )
    validated = validate_candidate_question(candidate, state)
    assert validated.grounding_status == ClaimGroundingStatus.SUPPORTED
    assert validated.total_score == 0.8


def test_validate_inferred_question_gets_small_penalty():
    state, node_id = make_state_with_node(NodeStatus.UNCERTAIN)
    candidate = CandidateQuestion(
        text="You said you're not sure about this — why?",
        category=QuestionCategory.CLARIFICATION,
        referenced_node_ids=[node_id],
        total_score=0.8,
    )
    validated = validate_candidate_question(candidate, state)
    assert validated.grounding_status == ClaimGroundingStatus.INFERRED
    assert validated.total_score == 0.65


# ---------------------------------------------------------------------------
# select_grounded_question
# ---------------------------------------------------------------------------

def test_select_grounded_question_picks_highest_scoring_valid_candidate():
    state, node_id = make_state_with_node(NodeStatus.KNOWN)
    good = CandidateQuestion(
        text="Good question",
        category=QuestionCategory.DEFINITION,
        referenced_node_ids=[node_id],
        total_score=0.6,
    )
    better = CandidateQuestion(
        text="Better question",
        category=QuestionCategory.MECHANISM,
        referenced_node_ids=[node_id],
        total_score=0.9,
    )
    unsupported = CandidateQuestion(
        text="Ungrounded question",
        category=QuestionCategory.MECHANISM,
        referenced_node_ids=["nonexistent"],
        total_score=0.95,  # would win on raw score, but must be rejected
    )

    selected = select_grounded_question([good, better, unsupported], state)
    assert selected is not None
    assert selected.text == "Better question"


def test_select_grounded_question_returns_none_when_all_unsupported():
    state = SessionState(topic="Topic")
    candidates = [
        CandidateQuestion(
            text="Bad question",
            category=QuestionCategory.MECHANISM,
            referenced_node_ids=["nonexistent"],
            total_score=0.9,
        )
    ]
    assert select_grounded_question(candidates, state) is None


def test_select_grounded_question_empty_list_returns_none():
    state = SessionState(topic="Topic")
    assert select_grounded_question([], state) is None


# ---------------------------------------------------------------------------
# leakage_check
# ---------------------------------------------------------------------------

def test_leakage_check_true_for_untaught_reference():
    state = SessionState(topic="Topic")
    assert leakage_check(["untaught"], state) is True


def test_leakage_check_false_for_taught_reference():
    state, node_id = make_state_with_node(NodeStatus.KNOWN)
    assert leakage_check([node_id], state) is False