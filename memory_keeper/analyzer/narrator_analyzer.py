"""Narrator state extraction from roleplay messages."""

from typing import Optional

from memory_keeper.analyzer.llm_client import LLMClient
from memory_keeper.analyzer.prompts import load_prompt, NARRATOR_EXTRACTION


async def extract_narrator_state(
    client: LLMClient,
    message: str,
    previous_state: Optional[dict] = None,
) -> dict:
    """Extract narrator voice characteristics from a message.

    Uses the narrator_extraction.md prompt template.
    Returns dict with tense, perspective, description_density, pacing, tone.
    """
    prompt_template = load_prompt(NARRATOR_EXTRACTION)
    user_prompt = (
        prompt_template
        .replace("{message_content}", message)
        .replace("{previous_narrator_state}", str(previous_state) if previous_state else "No previous state.")
    )
    system_prompt = (
        "You are an expert at analyzing narrative voice and style in fiction. "
        "Respond with valid JSON only."
    )
    result = await client.call_json(system_prompt, user_prompt)
    return {
        "tense": result.get("tense"),
        "perspective": result.get("perspective"),
        "description_density": result.get("description_density"),
        "pacing": result.get("pacing"),
        "tone": result.get("tone"),
    }
