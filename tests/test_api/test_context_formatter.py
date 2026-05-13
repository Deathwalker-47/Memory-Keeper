"""Tests for the context formatter including narrator and correction prompts."""

import pytest
from uuid import uuid4

from memory_keeper.api.context_formatter import format_memory_context, _build_correction_note
from memory_keeper.store.models import (
    CharacterIdentity,
    CharacterState,
    NarratorState,
    Fact,
    FactCategory,
    RelationshipDynamic,
    NarrativeArc,
    ArcStatus,
    DriftLog,
    DriftSeverity,
    InconsistencyType,
)


@pytest.fixture
def session_id():
    return uuid4()


@pytest.fixture
def character(session_id):
    return CharacterIdentity(
        session_id=session_id,
        name="Elena Blackwood",
        core_traits=["sarcastic", "guarded"],
        worldview="Trust no one",
    )


@pytest.fixture
def drift_warning(session_id):
    return DriftLog(
        character_id=uuid4(),
        session_id=session_id,
        inconsistency_type=InconsistencyType.TRAIT,
        detected_in_message="test message",
        previous_state="Elena is guarded and distrustful",
        conflicting_state="Elena openly shared her feelings",
        severity=DriftSeverity.MODERATE,
    )


def test_basic_context_output(character):
    """Basic context includes character identity."""
    result = format_memory_context(
        character=character,
        state=None,
        facts=[],
        relationships=[],
        arcs=[],
        drift_warnings=[],
    )
    assert "[MEMORY_KEEPER_START]" in result
    assert "[MEMORY_KEEPER_END]" in result
    assert "Elena Blackwood" in result
    assert "sarcastic" in result


def test_narrator_state_included(character, session_id):
    """Narrator state appears in context when provided."""
    narrator = NarratorState(
        session_id=session_id,
        tense="past",
        perspective="third_person",
        tone="dark",
        pacing="slow",
        description_density="dense",
    )
    result = format_memory_context(
        character=character,
        state=None,
        facts=[],
        relationships=[],
        arcs=[],
        drift_warnings=[],
        narrator_state=narrator,
    )
    assert "Narrative Voice" in result
    assert "Tense: past" in result
    assert "Perspective: third_person" in result
    assert "Tone: dark" in result


def test_narrator_state_omitted_when_none(character):
    """No narrator section when narrator_state is None."""
    result = format_memory_context(
        character=character,
        state=None,
        facts=[],
        relationships=[],
        arcs=[],
        drift_warnings=[],
        narrator_state=None,
    )
    assert "Narrative Voice" not in result


def test_correction_note_gentle(drift_warning, character):
    """Gentle correction uses 'Gentle reminder' language."""
    result = format_memory_context(
        character=character,
        state=None,
        facts=[],
        relationships=[],
        arcs=[],
        drift_warnings=[drift_warning],
        correction_strength="gentle",
    )
    assert "[CORRECTION_NOTE_START]" in result
    assert "Gentle reminder" in result
    assert "[CORRECTION_NOTE_END]" in result


def test_correction_note_moderate(drift_warning, character):
    """Moderate correction uses 'Correction needed' language."""
    result = format_memory_context(
        character=character,
        state=None,
        facts=[],
        relationships=[],
        arcs=[],
        drift_warnings=[drift_warning],
        correction_strength="moderate",
    )
    assert "Correction needed" in result
    assert "IMPORTANT:" in result


def test_correction_note_firm(drift_warning, character):
    """Firm correction uses 'CORRECTION REQUIRED' language."""
    result = format_memory_context(
        character=character,
        state=None,
        facts=[],
        relationships=[],
        arcs=[],
        drift_warnings=[drift_warning],
        correction_strength="firm",
    )
    assert "CORRECTION REQUIRED" in result
    assert "CRITICAL:" in result


def test_no_correction_note_without_drift(character):
    """No correction note when no drift warnings exist."""
    result = format_memory_context(
        character=character,
        state=None,
        facts=[],
        relationships=[],
        arcs=[],
        drift_warnings=[],
        correction_strength="firm",
    )
    assert "[CORRECTION_NOTE_START]" not in result


def test_max_length_respected(character, session_id):
    """Context output respects max_length budget."""
    facts = [
        Fact(
            session_id=session_id,
            category=FactCategory.WORLD,
            subject=f"Subject {i}",
            predicate="is",
            object=f"Object {i}" * 20,
            confidence=0.9,
        )
        for i in range(50)
    ]
    result = format_memory_context(
        character=character,
        state=None,
        facts=facts,
        relationships=[],
        arcs=[],
        drift_warnings=[],
        max_length=500,
    )
    body = result.split("[MEMORY_KEEPER_START]")[1].split("[MEMORY_KEEPER_END]")[0]
    assert len(body) <= 600  # some slack for section headers


def test_drift_prefix_varies_by_strength(drift_warning, character):
    """Drift warning lines use different prefixes per strength."""
    for strength, expected in [("gentle", "Note:"), ("moderate", "IMPORTANT:"), ("firm", "CRITICAL:")]:
        result = format_memory_context(
            character=character,
            state=None,
            facts=[],
            relationships=[],
            arcs=[],
            drift_warnings=[drift_warning],
            correction_strength=strength,
        )
        assert expected in result


def test_build_correction_note_empty_warnings():
    """_build_correction_note returns empty string for no warnings."""
    assert _build_correction_note([], "Test", "moderate") == ""
