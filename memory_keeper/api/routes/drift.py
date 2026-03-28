"""Drift detection routes."""

from fastapi import APIRouter, Depends, HTTPException, Query

from memory_keeper.api.schemas import DriftCheckRequest
from memory_keeper.api.server import get_store
from memory_keeper.store.sqlite_store import SQLiteStore

router = APIRouter(prefix="/sessions/{session_id}/drift", tags=["drift"])


@router.post("")
async def check_drift(
    session_id: str, body: DriftCheckRequest, store: SQLiteStore = Depends(get_store)
):
    """Run drift detection for a character against a message.

    This endpoint requires the analyzer to be configured with an LLM.
    If no LLM is configured, it returns a stub response.
    """
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    character = await store.find_character_by_name(session_id, body.character_name)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Build character profile for drift detection
    facts = await store.get_facts(session_id)
    relationships = await store.get_relationships(session_id)
    drift_logs = await store.get_drift_logs(session_id, str(character.character_id))
    sig = await store.get_behavioral_signature(
        str(character.character_id), session_id
    )

    character_facts = [
        f"{f.subject} {f.predicate} {f.object}"
        for f in facts
        if f.subject.lower() == character.name.lower()
    ]

    char_rels = [
        f"{r.label} (trust: {r.trust_level})"
        for r in relationships
        if str(r.from_character) == str(character.character_id)
    ]

    profile = {
        "character_name": character.name,
        "core_traits": character.core_traits,
        "known_facts": character_facts[:10],
        "relationships": char_rels[:10],
        "previous_behavior": sig.interaction_style if sig else "No behavioral data yet.",
    }

    # Try to run drift detection via the analyzer
    try:
        from memory_keeper.analyzer.drift_detector import detect_drift
        from memory_keeper.analyzer.llm_client import LLMClient
        from memory_keeper.config import load_config

        config = load_config()
        client = LLMClient(config.llm)
        result = await detect_drift(client, body.message_content, profile)
        return result
    except Exception:
        # If LLM is not configured, return the profile for manual inspection
        return {
            "inconsistencies_detected": False,
            "severity": "none",
            "drift_items": [],
            "overall_assessment": "Drift detection requires a configured LLM. Profile returned for manual review.",
            "character_profile": profile,
        }


@router.get("")
async def get_drift_logs(
    session_id: str,
    character_id: str = Query(None),
    store: SQLiteStore = Depends(get_store),
):
    """Get drift logs for a session."""
    logs = await store.get_drift_logs(session_id, character_id)
    return [d.model_dump(mode="json") for d in logs]
