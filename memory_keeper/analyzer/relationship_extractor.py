"""Relationship extraction from roleplay messages."""

from memory_keeper.analyzer.llm_client import LLMClient
from memory_keeper.analyzer.prompts import load_prompt, RELATIONSHIP_EXTRACTION


async def extract_relationships(
    client: LLMClient,
    message: str,
    character_name: str,
    other_characters: list[str] = None,
    existing_relationships: list[dict] = None,
) -> list[dict]:
    """Extract relationship dynamics from a message.

    Uses the relationship_extraction.md prompt template.
    Returns list of relationship dicts with target_character, label, trust_level, etc.
    """
    prompt_template = load_prompt(RELATIONSHIP_EXTRACTION)
    user_prompt = (
        prompt_template
        .replace("{character_name}", character_name)
        .replace("{other_characters}", ", ".join(other_characters) if other_characters else "None known")
        .replace("{existing_relationships}", str(existing_relationships) if existing_relationships else "None established")
        .replace("{message_content}", message)
    )
    system_prompt = (
        "You are an expert at detecting and analyzing character relationships. "
        "Respond with valid JSON only."
    )
    result = await client.call_json(system_prompt, user_prompt)
    return result.get("relationships", [])
