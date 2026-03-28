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
    Event,
    NarrativeArc,
    ArcStatus,
    DriftLog,
    DriftSeverity,
    InconsistencyType,
    BehavioralSignature,
    MemorySnapshot,
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


@pytest.mark.asyncio
async def test_update_character(store):
    """Test updating a character."""
    session = Session(name="Test")
    await store.create_session(session)

    c = CharacterIdentity(
        session_id=session.session_id,
        name="Elena",
        tier=CharacterTier.PRIMARY,
        core_traits=["sarcastic"],
    )
    await store.create_character(c)

    c.core_traits = ["sarcastic", "loyal"]
    c.background = "Former military operative"
    updated = await store.update_character(c)
    assert updated.core_traits == ["sarcastic", "loyal"]

    fetched = await store.get_character(str(c.character_id))
    assert fetched.core_traits == ["sarcastic", "loyal"]
    assert fetched.background == "Former military operative"


@pytest.mark.asyncio
async def test_event_crud(store):
    """Test event creation and retrieval."""
    session = Session(name="Test")
    await store.create_session(session)

    c1 = CharacterIdentity(session_id=session.session_id, name="Elena", tier=CharacterTier.PRIMARY)
    await store.create_character(c1)

    event = Event(
        session_id=session.session_id,
        involved_characters=[c1.character_id],
        description="Elena discovered the hidden passage",
        emotional_impact={c1.character_id: "surprised"},
        session_turn=5,
    )
    created = await store.create_event(event)
    assert created.description == "Elena discovered the hidden passage"

    fetched = await store.get_event(str(event.event_id))
    assert fetched is not None
    assert fetched.session_turn == 5
    assert c1.character_id in fetched.involved_characters

    events = await store.get_events(str(session.session_id))
    assert len(events) == 1


@pytest.mark.asyncio
async def test_narrative_arc_crud(store):
    """Test narrative arc creation, retrieval, and update."""
    session = Session(name="Test")
    await store.create_session(session)

    c1 = CharacterIdentity(session_id=session.session_id, name="Elena", tier=CharacterTier.PRIMARY)
    await store.create_character(c1)

    arc = NarrativeArc(
        session_id=session.session_id,
        title="The Betrayal",
        involved_characters=[c1.character_id],
        current_status=ArcStatus.SETUP,
        beats=["Discovery of betrayal"],
        expected_outcome="Confrontation",
    )
    created = await store.create_narrative_arc(arc)
    assert created.title == "The Betrayal"

    arcs = await store.get_narrative_arcs(str(session.session_id))
    assert len(arcs) == 1
    assert arcs[0].current_status == ArcStatus.SETUP

    arc.current_status = ArcStatus.DEVELOPMENT
    arc.beats.append("Gathering evidence")
    await store.update_narrative_arc(arc)

    arcs = await store.get_narrative_arcs(str(session.session_id))
    assert arcs[0].current_status == ArcStatus.DEVELOPMENT
    assert len(arcs[0].beats) == 2


@pytest.mark.asyncio
async def test_drift_log_crud(store):
    """Test drift log creation and retrieval."""
    session = Session(name="Test")
    await store.create_session(session)

    c1 = CharacterIdentity(session_id=session.session_id, name="Elena", tier=CharacterTier.PRIMARY)
    await store.create_character(c1)

    drift = DriftLog(
        character_id=c1.character_id,
        session_id=session.session_id,
        inconsistency_type=InconsistencyType.TRAIT,
        detected_in_message="Elena laughed warmly and hugged everyone",
        previous_state="guarded and sarcastic",
        conflicting_state="suddenly warm and open",
        severity=DriftSeverity.MODERATE,
    )
    created = await store.create_drift_log(drift)
    assert created.severity == DriftSeverity.MODERATE

    logs = await store.get_drift_logs(str(session.session_id))
    assert len(logs) == 1

    logs_filtered = await store.get_drift_logs(
        str(session.session_id), str(c1.character_id)
    )
    assert len(logs_filtered) == 1
    assert logs_filtered[0].inconsistency_type == InconsistencyType.TRAIT


