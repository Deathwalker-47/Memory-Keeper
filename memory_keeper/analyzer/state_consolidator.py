"""State consolidation — merges redundant facts and resolves conflicts."""

import json
from typing import Optional

from loguru import logger

from memory_keeper.analyzer.llm_client import LLMClient
from memory_keeper.analyzer.prompts import load_prompt, STATE_CONSOLIDATION


async def consolidate_facts(
    client: LLMClient,
    facts: list[dict],
    character_name: str = "",
    session_name: str = "",
) -> dict:
    """Analyze facts for redundancy, conflicts, and superseded information.

    Args:
        client: LLM client for analysis.
        facts: List of fact dicts (must include fact_id, subject, predicate, object, confidence).
        character_name: Focus character (or empty for all).
        session_name: Session name for context.

    Returns:
        Dict with redundant_groups, conflicts, and superseded lists.
    """
    if len(facts) < 2:
        return {"redundant_groups": [], "conflicts": [], "superseded": []}

    prompt_template = load_prompt(STATE_CONSOLIDATION)
    facts_json = json.dumps(facts, indent=2, default=str)

    user_prompt = (
        prompt_template
        .replace("{character_name}", character_name or "All characters")
        .replace("{session_name}", session_name or "Unknown")
        .replace("{facts_json}", facts_json)
    )

    system_prompt = (
        "You are an expert at analyzing knowledge bases for redundancy and conflicts. "
        "Respond with valid JSON only."
    )

    try:
        result = await client.call_json(system_prompt, user_prompt)
        return {
            "redundant_groups": result.get("redundant_groups", []),
            "conflicts": result.get("conflicts", []),
            "superseded": result.get("superseded", []),
        }
    except Exception as e:
        logger.warning(f"State consolidation failed: {e}")
        return {"redundant_groups": [], "conflicts": [], "superseded": []}


async def apply_consolidation(
    store,
    session_id: str,
    consolidation_result: dict,
    auto_apply: bool = False,
) -> dict:
    """Apply consolidation results by deactivating redundant/superseded/conflicting facts.

    Args:
        store: SQLiteStore instance.
        session_id: Session to consolidate.
        consolidation_result: Output from consolidate_facts().
        auto_apply: If True, automatically deactivate facts. If False, return plan only.

    Returns:
        Dict with counts of actions taken/planned.
    """
    to_deactivate = set()

    for group in consolidation_result.get("redundant_groups", []):
        for fid in group.get("deactivate_fact_ids", []):
            to_deactivate.add(fid)

    for conflict in consolidation_result.get("conflicts", []):
        fid = conflict.get("recommended_deactivate")
        if fid:
            to_deactivate.add(fid)

    for sup in consolidation_result.get("superseded", []):
        fid = sup.get("old_fact_id")
        if fid:
            to_deactivate.add(fid)

    if auto_apply:
        for fact_id in to_deactivate:
            try:
                await store.deactivate_fact(fact_id)
            except Exception as e:
                logger.warning(f"Failed to deactivate fact {fact_id}: {e}")

    return {
        "facts_to_deactivate": len(to_deactivate),
        "applied": auto_apply,
        "deactivated_ids": list(to_deactivate),
    }
