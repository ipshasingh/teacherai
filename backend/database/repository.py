#translates between your Pydantic SessionState (what the rest of the app reasons over) and the ORM rows (how it's stored)
#translates between your clean Pydantic SessionState and these normalized rows. Everything else in the app (extractor, grounding, question generator, novice reasoning) only ever touches SessionState

"""
Repository: the ONLY bridge between the in-memory SessionState (Pydantic,
used by every agent) and the normalized SQLite tables.

Rule of thumb: agents/knowledge/* never import sqlalchemy. They read and
write SessionState objects and hand them to this repository to persist
or load. This keeps the reasoning layer fully decoupled from storage.
"""

from __future__ import annotations

from sqlalchemy.orm import Session as DBSession

from database.models import (
    ConversationMessage,
    ContradictionRow,
    KnowledgeEdgeRow,
    KnowledgeNodeRow,
    QuestionRow,
    SessionRow,
)
from schemas.knowledge import (
    CandidateQuestion,
    ClaimGroundingStatus,
    Contradiction,
    KnowledgeEdge,
    KnowledgeNode,
    NodeStatus,
    ProvenanceSource,
    QuestionCategory,
    RelationType,
    SessionState,
)


def _list_to_text(items: list[str]) -> str:
    return "\n".join(items)


def _text_to_list(text: str) -> list[str]:
    return [line for line in text.split("\n") if line.strip()]


