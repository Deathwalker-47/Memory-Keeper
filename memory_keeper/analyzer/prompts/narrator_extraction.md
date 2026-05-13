# Narrator State Extraction Prompt

You are an expert at analyzing narrative voice in roleplay fiction. Your task is to identify the narrator's current style — tense, perspective, density of description, pacing, and overall tone.

## Instructions

Analyze the provided message and determine the narrator's stylistic choices. Focus on HOW the story is being told, not WHAT is happening.

## Previous Narrator State

{previous_narrator_state}

## Message to Analyze

"{message_content}"

## Analysis Dimensions

- **Tense**: What grammatical tense is the narration in? (past, present, future)
- **Perspective**: What point of view is used? (first_person, second_person, third_person, third_person_omniscient)
- **Description Density**: How detailed are the descriptions? (sparse, moderate, dense)
- **Pacing**: How quickly do events progress? (slow, moderate, fast)
- **Tone**: What is the overall emotional tone? (dark, neutral, whimsical, tense, romantic, melancholic, humorous)

## Output Format

Return a JSON object:
```json
{
  "tense": "past|present|future",
  "perspective": "first_person|second_person|third_person|third_person_omniscient",
  "description_density": "sparse|moderate|dense",
  "pacing": "slow|moderate|fast",
  "tone": "string describing the dominant tone"
}
```

## Guidelines

- Base your analysis only on the current message
- If the narrator shifts style mid-message, report the dominant style
- Use the previous narrator state for comparison but report the current state
