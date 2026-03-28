"""Drift detection for character inconsistencies."""

from memory_keeper.analyzer.llm_client import LLMClient
from memory_keeper.analyzer.prompts import load_prompt, DRIFT_DETECTION


async def detect_drift(
    client: LLMClient,
    message: str,
    character_profile: dict,
) -> dict:
    """Detect character inconsistencies against an established profile.

    Uses the drift_detection.md prompt template.

    Args:
        client: LLM client instance.
        message: The message to analyze for drift.
        character_profile: Dict with keys: character_name, core_traits,
            known_facts, relationships, previous_behavior.

    Returns:
        Dict with inconsistencies_detected, severity, drift_items, overall_assessment.
    """
    prompt_template = load_prompt(DRIFT_DETECTION)
    user_prompt = (
        prompt_template
        .replace("{character_name}", character_profile.get("character_name", "Unknown"))
        .replace("{core_traits}", str(character_profile.get("core_traits", [])))
        .replace("{known_facts}", str(character_profile.get("known_facts", [])))
        .replace("{relationships}", str(character_profile.get("relationships", [])))
        .replace("{previous_behavior}", character_profile.get("previous_behavior", "No data"))
        .replace("{message_content}", message)
    )
    system_prompt = (
        "You are an expert at detecting character inconsistencies in roleplay. "
        "Respond with valid JSON only."
    )
    result = await client.call_json(system_prompt, user_prompt)

    # Ensure expected structure
    return {
        "inconsistencies_detected": result.get("inconsistencies_detected", False),
        "severity": result.get("severity", "none"),
        "drift_items": result.get("drift_items", []),
        "overall_assessment": result.get("overall_assessment", "No drift detected."),
    }
