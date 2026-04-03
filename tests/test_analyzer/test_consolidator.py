"""Tests for state consolidation analyzer."""

import json
import pytest
from unittest.mock import AsyncMock, patch

from memory_keeper.analyzer.state_consolidator import consolidate_facts, apply_consolidation


@pytest.mark.asyncio
async def test_consolidate_facts_finds_redundancy():
    """Test that consolidation detects redundant facts."""
    mock_client = AsyncMock()
    mock_client.call_json.return_value = {
        "redundant_groups": [
            {
                "keep_fact_id": "fact-1",
                "deactivate_fact_ids": ["fact-2"],
                "reason": "Both describe the safehouse location",
            }
        ],
        "conflicts": [],
        "superseded": [],
    }

    facts = [
        {"fact_id": "fact-1", "subject": "safehouse", "predicate": "is in", "object": "the church", "confidence": 0.9},
        {"fact_id": "fact-2", "subject": "safehouse", "predicate": "located at", "object": "the old church", "confidence": 0.7},
    ]

    result = await consolidate_facts(mock_client, facts, "Elena", "Test Session")

    assert len(result["redundant_groups"]) == 1
    assert result["redundant_groups"][0]["keep_fact_id"] == "fact-1"
    assert "fact-2" in result["redundant_groups"][0]["deactivate_fact_ids"]
    mock_client.call_json.assert_called_once()


@pytest.mark.asyncio
async def test_consolidate_facts_finds_conflicts():
    """Test that consolidation detects conflicting facts."""
    mock_client = AsyncMock()
    mock_client.call_json.return_value = {
        "redundant_groups": [],
        "conflicts": [
            {
                "fact_ids": ["fact-1", "fact-2"],
                "description": "Elena's eye color contradicts",
                "recommended_keep": "fact-2",
                "recommended_deactivate": "fact-1",
                "reason": "fact-2 has higher confidence",
            }
        ],
        "superseded": [],
    }

    facts = [
        {"fact_id": "fact-1", "subject": "Elena", "predicate": "has", "object": "blue eyes", "confidence": 0.5},
        {"fact_id": "fact-2", "subject": "Elena", "predicate": "has", "object": "green eyes", "confidence": 0.9},
    ]

    result = await consolidate_facts(mock_client, facts, "Elena", "Test")

    assert len(result["conflicts"]) == 1
    assert result["conflicts"][0]["recommended_deactivate"] == "fact-1"


@pytest.mark.asyncio
async def test_consolidate_too_few_facts():
    """Test that consolidation skips when fewer than 2 facts."""
    mock_client = AsyncMock()
    result = await consolidate_facts(mock_client, [{"fact_id": "1"}])
    assert result == {"redundant_groups": [], "conflicts": [], "superseded": []}
    mock_client.call_json.assert_not_called()


@pytest.mark.asyncio
async def test_apply_consolidation_collects_deactivations():
    """Test that apply_consolidation collects all fact IDs to deactivate."""
    consolidation_result = {
        "redundant_groups": [
            {"keep_fact_id": "f1", "deactivate_fact_ids": ["f2", "f3"]},
        ],
        "conflicts": [
            {"recommended_deactivate": "f4"},
        ],
        "superseded": [
            {"old_fact_id": "f5", "new_fact_id": "f1"},
        ],
    }

    mock_store = AsyncMock()
    result = await apply_consolidation(mock_store, "session-1", consolidation_result, auto_apply=False)

    assert result["facts_to_deactivate"] == 4  # f2, f3, f4, f5
    assert result["applied"] is False
    mock_store.deactivate_fact.assert_not_called()


@pytest.mark.asyncio
async def test_apply_consolidation_auto_apply():
    """Test that auto_apply actually deactivates facts."""
    consolidation_result = {
        "redundant_groups": [
            {"keep_fact_id": "f1", "deactivate_fact_ids": ["f2"]},
        ],
        "conflicts": [],
        "superseded": [],
    }

    mock_store = AsyncMock()
    result = await apply_consolidation(mock_store, "session-1", consolidation_result, auto_apply=True)

    assert result["applied"] is True
    assert result["facts_to_deactivate"] == 1
    mock_store.deactivate_fact.assert_called_once_with("f2")
