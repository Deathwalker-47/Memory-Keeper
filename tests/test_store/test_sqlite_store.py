"""Tests for the SQLite store implementation."""

import pytest
from memory_keeper.store.sqlite_store import SQLiteStore
from memory_keeper.store.models import (
    Session,
    CharacterIdentity,
    CharacterTier,
    Fact,
    FactCategory,
    CharacterState,
    RelationshipDynamic,
    SpeechPatterns,
)


@pytest.fixture
async def store(tmp_path):
    """Create a temporary SQLite store for testing."""
    db_path = str(tmp_path / "test.db")
    s = SQLiteStore(db_path=db_path)
    await s.initialize()
    yield s
    await s.close()


@pytest.mark.asyncio
async def test_session_crud(store):
    """Test creating, reading, and updating sessions."""
    session = Session(name="Test Session")
    created = await store.create_session(session)
    assert created.session_id == session.session_id
    assert created.name == "Test Session"

    fetched = await store.get_session(str(session.session_id))
    assert fetched is not None
    assert fetched.name == "Test Session"

    fetched.name = "Updated Session"
    updated = await store.update_session(fetched)
    assert updated.name == "Updated Session"

    sessions = await store.list_sessions()
    assert len(sessions) == 1

    await store.delete_session(str(session.session_id))
    sessions = await store.list_sessions()
    assert len(sessions) == 0  # Soft deleted


@pytest.mark.asyncio
async def test_character_crud(store):
    """Test character creation and retrieval."""
    session = Session(name="Test")
    await store.create_session(session)

    character = CharacterIdentity(
        session_id=session.session_id,
        name="Elena Blackwood",
        tier=CharacterTier.PRIMARY,
        core_traits=["sarcastic", "guarded", "loyal"],
        speech_patterns=SpeechPatterns(
            vocabulary_level="educated",
            quirks=["uses military metaphors"],
            avoids=["contractions when angry"],
        ),
        worldview="Trust no one.",
    )
    created = await store.create_character(character)
    assert created.name == "Elena Blackwood"

    fetched = await store.get_character(str(character.character_id))
    assert fetched is not None
    assert fetched.core_traits == ["sarcastic", "guarded", "loyal"]
    assert fetched.speech_patterns.quirks == ["uses military metaphors"]

    found = await store.find_character_by_name(str(session.session_id), "elena blackwood")
    assert found is not None
    assert found.character_id == character.character_id

    characters = await store.get_characters(str(session.session_id))
    assert len(characters) == 1


@pytest.mark.asyncio
async def test_fact_crud(store):
    """Test fact creation, retrieval, and deactivation."""
    session = Session(name="Test")
    await store.create_session(session)

    fact = Fact(
        session_id=session.session_id,
        category=FactCategory.WORLD,
        subject="The safehouse",
        predicate="is located in",
        object="the abandoned church on 5th street",
        confidence=0.95,
    )
    await store.create_fact(fact)

    facts = await store.get_facts(str(session.session_id))
    assert len(facts) == 1
    assert facts[0].subject == "The safehouse"

    await store.deactivate_fact(str(fact.fact_id))
    active_facts = await store.get_facts(str(session.session_id), active_only=True)
    assert len(active_facts) == 0

    all_facts = await store.get_facts(str(session.session_id), active_only=False)
    assert len(all_facts) == 1


@pytest.mark.asyncio
async def test_relationship_crud(store):
    """Test relationship creation and retrieval."""
    session = Session(name="Test")
    await store.create_session(session)

    c1 = CharacterIdentity(session_id=session.session_id, name="Elena", tier=CharacterTier.PRIMARY)
    c2 = CharacterIdentity(session_id=session.session_id, name="Marcus", tier=CharacterTier.SECONDARY)
    await store.create_character(c1)
    await store.create_character(c2)

    rel = RelationshipDynamic(
        session_id=session.session_id,
        from_character=c1.character_id,
        to_character=c2.character_id,
        label="reluctant allies",
        trust_level=0.4,
        power_balance=-0.2,
        emotional_undercurrent="suspicion",
    )
    await store.create_relationship(rel)

    fetched = await store.get_relationship(
        str(c1.character_id), str(c2.character_id), str(session.session_id)
    )
    assert fetched is not None
    assert fetched.label == "reluctant allies"
    assert fetched.trust_level == 0.4

    all_rels = await store.get_relationships(str(session.session_id))
    assert len(all_rels) == 1


@pytest.mark.asyncio
async def test_character_state_upsert(store):
    """Test character state upsert (insert and update)."""
    session = Session(name="Test")
    await store.create_session(session)

    c = CharacterIdentity(session_id=session.session_id, name="Elena", tier=CharacterTier.PRIMARY)
    await store.create_character(c)

    state1 = CharacterState(
        character_id=c.character_id,
        session_id=session.session_id,
        mood="tense",
        location="safehouse",
    )
    await store.upsert_character_state(state1)

    fetched = await store.get_character_state(str(c.character_id), str(session.session_id))
    assert fetched.mood == "tense"

    # Update via upsert
    state1.mood = "relieved"
    await store.upsert_character_state(state1)

    fetched2 = await store.get_character_state(str(c.character_id), str(session.session_id))
    assert fetched2.mood == "relieved"
