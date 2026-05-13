"""Format memory context for injection into chat prompts."""

from typing import List, Optional

from memory_keeper.store.models import (
    CharacterIdentity,
    CharacterState,
    NarratorState,
    Fact,
    RelationshipDynamic,
    NarrativeArc,
    DriftLog,
)


_DRIFT_PREFIX = {
    "gentle": "Note:",
    "moderate": "IMPORTANT:",
    "firm": "CRITICAL:",
}

_CORRECTION_TEMPLATES = {
    "gentle": (
        "Gentle reminder: {name} has been showing some inconsistency. "
        "Please keep the following in mind:\n{items}"
    ),
    "moderate": (
        "Correction needed: {name} should maintain consistency with "
        "their established character. Address the following:\n{items}"
    ),
    "firm": (
        "CORRECTION REQUIRED: {name} MUST adhere to established "
        "characterization. The following inconsistencies must be fixed:\n{items}"
    ),
}


def _build_correction_note(
    drift_warnings: List[DriftLog],
    character_name: str,
    strength: str,
) -> str:
    """Build a correction note block when drift warnings exist."""
    if not drift_warnings:
        return ""

    template = _CORRECTION_TEMPLATES.get(strength, _CORRECTION_TEMPLATES["moderate"])
    prefix = _DRIFT_PREFIX.get(strength, "IMPORTANT:")

    items = ""
    for d in drift_warnings[:3]:
        items += f"- {prefix} {d.previous_state} — but observed: {d.conflicting_state}\n"

    note = template.format(name=character_name, items=items)
    return f"\n[CORRECTION_NOTE_START]\n{note}[CORRECTION_NOTE_END]"


def format_memory_context(
    character: CharacterIdentity,
    state: Optional[CharacterState],
    facts: List[Fact],
    relationships: List[RelationshipDynamic],
    arcs: List[NarrativeArc],
    drift_warnings: List[DriftLog],
    character_names: dict = None,
    max_length: int = 2000,
    narrator_state: Optional[NarratorState] = None,
    correction_strength: str = "moderate",
) -> str:
    """Build the namespaced memory block for prompt injection.

    Prioritizes: identity > narrator > state > relationships > facts > arcs > drift warnings.
    Respects max_length budget (approximate character count).
    Appends a correction note when drift warnings are present.
    """
    char_names = character_names or {}
    sections = []
    budget = max_length

    # Section 1: Character Identity (highest priority)
    identity = f"## Character: {character.name}\n"
    if character.core_traits:
        identity += f"Traits: {', '.join(character.core_traits)}\n"
    if character.worldview:
        identity += f"Worldview: {character.worldview}\n"
    if character.speech_patterns and character.speech_patterns.quirks:
        identity += f"Speech quirks: {', '.join(character.speech_patterns.quirks)}\n"
    sections.append(identity)
    budget -= len(identity)

    # Section 2: Narrative Voice
    if narrator_state and budget > 100:
        voice_parts = []
        if narrator_state.tense:
            voice_parts.append(f"Tense: {narrator_state.tense}")
        if narrator_state.perspective:
            voice_parts.append(f"Perspective: {narrator_state.perspective}")
        if narrator_state.tone:
            voice_parts.append(f"Tone: {narrator_state.tone}")
        if narrator_state.pacing:
            voice_parts.append(f"Pacing: {narrator_state.pacing}")
        if narrator_state.description_density:
            voice_parts.append(f"Detail: {narrator_state.description_density}")
        if voice_parts:
            voice_text = "## Narrative Voice\n" + " | ".join(voice_parts) + "\n"
            sections.append(voice_text)
            budget -= len(voice_text)

    # Section 3: Current State
    if state and budget > 100:
        state_parts = []
        if state.mood:
            state_parts.append(f"Mood: {state.mood}")
        if state.location:
            state_parts.append(f"Location: {state.location}")
        if state.current_goal:
            state_parts.append(f"Goal: {state.current_goal}")
        if state_parts:
            state_text = "Current state: " + " | ".join(state_parts) + "\n"
            sections.append(state_text)
            budget -= len(state_text)

    # Section 4: Relationships
    char_rels = [
        r for r in relationships
        if str(r.from_character) == str(character.character_id)
    ]
    if char_rels and budget > 100:
        rel_text = "## Relationships\n"
        for r in char_rels:
            target = char_names.get(str(r.to_character), str(r.to_character)[:8])
            line = f"- {target}: {r.label} (trust: {r.trust_level:.1f})"
            if r.emotional_undercurrent:
                line += f" [{r.emotional_undercurrent}]"
            line += "\n"
            if budget - len(rel_text) - len(line) < 50:
                break
            rel_text += line
        sections.append(rel_text)
        budget -= len(rel_text)

    # Section 5: Key Facts
    if facts and budget > 100:
        fact_text = "## Key Facts\n"
        for f in sorted(facts, key=lambda x: x.confidence, reverse=True):
            line = f"- {f.subject} {f.predicate} {f.object}\n"
            if budget - len(fact_text) - len(line) < 50:
                break
            fact_text += line
        sections.append(fact_text)
        budget -= len(fact_text)

    # Section 6: Active Story Threads
    active_arcs = [a for a in arcs if a.current_status.value not in ("closed", "resolution")]
    if active_arcs and budget > 100:
        arc_text = "## Active Story Threads\n"
        for a in active_arcs:
            line = f"- {a.title} ({a.current_status.value.upper()})\n"
            if budget - len(arc_text) - len(line) < 50:
                break
            arc_text += line
        sections.append(arc_text)
        budget -= len(arc_text)

    # Section 7: Drift Warnings
    prefix = _DRIFT_PREFIX.get(correction_strength, "IMPORTANT:")
    if drift_warnings and budget > 80:
        drift_text = "## Consistency Warnings\n"
        for d in drift_warnings[:3]:
            line = f"- [{d.severity.value.upper()}] {prefix} {d.conflicting_state}\n"
            if budget - len(drift_text) - len(line) < 20:
                break
            drift_text += line
        sections.append(drift_text)

    body = "\n".join(sections)
    result = f"[MEMORY_KEEPER_START]\n{body}[MEMORY_KEEPER_END]"

    # Append correction note if drift warnings exist
    correction = _build_correction_note(drift_warnings, character.name, correction_strength)
    if correction:
        result += correction

    return result
