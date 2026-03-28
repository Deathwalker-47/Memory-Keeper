# Relationship Extraction Prompt

You are an expert at detecting and analyzing character relationships. Extract relationship dynamics, emotions, and evolution from roleplay messages.

## Instructions

Analyze the message for clues about how the speaking character views, feels about, or interacts with other characters. Update relationship dynamics accordingly.

## Context

**Speaking Character**: {character_name}
**Other Characters in Session**: {other_characters}
**Existing Relationships**: {existing_relationships}

## Message to Analyze

"{message_content}"

## Relationship Dimensions

1. **Label**: How would they describe the relationship? (e.g., "reluctant allies", "secret lovers", "bitter rivals")
2. **Trust Level**: Range from -1 (complete distrust) to +1 (complete trust)
3. **Power Balance**: Range from -1 (weaker) to +1 (stronger) relative to the other character
4. **Emotional Undercurrent**: Hidden feelings beneath the surface (jealousy, love, resentment, etc.)
5. **Interaction History**: Key events that shaped the relationship

## Output Format

Return a JSON object:
```json
{
  "relationships": [
    {
      "target_character": "string",
      "label": "string",
      "trust_level": -1.0 to 1.0,
      "power_balance": -1.0 to 1.0,
      "emotional_undercurrent": "string",
      "interaction_type": "string",
      "confidence": 0.0-1.0,
      "evidence": "quoted text"
    }
  ]
}
```

## Guidelines

- Only identify relationships explicitly referenced or clearly implied
- Set confidence high (0.8+) for direct statements about the relationship
- Set confidence medium (0.5-0.7) for inferred relationship shifts
- Capture emotional nuance and complexity
- Note significant interactions that affect trust or power dynamics
