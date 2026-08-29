"""
Grounding Validator — the anti-leakage enforcement layer.

Deliberately has ZERO LLM calls. Grounding is a deterministic graph lookup:
a question/claim is only allowed to reference concepts that actually exist
in the current session's knowledge state with real content. This is what
keeps the "knowledge boundary" (see project doc, CORE RESEARCH MOTIVATION)
enforced in code rather than trusted to prompt-following.

The LLM (question generator) proposes candidate questions and says which
node_ids they reference. This module only ever checks those references
against the graph — it never asks the LLM whether something is grounded.
"""

from __future__ import annotations

from knowledge.graph import get_node
from schemas.knowledge import (
    CandidateQuestion,
    ClaimGroundingStatus,
    KnowledgeNode,
    NodeStatus,
    SessionState,
)

# Statuses whose node content can be referenced as SUPPORTED.
_SUPPORTED_STATUSES = {NodeStatus.KNOWN, NodeStatus.PARTIALLY_UNDERSTOOD}

# CONTRADICTORY is allowed as SUPPORTED too, but only for the specific
# purpose of asking the user to resolve it — enforced by the caller
# (question generator) restricting which categories may target these nodes.
_CONTRADICTION_ALLOWED_STATUSES = {NodeStatus.CONTRADICTORY}

# UNCERTAIN is legitimate to probe further ("you said you're not sure
# about X — what makes you unsure?") but is weaker than SUPPORTED.
_INFERRED_STATUSES = {NodeStatus.UNCERTAIN, NodeStatus.UNKNOWN}


def classify_reference(node_id: str, state: SessionState) -> ClaimGroundingStatus:
    node: KnowledgeNode | None = get_node(state, node_id)
    if node is None:
        return ClaimGroundingStatus.UNSUPPORTED

    if node.status in _SUPPORTED_STATUSES or node.status in _CONTRADICTION_ALLOWED_STATUSES:
        return ClaimGroundingStatus.SUPPORTED
    if node.status in _INFERRED_STATUSES:
        return ClaimGroundingStatus.INFERRED

    return ClaimGroundingStatus.UNSUPPORTED


def grounding_score(referenced_node_ids: list[str], state: SessionState) -> float:
    if not referenced_node_ids:
        return 0.0
    statuses = [classify_reference(nid, state) for nid in referenced_node_ids]
    supported = sum(1 for s in statuses if s != ClaimGroundingStatus.UNSUPPORTED)
    return supported / len(statuses)


def overall_status(referenced_node_ids: list[str], state: SessionState) -> ClaimGroundingStatus:
    if not referenced_node_ids:
        return ClaimGroundingStatus.UNSUPPORTED

    statuses = [classify_reference(nid, state) for nid in referenced_node_ids]
    if any(s == ClaimGroundingStatus.UNSUPPORTED for s in statuses):
        return ClaimGroundingStatus.UNSUPPORTED
    if any(s == ClaimGroundingStatus.INFERRED for s in statuses):
        return ClaimGroundingStatus.INFERRED
    return ClaimGroundingStatus.SUPPORTED


def validate_candidate_question(
    candidate: CandidateQuestion, state: SessionState
) -> CandidateQuestion:
    status = overall_status(candidate.referenced_node_ids, state)
    candidate.grounding_status = status

    if status == ClaimGroundingStatus.UNSUPPORTED:
        candidate.unsupported_penalty = 1.0
    elif status == ClaimGroundingStatus.INFERRED:
        candidate.unsupported_penalty = 0.15
    else:
        candidate.unsupported_penalty = 0.0

    candidate.total_score = max(0.0, candidate.total_score - candidate.unsupported_penalty)
    return candidate


def select_grounded_question(
    candidates: list[CandidateQuestion], state: SessionState
) -> CandidateQuestion | None:
    validated = [validate_candidate_question(c, state) for c in candidates]
    grounded = [
        c for c in validated if c.grounding_status != ClaimGroundingStatus.UNSUPPORTED
    ]
    if not grounded:
        return None
    return max(grounded, key=lambda c: c.total_score)


def leakage_check(referenced_node_ids: list[str], state: SessionState) -> bool:
    return overall_status(referenced_node_ids, state) == ClaimGroundingStatus.UNSUPPORTED