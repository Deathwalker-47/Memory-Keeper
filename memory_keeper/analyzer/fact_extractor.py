"""Fact extraction from roleplay messages."""

from memory_keeper.analyzer.llm_client import LLMClient
from memory_keeper.analyzer.prompts import load_prompt, FACT_EXTRACTION


async def extract_facts(
    client: LLMClient,
    message: str,
    character_name: str,
    session_name: str = "",
    context_summary: str = "",
) -> list[dict]:
    """Extract world-building and character facts from a message.

    Uses the fact_extraction.md prompt template.
    Returns list of fact dicts with subject, predicate, object, category, confidence, evidence.
    """
    prompt_template = load_prompt(FACT_EXTRACTION)
    user_prompt = (
        prompt_template
        .replace("{character_name}", character_name)
        .replace("{session_name}", session_name or "Unknown")
        .replace("{context_summary}", context_summary or "No previous context.")
        .replace("{message_content}", message)
    )
    system_prompt = (
        "You are an expert at extracting world-building facts from roleplay narratives. "
        "Respond with valid JSON only."
    )
    result = await client.call_json(system_prompt, user_prompt)
    return result.get("facts", [])
