from agents.grounding import leakage_check
from evaluation.metrics import (
    ExtractionMetrics,
    extraction_metrics,
    gap_coverage,
    leakage_rate,
    question_diversity,
    question_grounding_accuracy,
)
from schemas.knowledge import (
    CandidateQuestion,
    KnowledgeNode,
    NodeStatus,
    SessionState,
)


def test_extraction_metrics_perfect_match():
    concepts = {"photosynthesis", "chlorophyll"}

    metrics = extraction_metrics(concepts, concepts)

    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1 == 1.0


def test_extraction_metrics_extra_concept_reduces_precision():
    expected = {"photosynthesis", "chlorophyll"}
    actual = {"photosynthesis", "chlorophyll", "sunlight"}

    metrics = extraction_metrics(expected, actual)

    assert metrics.precision == 2 / 3
    assert metrics.recall == 1.0


def test_extraction_metrics_missing_concept_reduces_recall():
    expected = {"photosynthesis", "chlorophyll", "sunlight"}
    actual = {"photosynthesis", "chlorophyll"}

    metrics = extraction_metrics(expected, actual)

    assert metrics.precision == 1.0
    assert metrics.recall == 2 / 3


def test_empty_extraction_has_zero_precision():
    metrics = extraction_metrics(
        {"photosynthesis"},
        set(),
    )

    assert metrics.precision == 0.0
    assert metrics.recall == 0.0
    assert metrics.f1 == 0.0


def test_grounding_accuracy_all_supported():
    state = SessionState(
        topic="Photosynthesis",
        nodes={
            "1": KnowledgeNode(
                id="1",
                concept="Photosynthesis",
                description="A process",
                status=NodeStatus.KNOWN,
            )
        },
    )

    questions = [
        CandidateQuestion(
            text="What is photosynthesis?",
            category="definition",
            referenced_node_ids=["1"],
        )
    ]

    assert question_grounding_accuracy(questions, state) == 1.0
    assert leakage_rate(questions, state) == 0.0


def test_unsupported_question_counts_as_leakage():
    state = SessionState(topic="Photosynthesis")

    questions = [
        CandidateQuestion(
            text="What is quantum mechanics?",
            category="definition",
            referenced_node_ids=["does-not-exist"],
        )
    ]

    assert question_grounding_accuracy(questions, state) == 0.0
    assert leakage_rate(questions, state) == 1.0


def test_question_diversity_rewards_new_nodes():
    questions = [
        CandidateQuestion(
            text="Q1",
            category="definition",
            referenced_node_ids=["1"],
        ),
        CandidateQuestion(
            text="Q2",
            category="definition",
            referenced_node_ids=["2"],
        ),
        CandidateQuestion(
            text="Q3",
            category="definition",
            referenced_node_ids=["3"],
        ),
    ]

    assert question_diversity(questions) == 1.0


def test_question_diversity_detects_repeated_node():
    questions = [
        CandidateQuestion(
            text="Q1",
            category="definition",
            referenced_node_ids=["1"],
        ),
        CandidateQuestion(
            text="Q2",
            category="definition",
            referenced_node_ids=["1"],
        ),
    ]

    assert question_diversity(questions) == 0.5