@pytest.mark.asyncio
async def test_behavioral_signature_crud(store):
    """Test behavioral signature creation, retrieval, and update."""
    session = Session(name="Test")
    await store.create_session(session)

    c1 = CharacterIdentity(session_id=session.session_id, name="Elena", tier=CharacterTier.PRIMARY)
    await store.create_character(c1)

    sig = BehavioralSignature(
        character_id=c1.character_id,
        session_id=session.session_id,
        vocabulary_patterns=["military jargon", "formal speech"],
        speech_quirks=["never uses contractions when angry"],
        emotional_ranges={"anger": ["cold silence", "clipped words"]},
        interaction_style="guarded, professional",
        confidence=0.8,
    )
    created = await store.create_behavioral_signature(sig)
    assert created.confidence == 0.8

    fetched = await store.get_behavioral_signature(
        str(c1.character_id), str(session.session_id)
    )
    assert fetched is not None
    assert fetched.vocabulary_patterns == ["military jargon", "formal speech"]

    sig.confidence = 0.9
    sig.speech_quirks.append("uses metaphors")
    await store.update_behavioral_signature(sig)

    fetched2 = await store.get_behavioral_signature(
        str(c1.character_id), str(session.session_id)
    )
    assert fetched2.confidence == 0.9
    assert len(fetched2.speech_quirks) == 2


@pytest.mark.asyncio
async def test_snapshot_crud(store):
    """Test snapshot creation, retrieval, listing, and cleanup."""
    session = Session(name="Test")
    await store.create_session(session)

    snapshot = MemorySnapshot(
        session_id=session.session_id,
        snapshot_data={"characters": [], "facts": [], "test": True},
        created_by="user",
        notes="Test snapshot",
    )
    created = await store.create_snapshot(snapshot)
    assert created.notes == "Test snapshot"

    fetched = await store.get_snapshot(str(snapshot.snapshot_id))
    assert fetched is not None
    assert fetched.snapshot_data["test"] is True

    snapshots = await store.list_snapshots(str(session.session_id))
    assert len(snapshots) == 1

    # Test cleanup - create 3 snapshots and keep only 2
    s2 = MemorySnapshot(
        session_id=session.session_id,
        snapshot_data={"n": 2},
    )
    s3 = MemorySnapshot(
        session_id=session.session_id,
        snapshot_data={"n": 3},
    )
    await store.create_snapshot(s2)
    await store.create_snapshot(s3)

    await store.delete_oldest_snapshots(str(session.session_id), keep=2)
    remaining = await store.list_snapshots(str(session.session_id))
    assert len(remaining) == 2


@pytest.mark.asyncio
async def test_search_facts_by_embedding(store):
    """Test semantic search over fact embeddings."""
    session = Session(name="Test")
    await store.create_session(session)

    # Create facts with simple embeddings for testing
    f1 = Fact(
        session_id=session.session_id,
        category=FactCategory.WORLD,
        subject="safehouse",
        predicate="is in",
        object="abandoned church",
        confidence=0.9,
        embedding=[1.0, 0.0, 0.0],
    )
    f2 = Fact(
        session_id=session.session_id,
        category=FactCategory.CHARACTER,
        subject="Elena",
        predicate="carries",
        object="a silver dagger",
        confidence=0.85,
        embedding=[0.0, 1.0, 0.0],
    )
    f3 = Fact(
        session_id=session.session_id,
        category=FactCategory.WORLD,
        subject="church",
        predicate="has",
        object="hidden basement",
        confidence=0.7,
        embedding=[0.9, 0.1, 0.0],  # Similar to f1
    )
    await store.create_fact(f1)
    await store.create_fact(f2)
    await store.create_fact(f3)

    # Search with embedding similar to f1
    results = await store.search_facts_by_embedding(
        str(session.session_id), [1.0, 0.0, 0.0], limit=2
    )
    assert len(results) == 2
    assert results[0].subject == "safehouse"  # Most similar
    assert results[1].subject == "church"  # Second most similar
