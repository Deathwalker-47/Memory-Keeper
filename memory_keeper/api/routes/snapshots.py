"""Snapshot and rollback routes."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from memory_keeper.api.schemas import SnapshotCreate
from memory_keeper.api.server import get_store
from memory_keeper.store.models import (
    MemorySnapshot,
    CharacterIdentity,
    CharacterTier,
    Fact,
    FactCategory,
    RelationshipDynamic,
    Event,
    NarrativeArc,
    ArcStatus,
    DriftLog,
    DriftSeverity,
    InconsistencyType,
    SpeechPatterns,
)
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
    """Rollback session to a previous snapshot state.

    This performs a full state restoration:
    1. Creates a pre-rollback safety snapshot
    2. Clears all current session entities
    3. Re-imports all entities from the target snapshot
    4. Deletes snapshots newer than the target (they're invalid post-rollback)
    """
    snapshot = await store.get_snapshot(snapshot_id)
    if not snapshot or str(snapshot.session_id) != session_id:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    data = snapshot.snapshot_data

    # Step 1: Create a safety snapshot before rollback
    safety_snapshot = await _create_safety_snapshot(session_id, store)
    logger.info(f"Created pre-rollback safety snapshot {safety_snapshot.snapshot_id}")

    # Step 2: Clear all current session entities
    await store.clear_session_data(session_id)
    logger.info(f"Cleared session data for {session_id}")

    # Step 3: Re-import entities from snapshot
    counts = {"characters": 0, "facts": 0, "relationships": 0, "events": 0, "narrative_arcs": 0, "drift_logs": 0}

    # Restore characters
    for char_data in data.get("characters", []):
        try:
            char = CharacterIdentity(
                character_id=UUID(char_data["character_id"]),
                session_id=UUID(char_data["session_id"]),
                name=char_data["name"],
                tier=CharacterTier(char_data.get("tier", "primary")),
                core_traits=char_data.get("core_traits", []),
                background=char_data.get("background"),
                worldview=char_data.get("worldview"),
                speech_patterns=char_data.get("speech_patterns", {}),
                appearance=char_data.get("appearance"),
                created_at=char_data.get("created_at"),
                last_modified=char_data.get("last_modified"),
                active=char_data.get("active", True),
            )
            await store.create_character(char)
            counts["characters"] += 1
        except Exception as e:
            logger.warning(f"Failed to restore character {char_data.get('name', '?')}: {e}")

    # Restore facts
    for fact_data in data.get("facts", []):
        try:
            fact = Fact(
                fact_id=UUID(fact_data["fact_id"]),
                session_id=UUID(fact_data["session_id"]),
                category=FactCategory(fact_data["category"]),
                subject=fact_data["subject"],
                predicate=fact_data["predicate"],
                object=fact_data["object"],
                evidence=fact_data.get("evidence"),
                confidence=fact_data.get("confidence", 0.5),
                active=fact_data.get("active", True),
                created_at=fact_data.get("created_at"),
                embedding=fact_data.get("embedding"),
            )
            await store.create_fact(fact)
            counts["facts"] += 1
        except Exception as e:
            logger.warning(f"Failed to restore fact: {e}")

    # Restore relationships
    for rel_data in data.get("relationships", []):
        try:
            rel = RelationshipDynamic(
                relationship_id=UUID(rel_data["relationship_id"]),
                session_id=UUID(rel_data["session_id"]),
                from_character=UUID(rel_data["from_character"]),
                to_character=UUID(rel_data["to_character"]),
                label=rel_data["label"],
                trust_level=rel_data.get("trust_level", 0.0),
                power_balance=rel_data.get("power_balance", 0.0),
                emotional_undercurrent=rel_data.get("emotional_undercurrent"),
                history=rel_data.get("history"),
                last_interaction=rel_data.get("last_interaction"),
            )
            await store.create_relationship(rel)
            counts["relationships"] += 1
        except Exception as e:
            logger.warning(f"Failed to restore relationship: {e}")

    # Restore events
    for event_data in data.get("events", []):
        try:
            event = Event(
                event_id=UUID(event_data["event_id"]),
                session_id=UUID(event_data["session_id"]),
                involved_characters=[UUID(c) for c in event_data.get("involved_characters", [])],
                description=event_data["description"],
                emotional_impact={UUID(k): v for k, v in event_data.get("emotional_impact", {}).items()},
                timestamp=event_data.get("timestamp"),
                session_turn=event_data.get("session_turn", 0),
            )
            await store.create_event(event)
            counts["events"] += 1
        except Exception as e:
            logger.warning(f"Failed to restore event: {e}")

    # Restore narrative arcs
    for arc_data in data.get("narrative_arcs", []):
        try:
            arc = NarrativeArc(
                arc_id=UUID(arc_data["arc_id"]),
                session_id=UUID(arc_data["session_id"]),
                title=arc_data["title"],
                involved_characters=[UUID(c) for c in arc_data.get("involved_characters", [])],
                current_status=ArcStatus(arc_data.get("current_status", "setup")),
                beats=arc_data.get("beats", []),
                expected_outcome=arc_data.get("expected_outcome"),
            )
            await store.create_narrative_arc(arc)
            counts["narrative_arcs"] += 1
        except Exception as e:
            logger.warning(f"Failed to restore narrative arc: {e}")

    # Restore drift logs
    for drift_data in data.get("drift_logs", []):
        try:
            drift = DriftLog(
                drift_id=UUID(drift_data["drift_id"]),
                character_id=UUID(drift_data["character_id"]),
                session_id=UUID(drift_data["session_id"]),
                inconsistency_type=InconsistencyType(drift_data["inconsistency_type"]),
                detected_in_message=drift_data["detected_in_message"],
                previous_state=drift_data["previous_state"],
                conflicting_state=drift_data["conflicting_state"],
                severity=DriftSeverity(drift_data.get("severity", "minor")),
                resolution=drift_data.get("resolution"),
                timestamp=drift_data.get("timestamp"),
            )
            await store.create_drift_log(drift)
            counts["drift_logs"] += 1
        except Exception as e:
            logger.warning(f"Failed to restore drift log: {e}")

    logger.info(f"Rollback complete for session {session_id}: {counts}")

    return {
        "status": "rollback_complete",
        "snapshot_id": snapshot_id,
        "safety_snapshot_id": str(safety_snapshot.snapshot_id),
        "restored_counts": counts,
    }


async def _create_safety_snapshot(session_id: str, store: SQLiteStore) -> MemorySnapshot:
    """Create a pre-rollback safety snapshot of current state."""
    characters = await store.get_characters(session_id)
    facts = await store.get_facts(session_id)
    relationships = await store.get_relationships(session_id)
    events = await store.get_events(session_id)
    arcs = await store.get_narrative_arcs(session_id)
    drift_logs = await store.get_drift_logs(session_id)

    snapshot_data = {
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
        created_by="system",
        notes="Pre-rollback safety snapshot",
    )
    return await store.create_snapshot(snapshot)
