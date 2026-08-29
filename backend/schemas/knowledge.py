"""
Core data contracts for Feynman's explicit knowledge state.

These models are the "memory" of the system. The LLM never holds state;
everything the agent is allowed to know must be representable here.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NodeStatus(str, Enum):
    KNOWN = "known"
    UNCERTAIN = "uncertain"
    PARTIALLY_UNDERSTOOD = "partially_understood"
    CONTRADICTORY = "contradictory"
    CORRECTED = "corrected"
    UNKNOWN = "unknown"


class ProvenanceSource(str, Enum):
    USER = "user"
    # Reserved for future extension (e.g. inferred-by-agent), but V1 should
    # almost always be USER. Anything else must be justified explicitly.
    INFERRED = "inferred"


class RelationType(str, Enum):
    IS_A = "is_a"
    HAS_ATTRIBUTE = "has_attribute"
    RELATES_TO = "relates_to"
    CAUSES = "causes"
    PRECEDES = "precedes"
    PART_OF = "part_of"
    EXAMPLE_OF = "example_of"
    CONTRADICTS = "contradicts"
    DEPENDS_ON = "depends_on"


class ClaimGroundingStatus(str, Enum):
    SUPPORTED = "supported"
    INFERRED = "inferred"
    UNSUPPORTED = "unsupported"


# ---------------------------------------------------------------------------
# Raw extraction output (what the extractor agent produces per user turn)
# ---------------------------------------------------------------------------

class ExtractedConcept(BaseModel):
    concept: str
    description: Optional[str] = None
    attributes: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    uncertainty_expressed: bool = False
    source: ProvenanceSource = ProvenanceSource.USER
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class ExtractedRelationship(BaseModel):
    source_concept: str
    target_concept: str
    relation_type: RelationType
    description: Optional[str] = None
    causal: bool = False
    source: ProvenanceSource = ProvenanceSource.USER
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class ExtractionResult(BaseModel):
    """Output of the Knowledge Extractor for a single user turn."""
    raw_text: str
    concepts: list[ExtractedConcept] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)
    contradictions_flagged: list[str] = Field(default_factory=list)
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Persistent knowledge graph representation
# ---------------------------------------------------------------------------

class KnowledgeNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    concept: str
    description: Optional[str] = None
    attributes: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    status: NodeStatus = NodeStatus.UNKNOWN
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source: ProvenanceSource = ProvenanceSource.USER
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    times_referenced: int = 0
    times_clarified: int = 0


class KnowledgeEdge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source_node_id: str
    target_node_id: str
    relation_type: RelationType
    description: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source: ProvenanceSource = ProvenanceSource.USER
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Contradiction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    node_a_id: str
    node_b_id: str
    description: str
    resolved: bool = False
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------

class QuestionCategory(str, Enum):
    CLARIFICATION = "clarification"
    DEFINITION = "definition"
    RELATIONSHIP = "relationship"
    MECHANISM = "mechanism"
    CAUSE = "cause"
    CONSEQUENCE = "consequence"
    PREREQUISITE = "prerequisite"
    BOUNDARY_CONDITION = "boundary_condition"
    EXAMPLE = "example"
    COUNTEREXAMPLE = "counterexample"
    GENERALIZATION = "generalization"
    CONTRADICTION_RESOLUTION = "contradiction_resolution"


class CandidateQuestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    category: QuestionCategory
    referenced_node_ids: list[str] = Field(default_factory=list)
    relevance_score: float = 0.0
    gap_score: float = 0.0
    importance_score: float = 0.0
    redundancy_penalty: float = 0.0
    unsupported_penalty: float = 0.0
    total_score: float = 0.0
    grounding_status: Optional[ClaimGroundingStatus] = None


# ---------------------------------------------------------------------------
# Session state (the full explicit memory for one teaching session)
# ---------------------------------------------------------------------------

class SessionState(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    topic: str
    subject: str = "General"
    nodes: dict[str, KnowledgeNode] = Field(default_factory=dict)
    edges: list[KnowledgeEdge] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    questions_asked: list[CandidateQuestion] = Field(default_factory=list)
    turn_count: int = 0
    knowledge_leakage_events: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def concept_names(self) -> list[str]:
        return [n.concept for n in self.nodes.values()]

    def find_node_by_concept(self, concept: str) -> Optional[KnowledgeNode]:
        normalized = concept.strip().lower()
        for node in self.nodes.values():
            if node.concept.strip().lower() == normalized:
                return node
        return None