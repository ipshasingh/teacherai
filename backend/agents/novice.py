"""
Novice Reasoning Engine — orchestrates one full teaching turn.

Order: extract -> merge into graph -> generate a brief reflection ->
generate the next question. This is the file FastAPI calls; it never
touches the database itself (database/repository.py does that, called
by main.py) — keeps this fully testable with plain SessionState objects.

Reflection is generated deterministically from the graph diff, not via
an extra LLM call (see _generate_reflection) — keeps each turn to exactly
2 LLM calls (extraction + question phrasing), matching the project's
"explicit state over LLM judgment" principle.
"""

from __future__ import annotations

from pydantic import BaseModel

from agents.extractor import extract_knowledge
from agents.question_generator import generate_question
from knowledge.state import SessionSummary, summarize
from knowledge.updater import merge_extraction
from llm.client import LLMClient
from schemas.knowledge import (
    CandidateQuestion,
    ExtractionResult,
    NodeStatus,
    SessionState,
)

# Statuses worth showing the extractor as "already taught" context.
# UNKNOWN stubs are excluded — they have no real content to compare against.
_CONTEXT_STATUSES = (
    NodeStatus.KNOWN,
    NodeStatus.PARTIALLY_UNDERSTOOD,
    NodeStatus.UNCERTAIN,
    NodeStatus.CONTRADICTORY,
)


class TurnResult(BaseModel):
    reflection: str
    question: CandidateQuestion | None
    summary: SessionSummary


def process_turn(client: LLMClient, state: SessionState, user_text: str) -> TurnResult:
    """
    Mutates `state` in place (adds/enriches nodes, may append a question to
    questions_asked) and returns a TurnResult describing what happened.
    Caller is responsible for persisting `state` afterward.
    """
    known_concepts = _known_concepts_context(state)

    extraction = extract_knowledge(client, state.topic, known_concepts, user_text)
    merge_extraction(state, extraction)

    reflection = _generate_reflection(extraction, state)

    question = generate_question(client, state)
    if question is not None:
        state.questions_asked.append(question)

    return TurnResult(reflection=reflection, question=question, summary=summarize(state))


def _known_concepts_context(state: SessionState) -> list[dict]:
    return [
        {"concept": n.concept, "description": n.description}
        for n in state.nodes.values()
        if n.status in _CONTEXT_STATUSES
    ]


def _generate_reflection(extraction: ExtractionResult, state: SessionState) -> str:
    if not extraction.concepts and not extraction.relationships:
        return "I'm not sure I caught anything new there — could you explain a bit more?"

    if extraction.contradictions_flagged:
        return (
            "Wait, that seems to conflict with something you told me earlier. "
            "Let me make sure I have both versions."
        )

    touched_names = [c.concept for c in extraction.concepts]

    contradictory_touched = sorted(
        {
            n.concept.replace(" (revised)", "")
            for n in state.nodes.values()
            if n.status == NodeStatus.CONTRADICTORY
            and n.concept.replace(" (revised)", "") in touched_names
        }
    )
    if contradictory_touched:
        return (
            f"Hold on — what you just said about {contradictory_touched[0]} doesn't "
            f"match what you told me before. Which one is right?"
        )

    if not touched_names:
        return "Got it — I've noted that."
    if len(touched_names) == 1:
        return f"Okay, I think I understand {touched_names[0]} now."
    return f"Okay, I think I understand {', '.join(touched_names[:-1])} and {touched_names[-1]} now."