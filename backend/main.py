"""
FastAPI entry point. Wires together: database, repository, LLM client,
and the novice reasoning orchestrator.

Endpoints:
  POST /sessions              -> create a new (empty) teaching session
  GET  /sessions               -> list all sessions
  GET  /sessions/{id}          -> get current state summary
  POST /sessions/{id}/turns    -> teach the AI one explanation, get its
                                   reflection + next question back
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from agents.novice import process_turn
from database.database import get_db, init_db
from database.repository import SessionRepository
from database.models import ConversationMessage
from knowledge.state import SessionSummary, summarize
from llm.client import LLMClient
from schemas.knowledge import CandidateQuestion

_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Feyn AI API", lifespan=lifespan)

# Adjust origins once you know your frontend dev server port (Vite default
# shown here). Wide open for hackathon convenience; tighten for anything
# beyond a local demo.
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "https://feynn-ai-lpcm.onrender.com",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    topic: str
    subject: str = "General"


class SessionResponse(BaseModel):
    session_id: str
    topic: str
    subject: str
    summary: SessionSummary

class MessageResponse(BaseModel):
    id: int
    role: str
    text: str
    created_at: str


class SessionDetailResponse(BaseModel):
    session_id: str
    topic: str
    summary: SessionSummary
    messages: list[MessageResponse]

class TeachRequest(BaseModel):
    text: str


class TeachResponse(BaseModel):
    reflection: str
    question: CandidateQuestion | None
    summary: SessionSummary


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/sessions", response_model=SessionResponse)
def create_session(req: CreateSessionRequest, db: DBSession = Depends(get_db)):
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="topic must not be empty")
    repo = SessionRepository(db)
    state = repo.create_session(topic=req.topic.strip(), subject=req.subject.strip() or "General")
    return SessionResponse(
        session_id=state.session_id, topic=state.topic, subject=state.subject, summary=summarize(state)
    )

@app.get("/sessions")
def list_sessions(db: DBSession = Depends(get_db)):
    return SessionRepository(db).list_sessions()


@app.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, db: DBSession = Depends(get_db)):
    state = SessionRepository(db).load_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(
        session_id=state.session_id, topic=state.topic, subject=state.subject, summary=summarize(state)
    )

@app.post("/sessions/{session_id}/turns", response_model=TeachResponse)
def teach(
    session_id: str,
    req: TeachRequest,
    db: DBSession = Depends(get_db),
    client: LLMClient = Depends(get_llm_client),
):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")

    repo = SessionRepository(db)
    state = repo.load_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")

    user_text = req.text.strip()

    result = process_turn(client, state, user_text)

    repo.add_message(
        session_id=session_id,
        role="user",
        text=user_text,
    )

    repo.add_message(
        session_id=session_id,
        role="assistant",
        text=result.reflection,
    )

    if result.question is not None:
        repo.add_message(
            session_id=session_id,
            role="assistant",
            text=result.question.text,
        )

    repo.save_session(state)

    return TeachResponse(
        reflection=result.reflection,
        question=result.question,
        summary=result.summary,
    )