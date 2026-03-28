"""Tests for the LLM client."""

import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch

from memory_keeper.config import LLMConfig
from memory_keeper.analyzer.llm_client import LLMClient, LLMClientError


@pytest.fixture
def openai_config():
    return LLMConfig(
        provider="openai",
        model="gpt-4",
        api_key="test-key",
        temperature=0.7,
        max_tokens=2000,
    )


@pytest.fixture
def anthropic_config():
    return LLMConfig(
        provider="anthropic",
        model="claude-sonnet-4-6",
        api_key="test-key",
        temperature=0.7,
        max_tokens=2000,
    )


@pytest.fixture
def client(openai_config):
    return LLMClient(openai_config)


def _mock_openai_response(content: str) -> httpx.Response:
    """Create a mock OpenAI-style response."""
    return httpx.Response(
        status_code=200,
        json={"choices": [{"message": {"content": content}}]},
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
    )


def _mock_anthropic_response(content: str) -> httpx.Response:
    """Create a mock Anthropic-style response."""
    return httpx.Response(
        status_code=200,
        json={"content": [{"type": "text", "text": content}]},
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
    )


@pytest.mark.asyncio
async def test_call_openai(client):
    """Test basic OpenAI-compatible call."""
    mock_resp = _mock_openai_response("Hello world")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await client.call("system", "user")
        assert result == "Hello world"


@pytest.mark.asyncio
async def test_call_anthropic(anthropic_config):
    """Test Anthropic API call."""
    client = LLMClient(anthropic_config)
    mock_resp = _mock_anthropic_response("Hello from Claude")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await client.call("system", "user")
        assert result == "Hello from Claude"


@pytest.mark.asyncio
async def test_call_json_clean(client):
    """Test JSON parsing from clean response."""
    json_str = json.dumps({"key": "value", "count": 42})
    mock_resp = _mock_openai_response(json_str)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await client.call_json("system", "user")
        assert result == {"key": "value", "count": 42}


@pytest.mark.asyncio
async def test_call_json_with_markdown_fences(client):
    """Test JSON parsing from markdown-fenced response."""
    content = '```json\n{"key": "value"}\n```'
    mock_resp = _mock_openai_response(content)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await client.call_json("system", "user")
        assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_call_json_with_surrounding_text(client):
    """Test JSON parsing from response with extra text."""
    content = 'Here is the result:\n{"key": "value"}\nThat is the output.'
    mock_resp = _mock_openai_response(content)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await client.call_json("system", "user")
        assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_call_json_nested(client):
    """Test JSON parsing with nested objects."""
    data = {"outer": {"inner": [1, 2, 3]}, "flag": True}
    content = json.dumps(data)
    mock_resp = _mock_openai_response(content)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await client.call_json("system", "user")
        assert result == data


@pytest.mark.asyncio
async def test_custom_api_base():
    """Test custom API base URL for local LLMs."""
    config = LLMConfig(
        provider="local",
        model="llama-3",
        api_base="http://localhost:1234",
    )
    client = LLMClient(config)
    assert client.api_base == "http://localhost:1234"


def test_extract_json_direct():
    """Test direct JSON extraction."""
    result = LLMClient._extract_json('{"key": "value"}')
    assert result == {"key": "value"}


def test_extract_json_no_json():
    """Test JSON extraction with no JSON present."""
    with pytest.raises(ValueError):
        LLMClient._extract_json("This has no JSON at all")
