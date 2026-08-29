from __future__ import annotations

from dataclasses import dataclass

from agents.grounding import (
    classify_reference,
    leakage_check,
)
from knowledge.gaps import detect_gaps
from schemas.knowledge import (
    CandidateQuestion,
    ClaimGroundingStatus,
    SessionState,
)


@dataclass
class ExtractionMetrics:
    """
    Deterministic comparison between expected concepts and
    concepts actually extracted by the system.
    """

    precision: float
    recall: float
    f1: float


def extraction_metrics(
    expected_concepts: set[str],
    actual_concepts: set[str],
) -> ExtractionMetrics:
    """
    Calculate precision, recall and F1 for extracted concepts.
    """

    if not actual_concepts:
        precision = 0.0
    else:
        precision = len(expected_concepts & actual_concepts) / len(actual_concepts)

    if not expected_concepts:
        recall = 1.0 if not actual_concepts else 0.0
    else:
        recall = len(expected_concepts & actual_concepts) / len(expected_concepts)

    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)

    return ExtractionMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
    )


def question_grounding_accuracy(
    questions: list[CandidateQuestion],
    state: SessionState,
) -> float:
    """
    Percentage of questions whose references are not unsupported.

    SUPPORTED and INFERRED both count as grounded enough to ask.
    UNSUPPORTED counts as leakage.
    """

    if not questions:
        return 1.0

    grounded = sum(
        1
        for question in questions
        if not leakage_check(question.referenced_node_ids, state)
    )

    return grounded / len(questions)


def leakage_rate(
    questions: list[CandidateQuestion],
    state: SessionState,
) -> float:
    """
    Percentage of candidate questions that reference
    unsupported concepts.
    """

    if not questions:
        return 0.0

    leaked = sum(
        1
        for question in questions
        if leakage_check(question.referenced_node_ids, state)
    )

    return leaked / len(questions)


def question_diversity(
    questions: list[CandidateQuestion],
) -> float:
    """
    Measures how many distinct graph nodes are touched by questions.

    0.0 = no questions
    1.0 = every question touches a completely new node set
    """

    if not questions:
        return 1.0

    seen_nodes: set[str] = set()
    unique_questions = 0

    for question in questions:
        nodes = set(question.referenced_node_ids)

        if not nodes:
            continue

        if not nodes.issubset(seen_nodes):
            unique_questions += 1

        seen_nodes.update(nodes)

    return unique_questions / len(questions)


def gap_coverage(
    state: SessionState,
) -> float:
    """
    Measures how many currently detected gaps have already
    been addressed by at least one question.

    A gap is considered covered when a previous question:
      - targets the same category, and
      - references at least one of the gap's nodes.
    """

    gaps = detect_gaps(state)

    if not gaps:
        return 1.0

    covered = 0

    for gap in gaps:
        gap_nodes = set(gap.node_ids)

        for question in state.questions_asked:
            question_nodes = set(question.referenced_node_ids)

            if (
                question.category == gap.category
                and gap_nodes & question_nodes
            ):
                covered += 1
                break

    return covered / len(gaps)