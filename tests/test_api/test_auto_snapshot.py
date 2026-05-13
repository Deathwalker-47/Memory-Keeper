"""Tests for auto-snapshot behavior triggered through the message processing API."""

import asyncio

import pytest
from httpx import AsyncClient, ASGITransport

from memory_keeper.config import Config
from memory_keeper.api import server as server_module
from memory_keeper.api.server import create_app
from memory_keeper.store.sqlite_store import SQLiteStore


@pytest.fixture
async def client(tmp_path):
    """Create an async test client with a low auto_snapshot_interval for testing."""
    config = Config()
    config.database.sqlite_path = tmp_path / "test.db"
    config.session.auto_snapshot_interval = 3  # Low interval for testing
    app = create_app(config)

    store = SQLiteStore(db_path=str(config.database.sqlite_path))
    await store.initialize()
    server_module._store = store
    server_module._config = config

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await store.close()
    server_module._store = None
    server_module._config = None


async def _create_session_and_character(client: AsyncClient) -> str:
    """Helper: create a session and a primary character, return the session_id."""
    resp = await client.post("/sessions", json={"name": "Snapshot Test Campaign"})
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    resp = await client.post(
        f"/sessions/{session_id}/characters",
        json={"name": "Elena", "tier": "primary", "core_traits": ["sarcastic"]},
    )
    assert resp.status_code == 200
    return session_id


@pytest.mark.asyncio
async def test_auto_snapshot_triggers_at_interval(client):
    """Sending exactly `auto_snapshot_interval` messages should create one auto-snapshot."""
    session_id = await _create_session_and_character(client)

    # Send 3 messages (interval = 3), so one auto-snapshot should fire after the 3rd
    for i in range(3):
        resp = await client.post(
            f"/sessions/{session_id}/messages",
            json={
                "character_name": "Elena",
                "message_content": f"Message number {i + 1}.",
            },
        )
        assert resp.status_code == 200

    # Let background tasks complete
    await asyncio.sleep(0.5)

    resp = await client.get(f"/sessions/{session_id}/snapshots")
    assert resp.status_code == 200
    snapshots = resp.json()

    auto_snapshots = [s for s in snapshots if s["created_by"] == "auto"]
    assert len(auto_snapshots) == 1


@pytest.mark.asyncio
async def test_no_snapshot_before_interval(client):
    """Sending fewer messages than the interval should NOT create a snapshot."""
    session_id = await _create_session_and_character(client)

    # Send only 2 messages (interval = 3), no auto-snapshot expected
    for i in range(2):
        resp = await client.post(
            f"/sessions/{session_id}/messages",
            json={
                "character_name": "Elena",
                "message_content": f"Message number {i + 1}.",
            },
        )
        assert resp.status_code == 200

    # Let background tasks complete
    await asyncio.sleep(0.5)

    resp = await client.get(f"/sessions/{session_id}/snapshots")
    assert resp.status_code == 200
    snapshots = resp.json()

    assert len(snapshots) == 0


@pytest.fixture
async def client_max_snapshots(tmp_path):
    """Test client with auto_snapshot_interval=1 and max_snapshots_per_session=2."""
    config = Config()
    config.database.sqlite_path = tmp_path / "test.db"
    config.session.auto_snapshot_interval = 1
    config.session.max_snapshots_per_session = 2
    app = create_app(config)

    store = SQLiteStore(db_path=str(config.database.sqlite_path))
    await store.initialize()
    server_module._store = store
    server_module._config = config

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await store.close()
    server_module._store = None
    server_module._config = None


@pytest.mark.asyncio
async def test_auto_snapshot_respects_max(client_max_snapshots):
    """With max_snapshots_per_session=2 and interval=1, at most 2 snapshots should remain."""
    client = client_max_snapshots

    resp = await client.post("/sessions", json={"name": "Max Snapshot Test"})
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    await client.post(
        f"/sessions/{session_id}/characters",
        json={"name": "Elena", "tier": "primary", "core_traits": ["sarcastic"]},
    )

    # Send 5 messages; each triggers an auto-snapshot (interval=1),
    # but only 2 should be retained (max_snapshots_per_session=2).
    for i in range(5):
        resp = await client.post(
            f"/sessions/{session_id}/messages",
            json={
                "character_name": "Elena",
                "message_content": f"Message number {i + 1}.",
            },
        )
        assert resp.status_code == 200
        # Let each background snapshot task finish before sending the next
        await asyncio.sleep(0.5)

    resp = await client.get(f"/sessions/{session_id}/snapshots")
    assert resp.status_code == 200
    snapshots = resp.json()

    assert len(snapshots) <= 2
