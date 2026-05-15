"""Tests for narrative arc CRUD API routes."""

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
    server_module._config = config

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await store.close()
    server_module._store = None
    server_module._config = None


@pytest.mark.asyncio
async def test_arc_crud(client):
    """Test full CRUD lifecycle for narrative arcs."""
    # Create session
    resp = await client.post("/sessions", json={"name": "Test Campaign"})
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    # Create arc
    resp = await client.post(
        f"/sessions/{session_id}/arcs",
        json={
            "title": "Hero's Journey",
            "current_status": "setup",
            "beats": ["Call to adventure"],
        },
    )
    assert resp.status_code == 200
    arc_data = resp.json()
    arc_id = arc_data["arc_id"]
    assert arc_data["title"] == "Hero's Journey"
    assert arc_data["current_status"] == "setup"
    assert arc_data["beats"] == ["Call to adventure"]

    # List arcs
    resp = await client.get(f"/sessions/{session_id}/arcs")
    assert resp.status_code == 200
    arcs = resp.json()
    assert len(arcs) == 1
    assert arcs[0]["arc_id"] == arc_id

    # Get single arc
    resp = await client.get(f"/sessions/{session_id}/arcs/{arc_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Hero's Journey"

    # Update arc
    resp = await client.put(
        f"/sessions/{session_id}/arcs/{arc_id}",
        json={
            "current_status": "development",
            "beats": ["Call to adventure", "Crossing the threshold"],
        },
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["current_status"] == "development"
    assert len(updated["beats"]) == 2
    assert "Crossing the threshold" in updated["beats"]


@pytest.mark.asyncio
async def test_arc_with_characters(client):
    """Test creating an arc with involved characters."""
    # Create session
    resp = await client.post("/sessions", json={"name": "Test Campaign"})
    session_id = resp.json()["session_id"]

    # Create two characters
    resp1 = await client.post(
        f"/sessions/{session_id}/characters",
        json={"name": "Elena", "tier": "primary"},
    )
    resp2 = await client.post(
        f"/sessions/{session_id}/characters",
        json={"name": "Marcus", "tier": "secondary"},
    )
    char1_id = resp1.json()["character_id"]
    char2_id = resp2.json()["character_id"]

    # Create arc with both characters
    resp = await client.post(
        f"/sessions/{session_id}/arcs",
        json={
            "title": "Alliance Arc",
            "involved_characters": [char1_id, char2_id],
            "current_status": "setup",
            "beats": ["First meeting"],
        },
    )
    assert resp.status_code == 200
    arc_data = resp.json()
    arc_id = arc_data["arc_id"]

    # GET the arc and verify both characters are present
    resp = await client.get(f"/sessions/{session_id}/arcs/{arc_id}")
    assert resp.status_code == 200
    involved = resp.json()["involved_characters"]
    assert len(involved) == 2
    assert char1_id in involved
    assert char2_id in involved


@pytest.mark.asyncio
async def test_arc_404(client):
    """Test that requesting a non-existent arc returns 404."""
    # Create session
    resp = await client.post("/sessions", json={"name": "Test Campaign"})
    session_id = resp.json()["session_id"]

    # GET non-existent arc
    resp = await client.get(
        f"/sessions/{session_id}/arcs/00000000-0000-0000-0000-000000000000"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_arc_invalid_status(client):
    """Test that creating an arc with an invalid status returns 400."""
    # Create session
    resp = await client.post("/sessions", json={"name": "Test Campaign"})
    session_id = resp.json()["session_id"]

    # Try to create arc with invalid status
    resp = await client.post(
        f"/sessions/{session_id}/arcs",
        json={
            "title": "Bad Arc",
            "current_status": "invalid_status",
            "beats": [],
        },
    )
    assert resp.status_code == 400
    assert "Invalid status" in resp.json()["detail"]
