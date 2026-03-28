"""Tests for API routes using FastAPI TestClient."""

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

    # Manually initialize the store (lifespan doesn't run with ASGITransport)
    store = SQLiteStore(db_path=str(config.database.sqlite_path))
    await store.initialize()
    server_module._store = store

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await store.close()
    server_module._store = None


@pytest.mark.asyncio
async def test_health(client):
    """Test health check endpoint."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_session_crud(client):
    """Test session CRUD via API."""
    # Create
    resp = await client.post("/sessions", json={"name": "Test Campaign"})
    assert resp.status_code == 200
    data = resp.json()
    session_id = data["session_id"]
    assert data["name"] == "Test Campaign"

    # List
    resp = await client.get("/sessions")
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) == 1

    # Get
    resp = await client.get(f"/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Campaign"

    # Update
    resp = await client.put(f"/sessions/{session_id}", json={"name": "Updated Campaign"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Campaign"

    # Delete (archive)
    resp = await client.delete(f"/sessions/{session_id}")
    assert resp.status_code == 200

    # List should be empty now
    resp = await client.get("/sessions")
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_character_crud(client):
    """Test character CRUD via API."""
    # Create session first
    resp = await client.post("/sessions", json={"name": "Test"})
    session_id = resp.json()["session_id"]

    # Create character
    resp = await client.post(
        f"/sessions/{session_id}/characters",
        json={
            "name": "Elena Blackwood",
            "tier": "primary",
            "core_traits": ["sarcastic", "guarded"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    char_id = data["character_id"]
    assert data["name"] == "Elena Blackwood"

    # List characters
    resp = await client.get(f"/sessions/{session_id}/characters")
    assert len(resp.json()) == 1

    # Get character
    resp = await client.get(f"/sessions/{session_id}/characters/{char_id}")
    assert resp.status_code == 200

    # Update character
    resp = await client.put(
        f"/sessions/{session_id}/characters/{char_id}",
        json={"core_traits": ["sarcastic", "guarded", "loyal"]},
    )
    assert resp.status_code == 200
    assert "loyal" in resp.json()["core_traits"]


@pytest.mark.asyncio
async def test_fact_crud(client):
    """Test fact CRUD via API."""
    resp = await client.post("/sessions", json={"name": "Test"})
    session_id = resp.json()["session_id"]

    # Create fact
    resp = await client.post(
        f"/sessions/{session_id}/facts",
        json={
            "category": "world",
            "subject": "The safehouse",
            "predicate": "is located in",
            "object": "the abandoned church",
            "confidence": 0.95,
        },
    )
    assert resp.status_code == 200

    # List facts
    resp = await client.get(f"/sessions/{session_id}/facts")
    facts = resp.json()
    assert len(facts) == 1
    fact_id = facts[0]["fact_id"]

    # Deactivate fact
    resp = await client.delete(f"/sessions/{session_id}/facts/{fact_id}")
    assert resp.status_code == 200

    # Active facts should be empty
    resp = await client.get(f"/sessions/{session_id}/facts?active_only=true")
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_relationship_crud(client):
    """Test relationship CRUD via API."""
    resp = await client.post("/sessions", json={"name": "Test"})
    session_id = resp.json()["session_id"]

    # Create characters
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

    # Create relationship
    resp = await client.post(
        f"/sessions/{session_id}/relationships",
        json={
            "from_character": char1_id,
            "to_character": char2_id,
            "label": "reluctant allies",
            "trust_level": 0.4,
        },
    )
    assert resp.status_code == 200

    # List relationships
    resp = await client.get(f"/sessions/{session_id}/relationships")
    assert len(resp.json()) == 1

    # Get specific relationship
    resp = await client.get(f"/sessions/{session_id}/relationships/{char1_id}/{char2_id}")
    assert resp.status_code == 200
    assert resp.json()["label"] == "reluctant allies"


@pytest.mark.asyncio
async def test_snapshot_crud(client):
    """Test snapshot creation and listing."""
    resp = await client.post("/sessions", json={"name": "Test"})
    session_id = resp.json()["session_id"]

    # Create snapshot
    resp = await client.post(
        f"/sessions/{session_id}/snapshots",
        json={"notes": "Before big battle", "created_by": "user"},
    )
    assert resp.status_code == 200

    # List snapshots
    resp = await client.get(f"/sessions/{session_id}/snapshots")
    snapshots = resp.json()
    assert len(snapshots) == 1
    assert snapshots[0]["notes"] == "Before big battle"


@pytest.mark.asyncio
async def test_memory_context(client):
    """Test memory context retrieval."""
    resp = await client.post("/sessions", json={"name": "Test"})
    session_id = resp.json()["session_id"]

    # Create character
    await client.post(
        f"/sessions/{session_id}/characters",
        json={
            "name": "Elena",
            "tier": "primary",
            "core_traits": ["sarcastic", "guarded"],
        },
    )

    # Create a fact
    await client.post(
        f"/sessions/{session_id}/facts",
        json={
            "category": "world",
            "subject": "The safehouse",
            "predicate": "is in",
            "object": "the church",
            "confidence": 0.9,
        },
    )

    # Get memory context
    resp = await client.get(
        f"/sessions/{session_id}/memory", params={"character": "Elena"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Elena" in data["context"]
    assert "MEMORY_KEEPER_START" in data["context"]
    assert data["facts_count"] == 1


@pytest.mark.asyncio
async def test_message_processing(client):
    """Test the main message processing endpoint."""
    resp = await client.post("/sessions", json={"name": "Test Campaign"})
    session_id = resp.json()["session_id"]

    # Create character
    await client.post(
        f"/sessions/{session_id}/characters",
        json={"name": "Elena", "tier": "primary", "core_traits": ["sarcastic"]},
    )

    # Process a message (LLM won't be configured, so extraction will be skipped)
    resp = await client.post(
        f"/sessions/{session_id}/messages",
        json={
            "character_name": "Elena",
            "message_content": "I trust no one in this place.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["character_name"] == "Elena"
    assert "MEMORY_KEEPER_START" in data["memory_context"]


@pytest.mark.asyncio
async def test_message_auto_creates_character(client):
    """Test that processing a message for an unknown character auto-creates it."""
    resp = await client.post("/sessions", json={"name": "Test"})
    session_id = resp.json()["session_id"]

    # Process message for non-existent character
    resp = await client.post(
        f"/sessions/{session_id}/messages",
        json={
            "character_name": "NewCharacter",
            "message_content": "Hello world.",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["character_name"] == "NewCharacter"

    # Character should now exist
    resp = await client.get(f"/sessions/{session_id}/characters")
    chars = resp.json()
    assert len(chars) == 1
    assert chars[0]["name"] == "NewCharacter"
    assert chars[0]["tier"] == "secondary"  # Auto-created as secondary


@pytest.mark.asyncio
async def test_404_handling(client):
    """Test 404 responses for missing resources."""
    resp = await client.get("/sessions/nonexistent-id")
    assert resp.status_code == 404

    resp = await client.get("/sessions/nonexistent-id/characters")
    # This returns empty list, not 404
    # but get specific character should 404
    resp = await client.get("/sessions/nonexistent-id/characters/bad-id")
    assert resp.status_code == 404
