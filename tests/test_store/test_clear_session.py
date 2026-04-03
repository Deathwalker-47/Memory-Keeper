"""Tests for session data clearing (used by rollback)."""

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
    Event,
    NarrativeArc,
    ArcStatus,
    DriftLog,
    DriftSeverity,
    InconsistencyType,
    BehavioralSignature,
)


@pytest.fixture
async def store(tmp_path):
    """Create a temporary SQLite store for testing."""
    db_path = str(tmp_path / "test.db")
    s = SQLiteStore(db_path=db_path)
    await s.initialize()
    yield s
    await s.close()


async def _populate_session(store, session):
    """Helper to populate a session with all entity types. Returns entity counts."""
    sid = session.session_id

    c1 = CharacterIdentity(session_id=sid, name="Elena", tier=CharacterTier.PRIMARY)
    c2 = CharacterIdentity(session_id=sid, name="Marcus", tier=CharacterTier.SECONDARY)
    await store.create_character(c1)
    await store.create_character(c2)

    await store.create_fact(Fact(
        session_id=sid, category=FactCategory.WORLD,
        subject="safehouse", predicate="is in", object="church", confidence=0.9,
    ))
    await store.create_fact(Fact(
        session_id=sid, category=FactCategory.CHARACTER,
        subject="Elena", predicate="carries", object="dagger", confidence=0.8,
    ))

    await store.create_relationship(RelationshipDynamic(
        session_id=sid, from_character=c1.character_id,
        to_character=c2.character_id, label="allies", trust_level=0.5,
    ))

    await store.create_event(Event(
        session_id=sid, involved_characters=[c1.character_id],
        description="Elena found the passage", session_turn=1,
    ))

    await store.create_narrative_arc(NarrativeArc(
        session_id=sid, title="The Betrayal",
        involved_characters=[c1.character_id], current_status=ArcStatus.SETUP,
    ))

    await store.create_drift_log(DriftLog(
        character_id=c1.character_id, session_id=sid,
        inconsistency_type=InconsistencyType.TRAIT,
        detected_in_message="Elena laughed warmly",
        previous_state="guarded", conflicting_state="warm",
        severity=DriftSeverity.MINOR,
    ))

    await store.upsert_character_state(CharacterState(
        character_id=c1.character_id, session_id=sid,
        mood="tense", location="safehouse",
    ))

    await store.create_behavioral_signature(BehavioralSignature(
        character_id=c1.character_id, session_id=sid,
        vocabulary_patterns=["formal"], speech_quirks=["no contractions"],
        interaction_style="guarded", confidence=0.7,
    ))

    return c1, c2


@pytest.mark.asyncio
async def test_clear_session_data(store):
    """Test that clear_session_data removes all entities but keeps the session."""
    session = Session(name="Test")
    await store.create_session(session)
    sid = str(session.session_id)

    await _populate_session(store, session)

    # Verify data exists
    assert len(await store.get_characters(sid)) == 2
    assert len(await store.get_facts(sid)) == 2
    assert len(await store.get_relationships(sid)) == 1
    assert len(await store.get_events(sid)) == 1
    assert len(await store.get_narrative_arcs(sid)) == 1
    assert len(await store.get_drift_logs(sid)) == 1

    # Clear all session data
    await store.clear_session_data(sid)

    # Verify all entity data is gone
    assert len(await store.get_characters(sid)) == 0
    assert len(await store.get_facts(sid)) == 0
    assert len(await store.get_relationships(sid)) == 0
    assert len(await store.get_events(sid)) == 0
    assert len(await store.get_narrative_arcs(sid)) == 0
    assert len(await store.get_drift_logs(sid)) == 0

    # Session itself should still exist
    fetched = await store.get_session(sid)
    assert fetched is not None
    assert fetched.name == "Test"


@pytest.mark.asyncio
async def test_clear_session_data_isolation(store):
    """Test that clearing one session doesn't affect another."""
    s1 = Session(name="Session 1")
    s2 = Session(name="Session 2")
    await store.create_session(s1)
    await store.create_session(s2)

    await _populate_session(store, s1)
    await _populate_session(store, s2)

    # Clear session 1 only
    await store.clear_session_data(str(s1.session_id))

    # Session 1 should be empty
    assert len(await store.get_characters(str(s1.session_id))) == 0
    assert len(await store.get_facts(str(s1.session_id))) == 0

    # Session 2 should be untouched
    assert len(await store.get_characters(str(s2.session_id))) == 2
    assert len(await store.get_facts(str(s2.session_id))) == 2
    assert len(await store.get_relationships(str(s2.session_id))) == 1
