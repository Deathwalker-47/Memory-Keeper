"""Analyzer prompt templates."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent

# Prompt file paths
CHARACTER_EXTRACTION = PROMPTS_DIR / "character_extraction.md"
DRIFT_DETECTION = PROMPTS_DIR / "drift_detection.md"
FACT_EXTRACTION = PROMPTS_DIR / "fact_extraction.md"
RELATIONSHIP_EXTRACTION = PROMPTS_DIR / "relationship_extraction.md"


def load_prompt(path: Path) -> str:
    """Load a prompt template from file."""
    return path.read_text()
