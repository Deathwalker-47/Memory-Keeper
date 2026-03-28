"""Snapshot and rollback routes."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from memory_keeper.api.schemas import SnapshotCreate
from memory_keeper.api.server import get_store
from memory_keeper.store.models import MemorySnapshot
from memory_keeper.store.sqlite_store import SQLiteStore

router = APIRouter(prefix="/sessions/{session_id}", tags=["snapshots"])


@router.post("/snapshots")
async def create_snapshot(
    session_id: str, body: SnapshotCreate, store: SQLiteStore = Depends(get_store)
):
    """Create a memory snapshot of the current session state."""
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Serialize current session state
    characters = await store.get_characters(session_id)
    facts = await store.get_facts(session_id)
    relationships = await store.get_relationships(session_id)
    events = await store.get_events(session_id)
    arcs = await store.get_narrative_arcs(session_id)
    drift_logs = await store.get_drift_logs(session_id)

    snapshot_data = {
        "session": session.model_dump(mode="json"),
        "characters": [c.model_dump(mode="json") for c in characters],
        "facts": [f.model_dump(mode="json") for f in facts],
        "relationships": [r.model_dump(mode="json") for r in relationships],
        "events": [e.model_dump(mode="json") for e in events],
        "narrative_arcs": [a.model_dump(mode="json") for a in arcs],
        "drift_logs": [d.model_dump(mode="json") for d in drift_logs],
    }

    snapshot = MemorySnapshot(
        session_id=UUID(session_id),
        snapshot_data=snapshot_data,
        created_by=body.created_by,
        notes=body.notes,
    )
    created = await store.create_snapshot(snapshot)

    # Enforce max snapshots limit
    await store.delete_oldest_snapshots(session_id, keep=10)

    return created.model_dump(mode="json")


@router.get("/snapshots")
async def list_snapshots(session_id: str, store: SQLiteStore = Depends(get_store)):
    """List all snapshots for a session."""
    snapshots = await store.list_snapshots(session_id)
    # Return without the full snapshot_data to keep response light
    return [
        {
            "snapshot_id": str(s.snapshot_id),
            "session_id": str(s.session_id),
            "timestamp": s.timestamp.isoformat() if hasattr(s.timestamp, "isoformat") else str(s.timestamp),
            "created_by": s.created_by,
            "notes": s.notes,
        }
        for s in snapshots
    ]


@router.post("/rollback/{snapshot_id}")
async def rollback_to_snapshot(
    session_id: str, snapshot_id: str, store: SQLiteStore = Depends(get_store)
):
    """Rollback session to a previous snapshot state."""
    snapshot = await store.get_snapshot(snapshot_id)
    if not snapshot or str(snapshot.session_id) != session_id:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    # The snapshot_data contains the full serialized state.
    # For now, return the snapshot data so the caller knows what state to restore.
    # Full restore requires re-importing all entities, which is a complex operation.
    return {
        "status": "rollback_ready",
        "snapshot_id": snapshot_id,
        "snapshot_data": snapshot.snapshot_data,
    }
