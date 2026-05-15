"""Drift detection for narrator style inconsistencies."""

from memory_keeper.analyzer.llm_client import LLMClient
from memory_keeper.analyzer.prompts import load_prompt, NARRATOR_DRIFT_DETECTION


async def detect_narrator_drift(
    client: LLMClient,
    message: str,
    established_state: dict,
) -> dict:
    """Detect narrator style drift against an established narrator state.

    Uses the narrator_drift_detection.md prompt template.

    Args:
        client: LLM client instance.
        message: The message to analyze for narrator drift.
        established_state: Dict with keys: tense, perspective,
            description_density, pacing, tone.

    Returns:
        Dict with drift_detected, severity, drift_items, overall_assessment.
    """
    prompt_template = load_prompt(NARRATOR_DRIFT_DETECTION)
    user_prompt = (
        prompt_template
        .replace("{established_tense}", established_state.get("tense") or "not established")
        .replace("{established_perspective}", established_state.get("perspective") or "not established")
        .replace("{established_density}", established_state.get("description_density") or "not established")
        .replace("{established_pacing}", established_state.get("pacing") or "not established")
        .replace("{established_tone}", established_state.get("tone") or "not established")
        .replace("{message_content}", message)
    )
    system_prompt = (
        "You are an expert at detecting narrator style inconsistencies in fiction. "
        "Respond with valid JSON only."
    )
    result = await client.call_json(system_prompt, user_prompt)

    # Ensure expected structure
    return {
        "drift_detected": result.get("drift_detected", False),
        "severity": result.get("severity", "none"),
        "drift_items": result.get("drift_items", []),
        "overall_assessment": result.get("overall_assessment", "No drift detected."),
    }
