"""Tests for configuration system including presets."""

import pytest
from pathlib import Path

from memory_keeper.config import Config, load_config, AnalyzerConfig
from memory_keeper.presets import get_preset, list_presets, MODEL_PRESETS


def test_default_config_has_new_fields():
    """Verify new config fields exist with correct defaults."""
    config = Config()
    assert config.analyzer.extract_narrator_state is True
    assert config.analyzer.extract_narrative_arcs is True
    assert config.analyzer.memory_block_max_length == 2000
    assert config.analyzer.correction_strength == "moderate"
    assert config.preset is None


def test_preset_list():
    """All expected presets are available."""
    presets = list_presets()
    assert "deepseek" in presets
    assert "gemini-flash" in presets
    assert "llama" in presets
    assert "mistral" in presets


def test_get_preset_valid():
    """get_preset returns correct dict for known preset."""
    preset = get_preset("deepseek")
    assert preset is not None
    assert preset["llm"]["temperature"] == 0.5
    assert preset["analyzer"]["correction_strength"] == "moderate"


def test_get_preset_case_insensitive():
    """get_preset handles case insensitivity."""
    assert get_preset("DeepSeek") is not None
    assert get_preset("LLAMA") is not None


def test_get_preset_unknown():
    """get_preset returns None for unknown preset."""
    assert get_preset("nonexistent") is None


def test_preset_applied_via_load_config(tmp_path):
    """Preset values are applied when loading config with preset field."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("preset: llama\n")

    config = load_config(config_file)
    assert config.llm.temperature == 0.7
    assert config.analyzer.correction_strength == "firm"
    assert config.analyzer.drift_sensitivity == "high"


def test_explicit_config_overrides_preset(tmp_path):
    """Explicit config values take precedence over preset defaults."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "preset: llama\n"
        "llm:\n"
        "  temperature: 0.3\n"
    )

    config = load_config(config_file)
    # Explicit value should win
    assert config.llm.temperature == 0.3
    # Preset values still apply for non-overridden fields
    assert config.analyzer.correction_strength == "firm"


def test_unknown_preset_ignored(tmp_path):
    """Unknown preset name doesn't crash, uses defaults."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("preset: nonexistent_model\n")

    config = load_config(config_file)
    # Should fall back to defaults
    assert config.llm.temperature == 0.7
    assert config.analyzer.correction_strength == "moderate"


def test_analyzer_config_correction_strength_values():
    """correction_strength accepts all valid values."""
    for strength in ("gentle", "moderate", "firm"):
        cfg = AnalyzerConfig(correction_strength=strength)
        assert cfg.correction_strength == strength
