"""Memory context retrieval routes."""

from fastapi import APIRouter, Depends, HTTPException, Query

from memory_keeper.api.context_formatter import format_memory_context
from memory_keeper.api.schemas import MemoryContextResponse
from memory_keeper.api.server import get_store
from memory_keeper.store.sqlite_store import SQLiteStore

router = APIRouter(prefix="/sessions/{session_id}/memory", tags=["memory"])


@router.get("", response_model=MemoryContextResponse)
async def get_memory_context(
    session_id: str,
    character: str = Query(..., description="Character name to retrieve context for"),
    max_length: int = Query(2000, description="Max context length in characters"),
    store: SQLiteStore = Depends(get_store),
):
    """Get formatted memory context block for a character.

    This is the retrieval endpoint the adapter calls before the chat LLM responds.
    Returns a formatted text block ready for injection into the system prompt.
    """
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    char = await store.find_character_by_name(session_id, character)
    if not char:
        raise HTTPException(status_code=404, detail=f"Character '{character}' not found")

    # Gather all relevant data
    state = await store.get_character_state(str(char.character_id), session_id)
    facts = await store.get_facts(session_id)
    relationships = await store.get_relationships(session_id)
    arcs = await store.get_narrative_arcs(session_id)
    drift_logs = await store.get_drift_logs(session_id, str(char.character_id))

    # Build character name lookup
    all_chars = await store.get_characters(session_id)
    char_names = {str(c.character_id): c.name for c in all_chars}

    context = format_memory_context(
        character=char,
        state=state,
        facts=facts,
        relationships=relationships,
        arcs=arcs,
        drift_warnings=drift_logs[:5],
        character_names=char_names,
        max_length=max_length,
    )

    return MemoryContextResponse(
        context=context,
        character_name=char.name,
        facts_count=len(facts),
        relationships_count=len([
            r for r in relationships
            if str(r.from_character) == str(char.character_id)
        ]),
    )
