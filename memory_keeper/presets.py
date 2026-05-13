"""Model presets with recommended settings for tested cheap LLMs."""

MODEL_PRESETS: dict[str, dict] = {
    "deepseek": {
        "llm": {"temperature": 0.5, "max_tokens": 2000},
        "analyzer": {"correction_strength": "moderate", "drift_sensitivity": "medium"},
    },
    "gemini-flash": {
        "llm": {"temperature": 0.6, "max_tokens": 1500},
        "analyzer": {"correction_strength": "moderate", "drift_sensitivity": "medium"},
    },
    "llama": {
        "llm": {"temperature": 0.7, "max_tokens": 2000},
        "analyzer": {"correction_strength": "firm", "drift_sensitivity": "high"},
    },
    "mistral": {
        "llm": {"temperature": 0.6, "max_tokens": 2000},
        "analyzer": {"correction_strength": "moderate", "drift_sensitivity": "medium"},
    },
}


def get_preset(name: str) -> dict | None:
    """Get a model preset by name. Returns None if not found."""
    return MODEL_PRESETS.get(name.lower())


def list_presets() -> list[str]:
    """List all available preset names."""
    return list(MODEL_PRESETS.keys())
