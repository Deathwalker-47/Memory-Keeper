"""Character identification and extraction from messages."""

from memory_keeper.analyzer.llm_client import LLMClient
from memory_keeper.analyzer.prompts import load_prompt, CHARACTER_EXTRACTION


async def identify_characters(client: LLMClient, message: str) -> list[dict]:
    """Identify all characters present in a message with inferred tiers.

    Returns a list of dicts with 'name' and 'tier' keys.
    """
    system_prompt = (
        "You are an expert at identifying characters in roleplay narratives. "
        "Identify every character who speaks, acts, or is meaningfully referenced "
        "in the provided message. For each, infer their importance tier.\n\n"
        "Return a JSON object:\n"
        '{"characters": [\n'
        '  {"name": "string", "tier": "primary|secondary|tertiary|npc", '
        '"action_summary": "brief description of what they did/said"}\n'
        "]}\n\n"
        "Rules:\n"
        "- Primary: main character driving the scene\n"
        "- Secondary: significant NPCs with recurring presence\n"
        "- Tertiary: minor characters with brief appearances\n"
        "- NPC: background characters mentioned but not active"
    )
    result = await client.call_json(system_prompt, f"Message:\n{message}")
    return result.get("characters", [])


async def extract_character_info(
    client: LLMClient, message: str, character_name: str
) -> dict:
    """Extract character traits and patterns from a message.

    Uses the character_extraction.md prompt template.
    Returns parsed dict with core_traits, speech_patterns, emotional_state, etc.
    """
    prompt_template = load_prompt(CHARACTER_EXTRACTION)
    user_prompt = (
        prompt_template
        .replace("{character_name}", character_name)
        .replace("{message_content}", message)
    )
    system_prompt = (
        "You are an expert character analyst for roleplay narratives. "
        "Respond with valid JSON only."
    )
    return await client.call_json(system_prompt, user_prompt)