class SessionRepository:
    def __init__(self, db: DBSession):
        self.db = db

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_session(self, topic: str, subject: str = "General") -> SessionState:
        state = SessionState(topic=topic, subject=subject or "General")
        row = SessionRow(
            session_id=state.session_id,
            topic=state.topic,
            subject=state.subject,
            turn_count=0,
            knowledge_leakage_events=0,
        )
        self.db.add(row)
        self.db.commit()
        return state

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load_session(self, session_id: str) -> SessionState | None:
        row = self.db.get(SessionRow, session_id)
        if row is None:
            return None

        nodes: dict[str, KnowledgeNode] = {}
        for n in row.nodes:
            nodes[n.id] = KnowledgeNode(
                id=n.id,
                concept=n.concept,
                description=n.description,
                attributes=_text_to_list(n.attributes),
                examples=_text_to_list(n.examples),
                constraints=_text_to_list(n.constraints),
                conditions=_text_to_list(n.conditions),
                exceptions=_text_to_list(n.exceptions),
                status=NodeStatus(n.status),
                confidence=n.confidence,
                source=ProvenanceSource(n.source),
                created_at=n.created_at,
                updated_at=n.updated_at,
                times_referenced=n.times_referenced,
                times_clarified=n.times_clarified,
            )

        edges = [
            KnowledgeEdge(
                id=e.id,
                source_node_id=e.source_node_id,
                target_node_id=e.target_node_id,
                relation_type=RelationType(e.relation_type),
                description=e.description,
                confidence=e.confidence,
                source=ProvenanceSource(e.source),
                created_at=e.created_at,
            )
            for e in row.edges
        ]

        contradictions = [
            Contradiction(
                id=c.id,
                node_a_id=c.node_a_id,
                node_b_id=c.node_b_id,
                description=c.description,
                resolved=c.resolved,
                detected_at=c.detected_at,
                resolved_at=c.resolved_at,
            )
            for c in row.contradictions
        ]

        questions = [
            CandidateQuestion(
                id=q.id,
                text=q.text,
                category=QuestionCategory(q.category),
                referenced_node_ids=[
                    x for x in q.referenced_node_ids.split(",") if x
                ],
                relevance_score=q.relevance_score,
                gap_score=q.gap_score,
                importance_score=q.importance_score,
                redundancy_penalty=q.redundancy_penalty,
                unsupported_penalty=q.unsupported_penalty,
                total_score=q.total_score,
                grounding_status=(
                    ClaimGroundingStatus(q.grounding_status)
                    if q.grounding_status
                    else None
                ),
            )
            for q in row.questions
        ]

        return SessionState(
            session_id=row.session_id,
            topic=row.topic,
            subject=row.subject,
            nodes=nodes,
            edges=edges,
            contradictions=contradictions,
            questions_asked=questions,
            turn_count=row.turn_count,
            knowledge_leakage_events=row.knowledge_leakage_events,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    # ------------------------------------------------------------------
    # Save (full sync: replace child rows to match the in-memory state)
    # ------------------------------------------------------------------

    def save_session(self, state: SessionState) -> None:
        row = self.db.get(SessionRow, state.session_id)
        if row is None:
            raise ValueError(f"Session {state.session_id} does not exist")

        row.topic = state.topic
        row.subject = state.subject
        row.turn_count = state.turn_count
        row.knowledge_leakage_events = state.knowledge_leakage_events

        # Full replace of child rows. Simple and correct for hackathon scale
        # (sessions are small — tens of nodes, not thousands). If this ever
        # becomes a bottleneck, switch to targeted upserts.
        self.db.query(KnowledgeNodeRow).filter_by(session_id=state.session_id).delete()
        self.db.query(KnowledgeEdgeRow).filter_by(session_id=state.session_id).delete()
        self.db.query(ContradictionRow).filter_by(session_id=state.session_id).delete()
        self.db.query(QuestionRow).filter_by(session_id=state.session_id).delete()

        for node in state.nodes.values():
            self.db.add(
                KnowledgeNodeRow(
                    id=node.id,
                    session_id=state.session_id,
                    concept=node.concept,
                    description=node.description,
                    attributes=_list_to_text(node.attributes),
                    examples=_list_to_text(node.examples),
                    constraints=_list_to_text(node.constraints),
                    conditions=_list_to_text(node.conditions),
                    exceptions=_list_to_text(node.exceptions),
                    status=node.status.value,
                    confidence=node.confidence,
                    source=node.source.value,
                    times_referenced=node.times_referenced,
                    times_clarified=node.times_clarified,
                    created_at=node.created_at,
                    updated_at=node.updated_at,
                )
            )

        for edge in state.edges:
            self.db.add(
                KnowledgeEdgeRow(
                    id=edge.id,
                    session_id=state.session_id,
                    source_node_id=edge.source_node_id,
                    target_node_id=edge.target_node_id,
                    relation_type=edge.relation_type.value,
                    description=edge.description,
                    confidence=edge.confidence,
                    source=edge.source.value,
                    created_at=edge.created_at,
                )
            )

        for c in state.contradictions:
            self.db.add(
                ContradictionRow(
                    id=c.id,
                    session_id=state.session_id,
                    node_a_id=c.node_a_id,
                    node_b_id=c.node_b_id,
                    description=c.description,
                    resolved=c.resolved,
                    detected_at=c.detected_at,
                    resolved_at=c.resolved_at,
                )
            )

        for q in state.questions_asked:
            self.db.add(
                QuestionRow(
                    id=q.id,
                    session_id=state.session_id,
                    text=q.text,
                    category=q.category.value,
                    referenced_node_ids=",".join(q.referenced_node_ids),
                    relevance_score=q.relevance_score,
                    gap_score=q.gap_score,
                    importance_score=q.importance_score,
                    redundancy_penalty=q.redundancy_penalty,
                    unsupported_penalty=q.unsupported_penalty,
                    total_score=q.total_score,
                    grounding_status=(
                        q.grounding_status.value if q.grounding_status else None
                    ),
                )
            )

        self.db.commit()

    def list_sessions(self) -> list[dict]:
        rows = self.db.query(SessionRow).order_by(SessionRow.created_at.desc()).all()
        return [
            {
                "session_id": r.session_id,
                "topic": r.topic,
                "subject": r.subject,
                "turn_count": r.turn_count,
                "total_concepts": len(r.nodes),
                "created_at": r.created_at,
            }
            for r in rows
        ]

    def add_message(
        self,
        session_id: str,
        role: str,
        text: str,
    ) -> None:
        message = ConversationMessage(
            session_id=session_id,
            role=role,
            text=text,
        )
        self.db.add(message)
        self.db.commit()

    def get_messages(self, session_id: str) -> list[ConversationMessage]:
        return (
            self.db.query(ConversationMessage)
            .filter(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc())
            .all()
        )