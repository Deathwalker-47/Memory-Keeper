"""Tests for the rollback system via API."""

import pytest
from httpx import AsyncClient, ASGITransport

from memory_keeper.config import Config
from memory_keeper.api import server as server_module
from memory_keeper.api.server import create_app
from memory_keeper.store.sqlite_store import SQLiteStore


@pytest.fixture
async def client(tmp_path):
    """Create an async test client with initialized store."""
    config = Config()
    config.database.sqlite_path = tmp_path / "test.db"
    app = create_app(config)

    store = SQLiteStore(db_path=str(config.database.sqlite_path))
    await store.initialize()
    server_module._store = store

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await store.close()
    server_module._store = None


@pytest.mark.asyncio
async def test_rollback_restores_state(client):
    """Test full rollback: create data, snapshot, add more data, rollback, verify original state."""
    # Create session
    resp = await client.post("/sessions", json={"name": "Rollback Test"})
    session_id = resp.json()["session_id"]

    # Create initial character and fact
    resp = await client.post(
        f"/sessions/{session_id}/characters",
        json={"name": "Elena", "tier": "primary", "core_traits": ["sarcastic"]},
    )
    char_id = resp.json()["character_id"]

    await client.post(
        f"/sessions/{session_id}/facts",
        json={
            "category": "world",
            "subject": "safehouse",
            "predicate": "is in",
            "object": "church",
            "confidence": 0.9,
        },
    )

    # Create snapshot of this state
    resp = await client.post(
        f"/sessions/{session_id}/snapshots",
        json={"notes": "Before changes", "created_by": "test"},
    )
    assert resp.status_code == 200
    snapshot_id = resp.json()["snapshot_id"]

    # Add more data AFTER the snapshot
    await client.post(
        f"/sessions/{session_id}/characters",
        json={"name": "Marcus", "tier": "secondary"},
    )
    await client.post(
        f"/sessions/{session_id}/facts",
        json={
            "category": "character",
            "subject": "Marcus",
            "predicate": "carries",
            "object": "a sword",
            "confidence": 0.8,
        },
    )

    # Verify we now have 2 characters and 2 facts
    resp = await client.get(f"/sessions/{session_id}/characters")
    assert len(resp.json()) == 2

    resp = await client.get(f"/sessions/{session_id}/facts")
    assert len(resp.json()) == 2

    # Rollback to the snapshot
    resp = await client.post(f"/sessions/{session_id}/rollback/{snapshot_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rollback_complete"
    assert data["restored_counts"]["characters"] == 1
    assert data["restored_counts"]["facts"] == 1
    assert "safety_snapshot_id" in data

    # Verify state is restored: only original character and fact
    resp = await client.get(f"/sessions/{session_id}/characters")
    characters = resp.json()
    assert len(characters) == 1
    assert characters[0]["name"] == "Elena"

    resp = await client.get(f"/sessions/{session_id}/facts")
    facts = resp.json()
    assert len(facts) == 1
    assert facts[0]["subject"] == "safehouse"


@pytest.mark.asyncio
async def test_rollback_creates_safety_snapshot(client):
    """Test that rollback creates a safety snapshot before restoring."""
    resp = await client.post("/sessions", json={"name": "Safety Test"})
    session_id = resp.json()["session_id"]

    # Create snapshot (empty state)
    resp = await client.post(
        f"/sessions/{session_id}/snapshots",
        json={"notes": "Initial", "created_by": "test"},
    )
    snapshot_id = resp.json()["snapshot_id"]

    # Add a character after snapshot
    await client.post(
        f"/sessions/{session_id}/characters",
        json={"name": "Elena", "tier": "primary"},
    )

    # Rollback
    resp = await client.post(f"/sessions/{session_id}/rollback/{snapshot_id}")
    assert resp.status_code == 200
    safety_id = resp.json()["safety_snapshot_id"]

    # We should have 3 snapshots: original + safety + (the original we rolled back to)
    resp = await client.get(f"/sessions/{session_id}/snapshots")
    snapshots = resp.json()
    assert len(snapshots) == 2  # original + safety

    # The safety snapshot should have the pre-rollback data
    safety_found = any(s["snapshot_id"] == safety_id for s in snapshots)
    assert safety_found


@pytest.mark.asyncio
async def test_rollback_404_bad_snapshot(client):
    """Test rollback with non-existent snapshot returns 404."""
    resp = await client.post("/sessions", json={"name": "Test"})
    session_id = resp.json()["session_id"]

    resp = await client.post(f"/sessions/{session_id}/rollback/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rollback_relationships_and_events(client):
    """Test that rollback properly restores relationships and events."""
    resp = await client.post("/sessions", json={"name": "Full Rollback"})
    session_id = resp.json()["session_id"]

    # Create two characters and a relationship
    resp1 = await client.post(
        f"/sessions/{session_id}/characters",
        json={"name": "Elena", "tier": "primary"},
    )
    resp2 = await client.post(
        f"/sessions/{session_id}/characters",
        json={"name": "Marcus", "tier": "secondary"},
    )
    c1_id = resp1.json()["character_id"]
    c2_id = resp2.json()["character_id"]

    await client.post(
        f"/sessions/{session_id}/relationships",
        json={
            "from_character": c1_id,
            "to_character": c2_id,
            "label": "allies",
            "trust_level": 0.6,
        },
    )

    # Snapshot with relationship
    resp = await client.post(
        f"/sessions/{session_id}/snapshots",
        json={"notes": "With relationship", "created_by": "test"},
    )
    snapshot_id = resp.json()["snapshot_id"]

    # Add another relationship after snapshot
    await client.post(
        f"/sessions/{session_id}/relationships",
        json={
            "from_character": c2_id,
            "to_character": c1_id,
            "label": "enemies",
            "trust_level": -0.8,
        },
    )

    # Verify 2 relationships now
    resp = await client.get(f"/sessions/{session_id}/relationships")
    assert len(resp.json()) == 2

    # Rollback
    resp = await client.post(f"/sessions/{session_id}/rollback/{snapshot_id}")
    assert resp.status_code == 200
    assert resp.json()["restored_counts"]["relationships"] == 1

    # Should be back to 1 relationship
    resp = await client.get(f"/sessions/{session_id}/relationships")
    rels = resp.json()
    assert len(rels) == 1
    assert rels[0]["label"] == "allies"
