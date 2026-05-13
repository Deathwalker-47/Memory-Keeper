"""Tests for the PostgreSQL store implementation.

Requires a running PostgreSQL instance. Set the TEST_POSTGRES_URL
environment variable to enable these tests, e.g.:
    export TEST_POSTGRES_URL="postgresql://user:pass@localhost:5432/test_db"
"""

import os
import pytest

from memory_keeper.store.models import (
    Session,
    CharacterIdentity,
    CharacterTier,
    NarratorState,
    DriftLog,
    DriftSeverity,
    InconsistencyType,
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not os.environ.get("TEST_POSTGRES_URL"),
        reason="TEST_POSTGRES_URL not set",
    ),
]


@pytest.fixture
async def store():
    from memory_keeper.store.postgres_store import PostgresStore

    url = os.environ["TEST_POSTGRES_URL"]
    s = PostgresStore(dsn=url)
    await s.initialize()
    yield s
    # Clean up all test data
    async with s.pool.acquire() as conn:
        for table in [
            "drift_logs",
            "memory_snapshots",
            "behavioral_signatures",
            "character_states",
            "narrator_states",
            "events",
            "narrative_arcs",
            "relationships",
            "facts",
            "characters",
            "sessions",
        ]:
            await conn.execute(f"DELETE FROM {table}")
    await s.close()


async def test_pg_session_crud(store):
    """Test create, get, list, update, and delete for sessions."""
    session = Session(name="PG Test Session")
    created = await store.create_session(session)
    assert created.name == "PG Test Session"
    assert created.session_id == session.session_id

    # Get
    fetched = await store.get_session(str(session.session_id))
    assert fetched is not None
    assert fetched.name == "PG Test Session"

    # List (should include the session since it is not archived)
    sessions = await store.list_sessions()
    ids = [s.session_id for s in sessions]
    assert session.session_id in ids

    # Update
    fetched.name = "Updated PG Session"
    updated = await store.update_session(fetched)
    assert updated.name == "Updated PG Session"
    re_fetched = await store.get_session(str(session.session_id))
    assert re_fetched.name == "Updated PG Session"

    # Delete (soft delete — sets archived=True)
    await store.delete_session(str(session.session_id))
    after_delete = await store.list_sessions()
    ids_after = [s.session_id for s in after_delete]
    assert session.session_id not in ids_after


async def test_pg_character_crud(store):
    """Test create, get, list, and find-by-name for characters."""
    session = Session(name="Char Session")
    await store.create_session(session)

    character = CharacterIdentity(
        session_id=session.session_id,
        name="Elena",
        tier=CharacterTier.PRIMARY,
        core_traits=["brave", "sarcastic"],
    )
    created = await store.create_character(character)
    assert created.name == "Elena"

    # Get by ID
    fetched = await store.get_character(str(character.character_id))
    assert fetched is not None
    assert fetched.name == "Elena"
    assert fetched.core_traits == ["brave", "sarcastic"]

    # List characters in session
    chars = await store.get_characters(str(session.session_id))
    assert len(chars) == 1
    assert chars[0].character_id == character.character_id

    # Find by name (case-insensitive)
    found = await store.find_character_by_name(str(session.session_id), "elena")
    assert found is not None
    assert found.character_id == character.character_id


async def test_pg_narrator_state_upsert(store):
    """Test upsert semantics: insert then update, only one row per session."""
    session = Session(name="Narrator Session")
    await store.create_session(session)
    sid = str(session.session_id)

    state1 = NarratorState(
        session_id=session.session_id,
        tense="past",
        perspective="third person limited",
        description_density="moderate",
        pacing="steady",
        tone="somber",
    )
    await store.upsert_narrator_state(state1)

    fetched = await store.get_narrator_state(sid)
    assert fetched is not None
    assert fetched.tense == "past"
    assert fetched.tone == "somber"

    # Upsert again with changed values
    state2 = NarratorState(
        session_id=session.session_id,
        tense="present",
        perspective="first person",
        description_density="lush",
        pacing="rapid",
        tone="whimsical",
    )
    await store.upsert_narrator_state(state2)

    fetched2 = await store.get_narrator_state(sid)
    assert fetched2 is not None
    assert fetched2.tense == "present"
    assert fetched2.tone == "whimsical"

    # Verify only one row exists (upsert, not duplicate insert)
    async with store.pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM narrator_states WHERE session_id = $1", sid
        )
    assert count == 1


async def test_pg_increment_message_count(store):
    """Test that increment_message_count increases the count correctly."""
    session = Session(name="Counter Session")
    await store.create_session(session)
    sid = str(session.session_id)

    # Initial count should be 0
    fetched = await store.get_session(sid)
    assert fetched.message_count == 0

    # Increment twice
    count1 = await store.increment_message_count(sid)
    assert count1 == 1

    count2 = await store.increment_message_count(sid)
    assert count2 == 2

    # Verify via get_session
    fetched2 = await store.get_session(sid)
    assert fetched2.message_count == 2


async def test_pg_drift_log_nullable_character(store):
    """Test creating a drift log with character_id=None (narrator-level drift)."""
    session = Session(name="Drift Session")
    await store.create_session(session)

    drift = DriftLog(
        character_id=None,
        session_id=session.session_id,
        inconsistency_type=InconsistencyType.NARRATOR,
        detected_in_message="The tone shifted abruptly.",
        previous_state="somber",
        conflicting_state="whimsical",
        severity=DriftSeverity.MODERATE,
    )
    created = await store.create_drift_log(drift)
    assert created.character_id is None

    # Retrieve and verify
    logs = await store.get_drift_logs(str(session.session_id))
    assert len(logs) == 1
    log = logs[0]
    assert log.character_id is None
    assert log.inconsistency_type == InconsistencyType.NARRATOR
    assert log.severity == DriftSeverity.MODERATE
    assert log.previous_state == "somber"
    assert log.conflicting_state == "whimsical"
    assert log.drift_id == drift.drift_id
