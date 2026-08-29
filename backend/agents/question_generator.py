"""
Question Generator agent.

Two-stage, matching the project's "explicit state over LLM judgment"
principle:
  1. Deterministic gap detection (knowledge/gaps.py) decides WHAT needs
     asking about and WHY — no LLM involved.
  2. The LLM only PHRASES the top gaps into natural novice-style question
     text. It does not choose topics or invent references.
  3. Every phrased question still passes through the grounding validator
     before being returned, as a final structural safety net.
"""

from __future__ import annotations

import logging
from pathlib import Path

from agents.grounding import select_grounded_question
from knowledge.gaps import GapSignal, detect_gaps
from llm.client import LLMClient, LLMError
from schemas.knowledge import CandidateQuestion, SessionState

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "question_generator.txt"
_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

_MAX_GAPS_CONSIDERED = 6


def generate_question(client: LLMClient, state: SessionState) -> CandidateQuestion | None:
    """
    Returns the single best grounded question to ask next, or None if
    there's nothing left to ask (either no gaps exist, or everything
    detected has already been asked about).
    """
    gaps = detect_gaps(state)
    if not gaps:
        return None

    ranked_gaps = _rank_and_filter_gaps(gaps, state)
    if not ranked_gaps:
        return None

    top_gaps = ranked_gaps[:_MAX_GAPS_CONSIDERED]
    candidates = _phrase_candidates(client, state, top_gaps)
    if not candidates:
        return None

    return select_grounded_question(candidates, state)


def _rank_and_filter_gaps(gaps: list[GapSignal], state: SessionState) -> list[GapSignal]:
    scored = []
    for gap in gaps:
        redundancy = _redundancy_penalty(gap, state)
        fatigue = _fatigue_penalty(gap, state)
        score = (gap.importance_score * 0.5 + gap.gap_score * 0.5) - redundancy - fatigue
        if score <= 0:
            continue
        scored.append((score, gap))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [gap for _, gap in scored]


def _fatigue_penalty(gap: GapSignal, state: SessionState) -> float:
    """Diminishing returns per node: the more times a node has already been
    asked about (any category), the less likely it's picked again — keeps
    the session moving to new concepts instead of drilling one forever."""
    gap_nodes = set(gap.node_ids)
    times_touched = sum(
        1 for asked in state.questions_asked if set(asked.referenced_node_ids) & gap_nodes
    )
    return min(0.6, times_touched * 0.2)

def _redundancy_penalty(gap: GapSignal, state: SessionState) -> float:
    gap_node_set = set(gap.node_ids)
    for asked in state.questions_asked:
        if asked.category == gap.category and set(asked.referenced_node_ids) == gap_node_set:
            return 1.0
    return 0.0


def _phrase_candidates(
    client: LLMClient, state: SessionState, gaps: list[GapSignal]
) -> list[CandidateQuestion]:
    user_prompt = _build_user_prompt(state, gaps)
    try:
        raw = client.complete_json(_SYSTEM_PROMPT, user_prompt)
    except LLMError as e:
        logger.warning("Question phrasing LLM call failed: %s", e)
        return []

    phrasings = raw.get("questions", [])
    candidates: list[CandidateQuestion] = []
    for i, gap in enumerate(gaps):
        if i >= len(phrasings):
            break
        item = phrasings[i]
        text = str(item.get("text", "")).strip() if isinstance(item, dict) else ""
        if not text:
            continue
        candidates.append(
            CandidateQuestion(
                text=text,
                category=gap.category,
                referenced_node_ids=gap.node_ids,
                relevance_score=gap.gap_score,
                gap_score=gap.gap_score,
                importance_score=gap.importance_score,
                total_score=(gap.importance_score * 0.5 + gap.gap_score * 0.5),
            )
        )
    return candidates


def _build_user_prompt(state: SessionState, gaps: list[GapSignal]) -> str:
    lines = [
        f"{i + 1}. Category: {gap.category.value}\n   Context: {gap.context}"
        for i, gap in enumerate(gaps)
    ]
    gaps_text = "\n".join(lines)
    return (
        f"Topic: {state.topic}\n\n"
        f"Here are {len(gaps)} knowledge gaps, each already identified by the system. "
        f"For EACH one, write ONE natural, concise novice-learner question that addresses "
        f"exactly that gap and nothing more. Do not add outside facts.\n\n"
        f"{gaps_text}"
    )