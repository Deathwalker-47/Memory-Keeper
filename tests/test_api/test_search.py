"""Tests for semantic search API route."""

from unittest.mock import patch, MagicMock
from uuid import uuid4

import pytest
from httpx import AsyncClient, ASGITransport

from memory_keeper.config import Config
from memory_keeper.api import server as server_module
from memory_keeper.api.server import create_app
from memory_keeper.store.sqlite_store import SQLiteStore
from memory_keeper.store.models import Fact, FactCategory


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


@pytest.fixture
async def client_and_store(tmp_path):
    """Create an async test client with initialized store, yielding both."""
    config = Config()
    config.database.sqlite_path = tmp_path / "test.db"
    app = create_app(config)

    store = SQLiteStore(db_path=str(config.database.sqlite_path))
    await store.initialize()
    server_module._store = store
    server_module._config = config

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, store

    await store.close()
    server_module._store = None
    server_module._config = None


@pytest.mark.asyncio
async def test_search_no_embeddings_disabled(tmp_path):
    """Test that search returns 400 when embeddings are disabled."""
    config = Config()
    config.database.sqlite_path = tmp_path / "test.db"
    config.database.enable_embeddings = False
    app = create_app(config)

    store = SQLiteStore(db_path=str(config.database.sqlite_path))
    await store.initialize()
    server_module._store = store
    server_module._config = config

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create a session first
        resp = await ac.post("/sessions", json={"name": "Test"})
        session_id = resp.json()["session_id"]

        # Attempt search with embeddings disabled
        resp = await ac.post(
            f"/sessions/{session_id}/search",
            json={"query": "test"},
        )
        assert resp.status_code == 400
        assert "disabled" in resp.json()["detail"].lower()

    await store.close()
    server_module._store = None
    server_module._config = None


@pytest.mark.asyncio
async def test_search_no_session_404(client):
    """Test that searching in a non-existent session returns 404."""
    resp = await client.post(
        "/sessions/nonexistent/search",
        json={"query": "test"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search_with_mock_embeddings(client_and_store):
    """Test semantic search with mocked embedding generation."""
    client, store = client_and_store

    # Create a session
    resp = await client.post("/sessions", json={"name": "Test Campaign"})
    session_id = resp.json()["session_id"]

    # Insert a fact with an embedding directly via the store
    embedding_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
    fact = Fact(
        session_id=session_id,
        category=FactCategory.WORLD,
        subject="The safehouse",
        predicate="is located in",
        object="the abandoned church",
        confidence=0.95,
        embedding=embedding_vector,
    )
    await store.create_fact(fact)

    # Mock generate_embedding to return a known vector similar to the fact's
    mock_query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

    with patch(
        "memory_keeper.analyzer.embeddings.generate_embedding",
        return_value=mock_query_embedding,
    ), patch(
        "memory_keeper.analyzer.embeddings.compute_similarity",
        return_value=0.99,
    ):
        resp = await client.post(
            f"/sessions/{session_id}/search",
            json={"query": "where is the safehouse"},
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 1

        # Verify the result contains our fact
        result = results[0]
        assert result["subject"] == "The safehouse"
        assert result["predicate"] == "is located in"
        assert result["object"] == "the abandoned church"
        assert result["similarity"] == pytest.approx(0.99)
        assert result["confidence"] == pytest.approx(0.95)
