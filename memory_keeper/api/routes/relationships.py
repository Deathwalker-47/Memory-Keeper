"""Relationship management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from memory_keeper.api.schemas import RelationshipCreate
from memory_keeper.api.server import get_store
from memory_keeper.store.models import RelationshipDynamic
from memory_keeper.store.sqlite_store import SQLiteStore

router = APIRouter(prefix="/sessions/{session_id}/relationships", tags=["relationships"])


@router.post("")
async def create_relationship(
    session_id: str, body: RelationshipCreate, store: SQLiteStore = Depends(get_store)
):
    """Create a new relationship between characters."""
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    rel = RelationshipDynamic(
        session_id=UUID(session_id),
        from_character=UUID(body.from_character),
        to_character=UUID(body.to_character),
        label=body.label,
        trust_level=body.trust_level,
        power_balance=body.power_balance,
        emotional_undercurrent=body.emotional_undercurrent,
        history=body.history,
    )
    created = await store.create_relationship(rel)
    return created.model_dump(mode="json")


@router.get("")
async def list_relationships(session_id: str, store: SQLiteStore = Depends(get_store)):
    """List all relationships in a session."""
    rels = await store.get_relationships(session_id)
    return [r.model_dump(mode="json") for r in rels]


@router.get("/{from_char}/{to_char}")
async def get_relationship(
    session_id: str, from_char: str, to_char: str, store: SQLiteStore = Depends(get_store)
):
    """Get a specific relationship between two characters."""
    rel = await store.get_relationship(from_char, to_char, session_id)
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return rel.model_dump(mode="json")
