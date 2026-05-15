"""Narrative arc management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from memory_keeper.api.schemas import ArcCreate, ArcUpdate
from memory_keeper.api.server import get_store
from memory_keeper.store.base import BaseStore
from memory_keeper.store.models import NarrativeArc, ArcStatus

router = APIRouter(prefix="/sessions/{session_id}/arcs", tags=["arcs"])


@router.post("")
async def create_arc(
    session_id: str, body: ArcCreate, store: BaseStore = Depends(get_store)
):
    """Create a new narrative arc."""
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        status = ArcStatus(body.current_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.current_status}")

    arc = NarrativeArc(
        session_id=UUID(session_id),
        title=body.title,
        involved_characters=[UUID(c) for c in body.involved_characters],
        current_status=status,
        beats=body.beats,
        expected_outcome=body.expected_outcome,
    )
    created = await store.create_narrative_arc(arc)
    return created.model_dump(mode="json")


@router.get("")
async def list_arcs(
    session_id: str, store: BaseStore = Depends(get_store)
):
    """List all narrative arcs in a session."""
    arcs = await store.get_narrative_arcs(session_id)
    return [a.model_dump(mode="json") for a in arcs]


@router.get("/{arc_id}")
async def get_arc(
    session_id: str, arc_id: str, store: BaseStore = Depends(get_store)
):
    """Get a specific narrative arc."""
    arc = await store.get_narrative_arc(arc_id)
    if not arc or str(arc.session_id) != session_id:
        raise HTTPException(status_code=404, detail="Arc not found")
    return arc.model_dump(mode="json")


@router.put("/{arc_id}")
async def update_arc(
    session_id: str, arc_id: str, body: ArcUpdate, store: BaseStore = Depends(get_store)
):
    """Update a narrative arc."""
    arc = await store.get_narrative_arc(arc_id)
    if not arc or str(arc.session_id) != session_id:
        raise HTTPException(status_code=404, detail="Arc not found")

    if body.title is not None:
        arc.title = body.title
    if body.current_status is not None:
        try:
            arc.current_status = ArcStatus(body.current_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {body.current_status}")
    if body.beats is not None:
        arc.beats = body.beats
    if body.expected_outcome is not None:
        arc.expected_outcome = body.expected_outcome

    updated = await store.update_narrative_arc(arc)
    return updated.model_dump(mode="json")
