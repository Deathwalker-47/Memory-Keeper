"""Format memory context for injection into chat prompts."""

from typing import List, Optional

from memory_keeper.store.models import (
    CharacterIdentity,
    CharacterState,
    Fact,
    RelationshipDynamic,
    NarrativeArc,
    DriftLog,
)


def format_memory_context(
    character: CharacterIdentity,
    state: Optional[CharacterState],
    facts: List[Fact],
    relationships: List[RelationshipDynamic],
    arcs: List[NarrativeArc],
    drift_warnings: List[DriftLog],
    character_names: dict = None,
    max_length: int = 2000,
) -> str:
    """Build the namespaced memory block for prompt injection.

    Prioritizes: identity > state > relationships > facts > arcs > drift warnings.
    Respects max_length budget (approximate character count).

    Args:
        character: The character to build context for.
        state: Current character state (mood, location, etc.).
        facts: Relevant facts for the session.
        relationships: Relationships involving this character.
        arcs: Active narrative arcs.
        drift_warnings: Recent drift logs for this character.
        character_names: Optional mapping of character_id -> name for display.
        max_length: Maximum character count for the context block.
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

    # Section 2: Current State
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

    # Section 3: Relationships
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

    # Section 4: Key Facts
    if facts and budget > 100:
        fact_text = "## Key Facts\n"
        for f in sorted(facts, key=lambda x: x.confidence, reverse=True):
            line = f"- {f.subject} {f.predicate} {f.object}\n"
            if budget - len(fact_text) - len(line) < 50:
                break
            fact_text += line
        sections.append(fact_text)
        budget -= len(fact_text)

    # Section 5: Active Story Threads
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

    # Section 6: Drift Warnings (lowest priority)
    if drift_warnings and budget > 80:
        drift_text = "## Consistency Warnings\n"
        for d in drift_warnings[:3]:
            line = f"- [{d.severity.value.upper()}] {d.conflicting_state}\n"
            if budget - len(drift_text) - len(line) < 20:
                break
            drift_text += line
        sections.append(drift_text)

    body = "\n".join(sections)
    return f"[MEMORY_KEEPER_START]\n{body}[MEMORY_KEEPER_END]"
