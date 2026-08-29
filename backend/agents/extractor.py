"""
Knowledge Extractor agent.

Converts one user turn (a natural-language explanation) into a structured
ExtractionResult, using the LLM as a language-understanding component only.
The LLM is instructed never to add outside facts (see prompts/extractor.txt);
this file additionally never lets a malformed single item crash the whole
turn — it logs and skips instead, so one bad LLM response doesn't lose the
rest of a good extraction.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import ValidationError

from llm.client import LLMClient, LLMError
from schemas.knowledge import (
    ExtractedConcept,
    ExtractedRelationship,
    ExtractionResult,
    RelationType,
)

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "extractor.txt"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

_VALID_RELATION_VALUES = {r.value for r in RelationType}


def extract_knowledge(
    client: LLMClient,
    topic: str,
    known_concepts: list[dict],
    user_text: str,
) -> ExtractionResult:
    """
    known_concepts: list of {"concept": str, "description": str | None},
    a lightweight summary of the current graph — enough for the extractor
    to detect contradictions against prior teaching without exposing the
    full internal graph structure.
    """
    user_prompt = _build_user_prompt(topic, known_concepts, user_text)

    try:
        raw = client.complete_json(_SYSTEM_PROMPT, user_prompt)
    except LLMError as e:
        logger.warning("Extraction LLM call failed, returning empty extraction: %s", e)
        return ExtractionResult(raw_text=user_text)

    return _parse_extraction(raw, user_text)


def _build_user_prompt(topic: str, known_concepts: list[dict], user_text: str) -> str:
    if known_concepts:
        known_lines = "\n".join(
            f"- {c['concept']}: {c.get('description') or '(no description yet)'}"
            for c in known_concepts
        )
    else:
        known_lines = "(none yet — this is the first explanation in the session)"

    return (
        f"Topic: {topic}\n\n"
        f"Already taught in this session:\n{known_lines}\n\n"
        f"User's new explanation:\n{user_text}"
    )


def _parse_extraction(raw: dict, raw_text: str) -> ExtractionResult:
    concepts: list[ExtractedConcept] = []
    for item in raw.get("concepts", []):
        try:
            concepts.append(ExtractedConcept(**_normalize_concept_item(item)))
        except (ValidationError, TypeError) as e:
            logger.warning("Skipping malformed concept item %r: %s", item, e)

    relationships: list[ExtractedRelationship] = []
    for item in raw.get("relationships", []):
        try:
            relationships.append(
                ExtractedRelationship(**_normalize_relationship_item(item))
            )
        except (ValidationError, TypeError) as e:
            logger.warning("Skipping malformed relationship item %r: %s", item, e)

    contradictions = [
        str(c) for c in raw.get("contradictions_flagged", []) if isinstance(c, str)
    ]

    return ExtractionResult(
        raw_text=raw_text,
        concepts=concepts,
        relationships=relationships,
        contradictions_flagged=contradictions,
    )


def _normalize_concept_item(item: dict) -> dict:
    if not isinstance(item, dict) or "concept" not in item:
        raise TypeError("concept item missing required 'concept' field")

    confidence = item.get("confidence", 0.5)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    return {
        "concept": str(item["concept"]).strip(),
        "description": item.get("description") or None,
        "attributes": _as_str_list(item.get("attributes")),
        "examples": _as_str_list(item.get("examples")),
        "constraints": _as_str_list(item.get("constraints")),
        "conditions": _as_str_list(item.get("conditions")),
        "exceptions": _as_str_list(item.get("exceptions")),
        "uncertainty_expressed": bool(item.get("uncertainty_expressed", False)),
        "confidence": confidence,
    }


def _normalize_relationship_item(item: dict) -> dict:
    if not isinstance(item, dict):
        raise TypeError("relationship item is not an object")
    for field in ("source_concept", "target_concept"):
        if not item.get(field):
            raise TypeError(f"relationship item missing '{field}'")

    relation_type = str(item.get("relation_type", "relates_to")).strip().lower()
    if relation_type not in _VALID_RELATION_VALUES:
        relation_type = "relates_to"  # safe fallback rather than crashing

    confidence = item.get("confidence", 0.5)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    return {
        "source_concept": str(item["source_concept"]).strip(),
        "target_concept": str(item["target_concept"]).strip(),
        "relation_type": relation_type,
        "description": item.get("description") or None,
        "causal": bool(item.get("causal", False)),
        "confidence": confidence,
    }


def _as_str_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()]