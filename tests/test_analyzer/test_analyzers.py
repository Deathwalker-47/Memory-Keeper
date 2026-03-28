"""Tests for analyzer functions with mocked LLM responses."""

import json
import pytest
from unittest.mock import AsyncMock, patch

from memory_keeper.analyzer.character_analyzer import identify_characters, extract_character_info
from memory_keeper.analyzer.fact_extractor import extract_facts
from memory_keeper.analyzer.relationship_extractor import extract_relationships
from memory_keeper.analyzer.drift_detector import detect_drift
from memory_keeper.config import LLMConfig
from memory_keeper.analyzer.llm_client import LLMClient


@pytest.fixture
def client():
    config = LLMConfig(provider="openai", model="test", api_key="test")
    return LLMClient(config)


@pytest.mark.asyncio
async def test_identify_characters(client):
    """Test character identification from a message."""
    mock_result = {
        "characters": [
            {"name": "Elena", "tier": "primary", "action_summary": "spoke defiantly"},
            {"name": "Marcus", "tier": "secondary", "action_summary": "watched silently"},
        ]
    }
    with patch.object(client, "call_json", new_callable=AsyncMock, return_value=mock_result):
        result = await identify_characters(client, "Elena glared at Marcus.")
        assert len(result) == 2
        assert result[0]["name"] == "Elena"
        assert result[1]["tier"] == "secondary"


@pytest.mark.asyncio
async def test_extract_character_info(client):
    """Test character info extraction."""
    mock_result = {
        "character_name": "Elena",
        "core_traits": ["sarcastic", "guarded"],
        "speech_patterns": {
            "vocabulary_level": "educated",
            "quirks": ["military metaphors"],
            "favored_expressions": ["trust no one"],
        },
        "emotional_state": "tense",
        "behavioral_cues": ["crossed arms"],
        "inferred_goals": ["protect the group"],
    }
    with patch.object(client, "call_json", new_callable=AsyncMock, return_value=mock_result):
        result = await extract_character_info(client, "I trust no one here.", "Elena")
        assert result["core_traits"] == ["sarcastic", "guarded"]
        assert result["emotional_state"] == "tense"


@pytest.mark.asyncio
async def test_extract_facts(client):
    """Test fact extraction from a message."""
    mock_result = {
        "facts": [
            {
                "subject": "The safehouse",
                "predicate": "is located in",
                "object": "the abandoned church",
                "category": "world",
                "confidence": 0.95,
                "evidence": "The safehouse is in the old church on 5th.",
            }
        ]
    }
    with patch.object(client, "call_json", new_callable=AsyncMock, return_value=mock_result):
        result = await extract_facts(
            client,
            "The safehouse is in the old church on 5th.",
            "Elena",
            "Campaign 1",
        )
        assert len(result) == 1
        assert result[0]["subject"] == "The safehouse"
        assert result[0]["confidence"] == 0.95


@pytest.mark.asyncio
async def test_extract_relationships(client):
    """Test relationship extraction."""
    mock_result = {
        "relationships": [
            {
                "target_character": "Marcus",
                "label": "reluctant allies",
                "trust_level": 0.3,
                "power_balance": -0.2,
                "emotional_undercurrent": "suspicion",
                "interaction_type": "guarded conversation",
                "confidence": 0.8,
                "evidence": "She kept her distance.",
            }
        ]
    }
    with patch.object(client, "call_json", new_callable=AsyncMock, return_value=mock_result):
        result = await extract_relationships(
            client,
            "She kept her distance from Marcus.",
            "Elena",
            ["Marcus"],
        )
        assert len(result) == 1
        assert result[0]["trust_level"] == 0.3


@pytest.mark.asyncio
async def test_detect_drift_no_drift(client):
    """Test drift detection when no drift is found."""
    mock_result = {
        "inconsistencies_detected": False,
        "severity": "none",
        "drift_items": [],
        "overall_assessment": "Character behavior is consistent.",
    }
    profile = {
        "character_name": "Elena",
        "core_traits": ["sarcastic", "guarded"],
        "known_facts": [],
        "relationships": [],
        "previous_behavior": "Typically guarded and sarcastic.",
    }
    with patch.object(client, "call_json", new_callable=AsyncMock, return_value=mock_result):
        result = await detect_drift(client, "I don't trust this place.", profile)
        assert result["inconsistencies_detected"] is False
        assert result["severity"] == "none"


@pytest.mark.asyncio
async def test_detect_drift_with_drift(client):
    """Test drift detection when inconsistency is found."""
    mock_result = {
        "inconsistencies_detected": True,
        "severity": "moderate",
        "drift_items": [
            {
                "type": "trait",
                "description": "Elena is suddenly warm and trusting",
                "evidence_from_message": "Elena hugged everyone warmly",
                "confidence": 0.85,
            }
        ],
        "overall_assessment": "Character shows unexpected warmth.",
    }
    profile = {
        "character_name": "Elena",
        "core_traits": ["sarcastic", "guarded"],
        "known_facts": [],
        "relationships": [],
        "previous_behavior": "Typically guarded and sarcastic.",
    }
    with patch.object(client, "call_json", new_callable=AsyncMock, return_value=mock_result):
        result = await detect_drift(client, "Elena hugged everyone warmly.", profile)
        assert result["inconsistencies_detected"] is True
        assert result["severity"] == "moderate"
        assert len(result["drift_items"]) == 1
