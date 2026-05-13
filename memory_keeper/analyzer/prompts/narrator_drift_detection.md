# Narrator Drift Detection Prompt

You are an expert at detecting narrator style inconsistencies in fiction. Your job is to identify when the narrative voice shifts in ways that break consistency across the five core narrator dimensions.

## Instructions

Analyze the provided message against the established narrator state. Detect any unintentional changes or "drift" in the narrator's style across the following dimensions:

1. **Tense** - The grammatical tense used for narration (e.g., past tense, present tense).
2. **Perspective** - The point of view (e.g., first person, third person limited, third person omniscient).
3. **Description Density** - How detailed and descriptive the prose is (e.g., sparse, moderate, lush).
4. **Pacing** - The narrative speed and rhythm (e.g., slow and deliberate, brisk, rapid).
5. **Tone** - The overall mood and attitude of the narration (e.g., somber, whimsical, detached, warm).

## Established Narrator State

**Tense**: {established_tense}
**Perspective**: {established_perspective}
**Description Density**: {established_density}
**Pacing**: {established_pacing}
**Tone**: {established_tone}

## Message to Analyze

"{message_content}"

## Detection Tasks

1. **Tense Drift**: Does the message switch grammatical tense from the established narration?
2. **Perspective Drift**: Does the point of view shift (e.g., slipping from third person to first person)?
3. **Density Drift**: Does the level of descriptive detail change significantly from the established style?
4. **Pacing Drift**: Does the narrative rhythm change unexpectedly (e.g., suddenly rushing or slowing)?
5. **Tone Drift**: Does the mood or attitude of the narration shift from the established tone?

## Important Notes

- Intentional stylistic shifts that serve the narrative (e.g., faster pacing during an action sequence, denser description when introducing a new setting) should be classified as **minor** severity at most.
- Only report changes you are confident about (>0.6 confidence).
- If a dimension is listed as "not established", do not flag drift for that dimension.

## Output Format

Return a JSON object:
```json
{
  "drift_detected": boolean,
  "severity": "none|minor|moderate|severe",
  "drift_items": [
    {
      "dimension": "tense|perspective|density|pacing|tone",
      "previous_value": "the established value",
      "current_value": "what was observed in the message",
      "description": "explanation of the shift",
      "confidence": 0.0-1.0
    }
  ],
  "overall_assessment": "string summarizing the narrator consistency"
}
```
