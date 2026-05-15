"""Tests for narrator drift detection with mocked LLM responses."""

import pytest
from unittest.mock import AsyncMock, patch

from memory_keeper.analyzer.narrator_drift_detector import detect_narrator_drift
from memory_keeper.config import LLMConfig
from memory_keeper.analyzer.llm_client import LLMClient


@pytest.fixture
def client():
    config = LLMConfig(provider="openai", model="test", api_key="test")
    return LLMClient(config)


@pytest.mark.asyncio
async def test_detect_narrator_drift_no_drift(client):
    """Test narrator drift detection when no drift is found."""
    mock_result = {
        "drift_detected": False,
        "severity": "none",
        "drift_items": [],
        "overall_assessment": "Consistent.",
    }
    established_state = {
        "tense": "past",
        "perspective": "third person limited",
        "description_density": "moderate",
        "pacing": "steady",
        "tone": "somber",
    }
    with patch.object(client, "call_json", new_callable=AsyncMock, return_value=mock_result):
        result = await detect_narrator_drift(
            client,
            "The rain hammered the old roof as she waited in silence.",
            established_state,
        )
        assert result["drift_detected"] is False
        assert result["severity"] == "none"
        assert result["drift_items"] == []
        assert result["overall_assessment"] == "Consistent."


@pytest.mark.asyncio
async def test_detect_narrator_drift_with_shift(client):
    """Test narrator drift detection when a tense shift is found."""
    mock_result = {
        "drift_detected": True,
        "severity": "moderate",
        "drift_items": [
            {
                "dimension": "tense",
                "previous_value": "past",
                "current_value": "present",
                "description": "Narration switches from past tense to present tense.",
                "confidence": 0.9,
            }
        ],
        "overall_assessment": "Tense drift detected mid-paragraph.",
    }
    established_state = {
        "tense": "past",
        "perspective": "third person limited",
        "description_density": "moderate",
        "pacing": "steady",
        "tone": "somber",
    }
    with patch.object(client, "call_json", new_callable=AsyncMock, return_value=mock_result):
        result = await detect_narrator_drift(
            client,
            "She walks into the room and looks around.",
            established_state,
        )
        assert result["drift_detected"] is True
        assert result["severity"] == "moderate"
        assert len(result["drift_items"]) == 1
        item = result["drift_items"][0]
        assert item["dimension"] == "tense"
        assert item["previous_value"] == "past"
        assert item["current_value"] == "present"
        assert item["confidence"] == 0.9


@pytest.mark.asyncio
async def test_detect_narrator_drift_handles_none_state(client):
    """Test that None values in established_state are substituted with 'not established'."""
    mock_result = {
        "drift_detected": False,
        "severity": "none",
        "drift_items": [],
        "overall_assessment": "No established baseline to compare.",
    }
    established_state = {
        "tense": None,
        "perspective": "first person",
        "description_density": None,
        "pacing": None,
        "tone": "warm",
    }

    captured_prompts = {}

    async def capture_call_json(system_prompt, user_prompt):
        captured_prompts["system"] = system_prompt
        captured_prompts["user"] = user_prompt
        return mock_result

    with patch.object(client, "call_json", new=capture_call_json):
        result = await detect_narrator_drift(
            client,
            "I stepped forward cautiously.",
            established_state,
        )
        # Should not crash
        assert result["drift_detected"] is False

        # Verify the prompt substituted "not established" for None values
        user_prompt = captured_prompts["user"]
        assert "not established" in user_prompt
        # The non-None values should appear as-is
        assert "first person" in user_prompt
        assert "warm" in user_prompt
