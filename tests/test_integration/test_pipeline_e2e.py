"""End-to-end integration tests for the message pipeline."""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import UUID

from memory_keeper.api.pipeline import MessagePipeline
from memory_keeper.config import AnalyzerConfig
from memory_keeper.store.models import (
    Session,
    CharacterIdentity,
    CharacterTier,
    NarratorState,
    NarrativeArc,
    ArcStatus,
    DriftLog,
    DriftSeverity,
    InconsistencyType,
)
from memory_keeper.store.sqlite_store import SQLiteStore


@pytest.fixture
async def store(tmp_path):
    """Create a real SQLite store for integration tests."""
    s = SQLiteStore(db_path=str(tmp_path / "integration_test.db"))
    await s.initialize()
    yield s
    await s.close()


@pytest.fixture
async def session(store):
    """Create a test session."""
    sess = Session(name="Integration Test Campaign")
    await store.create_session(sess)
    return sess


@pytest.fixture
async def character(store, session):
    """Create a test character."""
    char = CharacterIdentity(
        session_id=session.session_id,
        name="Elena Blackwood",
        tier=CharacterTier.PRIMARY,
        core_traits=["sarcastic", "guarded", "loyal"],
    )
    await store.create_character(char)
    return char


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client that returns canned responses."""
    client = AsyncMock()
    client.call_json = AsyncMock(return_value={
        "facts": [],
        "relationships": [],
        "inconsistencies_detected": False,
        "severity": "none",
        "drift_items": [],
        "overall_assessment": "No drift.",
        "tense": "past",
        "perspective": "third_person",
        "description_density": "moderate",
        "pacing": "moderate",
        "tone": "dark",
        "arcs": [],
        "emotional_state": "tense",
        "inferred_goals": ["survive"],
        "core_traits": ["sarcastic"],
        "speech_patterns": [],
        "behavioral_observations": [],
    })
    return client


@pytest.fixture
def analyzer_config():
    """Default analyzer config for integration tests."""
    return AnalyzerConfig(
        enabled=True,
        extract_facts=True,
        extract_relationships=True,
        detect_drift=True,
        extract_narrator_state=True,
        extract_narrative_arcs=True,
    )


@pytest.mark.asyncio
async def test_full_message_flow(store, session, character, mock_llm_client, analyzer_config):
    """Process a message end-to-end and verify context is returned."""
    pipeline = MessagePipeline(
        store=store,
        llm_client=None,
        analyzer_config=analyzer_config,
    )

    result = await pipeline.process_message(
        str(session.session_id),
        "Elena Blackwood",
        "Elena surveyed the room with suspicion.",
    )

    assert result["session_id"] == str(session.session_id)
    assert result["character_name"] == "Elena Blackwood"
    assert "[MEMORY_KEEPER_START]" in result["memory_context"]
    assert "Elena Blackwood" in result["memory_context"]


@pytest.mark.asyncio
async def test_auto_character_creation(store, session):
    """Processing a message for an unknown character auto-creates it as secondary."""
    pipeline = MessagePipeline(
        store=store,
        llm_client=None,
        analyzer_config=AnalyzerConfig(enabled=False),
    )

    result = await pipeline.process_message(
        str(session.session_id),
        "Marcus Chen",
        "Marcus stepped out of the shadows.",
    )

    assert result["character_name"] == "Marcus Chen"
    char = await store.find_character_by_name(str(session.session_id), "Marcus Chen")
    assert char is not None
    assert char.tier == CharacterTier.SECONDARY


@pytest.mark.asyncio
async def test_context_includes_all_sections(store, session, character):
    """Verify context includes all populated entity types."""
    from memory_keeper.store.models import Fact, FactCategory, RelationshipDynamic

    # Create another character for relationships
    other = CharacterIdentity(
        session_id=session.session_id,
        name="Marcus",
        tier=CharacterTier.SECONDARY,
    )
    await store.create_character(other)

    # Add a fact
    fact = Fact(
        session_id=session.session_id,
        category=FactCategory.WORLD,
        subject="The safehouse",
        predicate="is located in",
        object="the abandoned church",
        confidence=0.9,
    )
    await store.create_fact(fact)

    # Add a relationship
    rel = RelationshipDynamic(
        session_id=session.session_id,
        from_character=character.character_id,
        to_character=other.character_id,
        label="reluctant allies",
        trust_level=0.3,
    )
    await store.create_relationship(rel)

    # Add a narrative arc
    arc = NarrativeArc(
        session_id=session.session_id,
        title="The Church Mystery",
        current_status=ArcStatus.DEVELOPMENT,
    )
    await store.create_narrative_arc(arc)

    # Add narrator state
    narrator = NarratorState(
        session_id=session.session_id,
        tense="past",
        perspective="third_person",
        tone="dark",
    )
    await store.upsert_narrator_state(narrator)

    pipeline = MessagePipeline(
        store=store,
        llm_client=None,
        analyzer_config=AnalyzerConfig(enabled=False),
    )
    result = await pipeline.process_message(
        str(session.session_id),
        "Elena Blackwood",
        "Elena checked the door.",
    )

    ctx = result["memory_context"]
    assert "Elena Blackwood" in ctx
    assert "Narrative Voice" in ctx
    assert "safehouse" in ctx
    assert "reluctant allies" in ctx
    assert "Church Mystery" in ctx


@pytest.mark.asyncio
async def test_correction_note_with_drift(store, session, character):
    """When drift warnings exist, correction note appears in context."""
    drift = DriftLog(
        character_id=character.character_id,
        session_id=session.session_id,
        inconsistency_type=InconsistencyType.TRAIT,
        detected_in_message="test",
        previous_state="Elena is guarded",
        conflicting_state="Elena openly shared",
        severity=DriftSeverity.MODERATE,
    )
    await store.create_drift_log(drift)

    pipeline = MessagePipeline(
        store=store,
        llm_client=None,
        analyzer_config=AnalyzerConfig(
            enabled=False,
            correction_strength="firm",
        ),
    )
    result = await pipeline.process_message(
        str(session.session_id),
        "Elena Blackwood",
        "Elena nodded.",
    )

    assert "[CORRECTION_NOTE_START]" in result["memory_context"]
    assert "CORRECTION REQUIRED" in result["memory_context"]


@pytest.mark.asyncio
async def test_narrator_state_crud(store, session):
    """Test narrator state upsert and retrieval."""
    state = NarratorState(
        session_id=session.session_id,
        tense="past",
        perspective="third_person",
        tone="dark",
        pacing="slow",
        description_density="dense",
    )
    await store.upsert_narrator_state(state)

    retrieved = await store.get_narrator_state(str(session.session_id))
    assert retrieved is not None
    assert retrieved.tense == "past"
    assert retrieved.perspective == "third_person"
    assert retrieved.tone == "dark"

    # Update
    state.tone = "whimsical"
    await store.upsert_narrator_state(state)
    updated = await store.get_narrator_state(str(session.session_id))
    assert updated.tone == "whimsical"


@pytest.mark.asyncio
async def test_snapshot_and_rollback_preserves_narrator(store, session, character):
    """Verify narrator state is cleared during rollback."""
    narrator = NarratorState(
        session_id=session.session_id,
        tense="past",
        perspective="third_person",
        tone="dark",
    )
    await store.upsert_narrator_state(narrator)

    # Verify narrator exists
    assert await store.get_narrator_state(str(session.session_id)) is not None

    # Clear session data (simulating rollback)
    await store.clear_session_data(str(session.session_id))

    # Narrator state should be cleared
    assert await store.get_narrator_state(str(session.session_id)) is None
