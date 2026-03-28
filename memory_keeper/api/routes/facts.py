"""Fact management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from memory_keeper.api.schemas import FactCreate
from memory_keeper.api.server import get_store
from memory_keeper.store.models import Fact, FactCategory
from memory_keeper.store.sqlite_store import SQLiteStore

router = APIRouter(prefix="/sessions/{session_id}/facts", tags=["facts"])


@router.post("")
async def create_fact(
    session_id: str, body: FactCreate, store: SQLiteStore = Depends(get_store)
):
    """Create a new fact."""
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    fact = Fact(
        session_id=UUID(session_id),
        category=FactCategory(body.category),
        subject=body.subject,
        predicate=body.predicate,
        object=body.object,
        evidence=body.evidence,
        confidence=body.confidence,
    )
    created = await store.create_fact(fact)
    return created.model_dump(mode="json")


@router.get("")
async def list_facts(
    session_id: str,
    active_only: bool = Query(True),
    store: SQLiteStore = Depends(get_store),
):
    """List facts for a session."""
    facts = await store.get_facts(session_id, active_only=active_only)
    return [f.model_dump(mode="json") for f in facts]


@router.delete("/{fact_id}")
async def deactivate_fact(
    session_id: str, fact_id: str, store: SQLiteStore = Depends(get_store)
):
    """Deactivate a fact."""
    await store.deactivate_fact(fact_id)
    return {"status": "deactivated", "fact_id": fact_id}
