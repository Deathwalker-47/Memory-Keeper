"""Narrative arc extraction from roleplay messages."""

from memory_keeper.analyzer.llm_client import LLMClient
from memory_keeper.analyzer.prompts import load_prompt, ARC_EXTRACTION


async def extract_narrative_arcs(
    client: LLMClient,
    message: str,
    character_name: str,
    existing_arcs: list[dict] = None,
) -> list[dict]:
    """Extract narrative arc developments from a message.

    Uses the arc_extraction.md prompt template.
    Returns list of arc dicts with title, is_new, current_status, new_beat, etc.
    """
    prompt_template = load_prompt(ARC_EXTRACTION)
    user_prompt = (
        prompt_template
        .replace("{character_name}", character_name)
        .replace("{existing_arcs}", str(existing_arcs) if existing_arcs else "No existing arcs.")
        .replace("{message_content}", message)
    )
    system_prompt = (
        "You are an expert at identifying and tracking narrative story arcs in fiction. "
        "Respond with valid JSON only."
    )
    result = await client.call_json(system_prompt, user_prompt)
    return result.get("arcs", [])
