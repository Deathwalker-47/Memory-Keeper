"""Session management routes."""

from fastapi import APIRouter, Depends, HTTPException

from memory_keeper.api.schemas import SessionCreate, SessionUpdate
from memory_keeper.api.server import get_store
from memory_keeper.store.models import Session
from memory_keeper.store.sqlite_store import SQLiteStore

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("")
async def create_session(body: SessionCreate, store: SQLiteStore = Depends(get_store)):
    """Create a new session."""
    session = Session(name=body.name, config=body.config)
    created = await store.create_session(session)
    return created.model_dump(mode="json")


@router.get("")
async def list_sessions(store: SQLiteStore = Depends(get_store)):
    """List all active sessions."""
    sessions = await store.list_sessions()
    return [s.model_dump(mode="json") for s in sessions]


@router.get("/{session_id}")
async def get_session(session_id: str, store: SQLiteStore = Depends(get_store)):
    """Get a session by ID."""
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.model_dump(mode="json")


@router.put("/{session_id}")
async def update_session(
    session_id: str, body: SessionUpdate, store: SQLiteStore = Depends(get_store)
):
    """Update a session."""
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if body.name is not None:
        session.name = body.name
    if body.config is not None:
        session.config = body.config
    updated = await store.update_session(session)
    return updated.model_dump(mode="json")


@router.delete("/{session_id}")
async def delete_session(session_id: str, store: SQLiteStore = Depends(get_store)):
    """Soft delete (archive) a session."""
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await store.delete_session(session_id)
    return {"status": "archived", "session_id": session_id}
