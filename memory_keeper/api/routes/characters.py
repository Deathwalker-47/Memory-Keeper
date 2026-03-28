"""Character management routes."""

from fastapi import APIRouter, Depends, HTTPException

from memory_keeper.api.schemas import CharacterCreate, CharacterUpdate
from memory_keeper.api.server import get_store
from memory_keeper.store.models import CharacterIdentity, CharacterTier, SpeechPatterns
from memory_keeper.store.sqlite_store import SQLiteStore

router = APIRouter(prefix="/sessions/{session_id}/characters", tags=["characters"])


@router.post("")
async def create_character(
    session_id: str, body: CharacterCreate, store: SQLiteStore = Depends(get_store)
):
    """Create a new character in a session."""
    from uuid import UUID

    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    character = CharacterIdentity(
        session_id=UUID(session_id),
        name=body.name,
        tier=CharacterTier(body.tier),
        core_traits=body.core_traits,
        background=body.background,
        worldview=body.worldview,
        speech_patterns=SpeechPatterns(**body.speech_patterns.model_dump()),
        appearance=body.appearance,
    )
    created = await store.create_character(character)
    return created.model_dump(mode="json")


@router.get("")
async def list_characters(session_id: str, store: SQLiteStore = Depends(get_store)):
    """List all active characters in a session."""
    characters = await store.get_characters(session_id)
    return [c.model_dump(mode="json") for c in characters]


@router.get("/{character_id}")
async def get_character(
    session_id: str, character_id: str, store: SQLiteStore = Depends(get_store)
):
    """Get a character by ID."""
    character = await store.get_character(character_id)
    if not character or str(character.session_id) != session_id:
        raise HTTPException(status_code=404, detail="Character not found")
    return character.model_dump(mode="json")


@router.put("/{character_id}")
async def update_character(
    session_id: str,
    character_id: str,
    body: CharacterUpdate,
    store: SQLiteStore = Depends(get_store),
):
    """Update a character."""
    character = await store.get_character(character_id)
    if not character or str(character.session_id) != session_id:
        raise HTTPException(status_code=404, detail="Character not found")

    if body.name is not None:
        character.name = body.name
    if body.tier is not None:
        character.tier = CharacterTier(body.tier)
    if body.core_traits is not None:
        character.core_traits = body.core_traits
    if body.background is not None:
        character.background = body.background
    if body.worldview is not None:
        character.worldview = body.worldview
    if body.appearance is not None:
        character.appearance = body.appearance

    updated = await store.update_character(character)
    return updated.model_dump(mode="json")
