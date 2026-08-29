"""
Tests for agents/novice.py (the turn orchestrator).

FakeLLMClient distinguishes extraction calls from question-phrasing calls
by sniffing the prompt content (both go through the same complete_json
method in real usage since novice.py calls both extract_knowledge and
generate_question with the same LLMClient instance).
"""

from agents.novice import process_turn
from schemas.knowledge import NodeStatus, SessionState


class FakeLLMClient:
    """Returns a canned concept extraction for extractor calls, and a
    canned phrased question for question-generator calls."""

    def complete_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.2):
        if "knowledge gaps" in user_prompt.lower():
            n = user_prompt.count("Category:")
            return {"questions": [{"text": f"Follow-up question {i + 1}?"} for i in range(n)]}

        return {
            "concepts": [
                {
                    "concept": "Binary Search Tree",
                    "description": "A tree where left children are smaller than the parent.",
                    "attributes": ["ordered"],
                    "examples": [],
                    "constraints": [],
                    "conditions": [],
                    "exceptions": [],
                    "uncertainty_expressed": False,
                    "confidence": 0.9,
                }
            ],
            "relationships": [],
            "contradictions_flagged": [],
        }


class EmptyExtractionClient:
    """Simulates a turn where the user said something the extractor
    couldn't parse into any structured knowledge."""

    def complete_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.2):
        if "knowledge gaps" in user_prompt.lower():
            return {"questions": []}
        return {"concepts": [], "relationships": [], "contradictions_flagged": []}


def test_process_turn_creates_node_from_extraction():
    state = SessionState(topic="Data Structures")
    result = process_turn(FakeLLMClient(), state, "A BST is a tree where left children are smaller.")

    node = state.find_node_by_concept("Binary Search Tree")
    assert node is not None
    assert node.status == NodeStatus.KNOWN
    assert result.summary.total_concepts == 1


def test_process_turn_increments_turn_count():
    state = SessionState(topic="Data Structures")
    process_turn(FakeLLMClient(), state, "some explanation")
    assert state.turn_count == 1

    process_turn(FakeLLMClient(), state, "some more explanation")
    assert state.turn_count == 2


def test_process_turn_generates_and_stores_question():
    state = SessionState(topic="Data Structures")
    result = process_turn(FakeLLMClient(), state, "A BST is a tree where left children are smaller.")

    # a DEFINITION or EXAMPLE gap should exist on the freshly created thin node
    assert result.question is not None
    assert len(state.questions_asked) == 1
    assert state.questions_asked[0].text == result.question.text


def test_process_turn_reflection_names_the_taught_concept():
    state = SessionState(topic="Data Structures")
    result = process_turn(FakeLLMClient(), state, "A BST is a tree where left children are smaller.")
    assert "Binary Search Tree" in result.reflection


def test_process_turn_with_no_extraction_gives_fallback_reflection():
    state = SessionState(topic="Data Structures")
    result = process_turn(EmptyExtractionClient(), state, "uh, I don't really know")

    assert "could you explain" in result.reflection.lower()
    assert result.question is None
    assert len(state.nodes) == 0


def test_process_turn_returns_summary_matching_state():
    state = SessionState(topic="Data Structures")
    result = process_turn(FakeLLMClient(), state, "A BST is a tree where left children are smaller.")

    assert result.summary.session_id == state.session_id
    assert result.summary.turn_count == state.turn_count