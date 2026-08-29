"""
Tests for agents/extractor.py.

Uses a FakeLLMClient (duck-typed, same interface as LLMClient.complete_json)
so these tests never hit the real Groq API — fast, free, and deterministic.
"""

from agents.extractor import extract_knowledge
from schemas.knowledge import NodeStatus, RelationType


class FakeLLMClient:
    """Stand-in for llm.client.LLMClient — returns a pre-set dict."""

    def __init__(self, response: dict):
        self._response = response

    def complete_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.2):
        return self._response


class RaisingLLMClient:
    """Simulates an LLM call that fails outright."""

    def complete_json(self, *args, **kwargs):
        from llm.client import LLMError
        raise LLMError("simulated failure")


def test_extracts_well_formed_concept():
    fake = FakeLLMClient(
        {
            "concepts": [
                {
                    "concept": "Binary Search Tree",
                    "description": "A tree where left children are smaller.",
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
    )

    result = extract_knowledge(fake, "Data Structures", [], "A BST is a tree where left children are smaller.")

    assert len(result.concepts) == 1
    assert result.concepts[0].concept == "Binary Search Tree"
    assert result.concepts[0].attributes == ["ordered"]
    assert result.concepts[0].confidence == 0.9


def test_extracts_relationship_with_valid_relation_type():
    fake = FakeLLMClient(
        {
            "concepts": [],
            "relationships": [
                {
                    "source_concept": "Light energy",
                    "target_concept": "Chemical energy",
                    "relation_type": "causes",
                    "description": "converted into",
                    "causal": True,
                    "confidence": 0.85,
                }
            ],
            "contradictions_flagged": [],
        }
    )

    result = extract_knowledge(fake, "Photosynthesis", [], "Light energy is converted into chemical energy.")

    assert len(result.relationships) == 1
    assert result.relationships[0].relation_type == RelationType.CAUSES
    assert result.relationships[0].causal is True


def test_invalid_relation_type_falls_back_to_relates_to():
    fake = FakeLLMClient(
        {
            "concepts": [],
            "relationships": [
                {
                    "source_concept": "A",
                    "target_concept": "B",
                    "relation_type": "some_made_up_type",
                    "confidence": 0.7,
                }
            ],
            "contradictions_flagged": [],
        }
    )

    result = extract_knowledge(fake, "Topic", [], "A leads to B.")

    assert result.relationships[0].relation_type == RelationType.RELATES_TO


def test_malformed_concept_item_is_skipped_not_crashing():
    fake = FakeLLMClient(
        {
            "concepts": [
                {"description": "missing the required concept field"},
                {
                    "concept": "Valid Concept",
                    "description": "This one is fine.",
                    "confidence": 0.8,
                },
            ],
            "relationships": [],
            "contradictions_flagged": [],
        }
    )

    result = extract_knowledge(fake, "Topic", [], "some text")

    assert len(result.concepts) == 1
    assert result.concepts[0].concept == "Valid Concept"


def test_missing_relationship_field_is_skipped():
    fake = FakeLLMClient(
        {
            "concepts": [],
            "relationships": [
                {"source_concept": "A"},  # missing target_concept
                {
                    "source_concept": "C",
                    "target_concept": "D",
                    "relation_type": "depends_on",
                    "confidence": 0.6,
                },
            ],
            "contradictions_flagged": [],
        }
    )

    result = extract_knowledge(fake, "Topic", [], "some text")

    assert len(result.relationships) == 1
    assert result.relationships[0].source_concept == "C"


def test_confidence_out_of_range_is_clamped():
    fake = FakeLLMClient(
        {
            "concepts": [
                {"concept": "X", "description": "desc", "confidence": 5.0},
            ],
            "relationships": [],
            "contradictions_flagged": [],
        }
    )

    result = extract_knowledge(fake, "Topic", [], "some text")
    assert result.concepts[0].confidence == 1.0


def test_contradictions_flagged_are_passed_through():
    fake = FakeLLMClient(
        {
            "concepts": [],
            "relationships": [],
            "contradictions_flagged": ["User contradicted the earlier claim about X."],
        }
    )

    result = extract_knowledge(fake, "Topic", [], "some text")
    assert result.contradictions_flagged == ["User contradicted the earlier claim about X."]


def test_llm_failure_returns_empty_extraction_not_crash():
    result = extract_knowledge(RaisingLLMClient(), "Topic", [], "some text")

    assert result.concepts == []
    assert result.relationships == []
    assert result.raw_text == "some text"


def test_known_concepts_are_included_in_prompt_context():
    """Sanity check that known_concepts actually reaches the prompt — we
    can't inspect the real prompt text through FakeLLMClient easily, so we
    use a small client that records what it was called with."""

    captured = {}

    class RecordingClient:
        def complete_json(self, system_prompt, user_prompt, temperature=0.2):
            captured["user_prompt"] = user_prompt
            return {"concepts": [], "relationships": [], "contradictions_flagged": []}

    extract_knowledge(
        RecordingClient(),
        "Cells",
        [{"concept": "Mitochondria", "description": "The powerhouse of the cell."}],
        "New explanation here.",
    )

    assert "Mitochondria" in captured["user_prompt"]
    assert "powerhouse of the cell" in captured["user_prompt"]