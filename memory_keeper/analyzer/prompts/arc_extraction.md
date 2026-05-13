# Narrative Arc Extraction Prompt

You are an expert at identifying and tracking narrative story arcs in roleplay fiction. Your task is to detect new story threads and update existing ones based on the latest message.

## Instructions

Analyze the message for narrative arc developments. A narrative arc is a storyline thread that spans multiple exchanges — a quest, a conflict, a mystery, a character growth arc, etc.

## Character Context

**Character**: {character_name}

## Existing Arcs

{existing_arcs}

## Message to Analyze

"{message_content}"

## Analysis Tasks

1. **New Arcs**: Identify any new story threads introduced in this message
2. **Arc Updates**: For existing arcs, detect status changes or new story beats
3. **Arc Status**: Classify each arc's current phase

## Arc Statuses

- **setup**: Arc is being introduced, characters/conflicts being established
- **development**: Arc is progressing, complications arising
- **climax**: Arc is reaching its peak tension or confrontation
- **resolution**: Arc is being wrapped up, consequences playing out
- **closed**: Arc is fully concluded

## Output Format

Return a JSON object:
```json
{
  "arcs": [
    {
      "title": "short descriptive title for the arc",
      "is_new": true,
      "existing_arc_title": null,
      "involved_characters": ["character name"],
      "current_status": "setup|development|climax|resolution|closed",
      "new_beat": "what just happened in this arc",
      "expected_outcome": "where this arc might be heading"
    }
  ]
}
```

For updates to existing arcs, set `is_new` to false and `existing_arc_title` to the matching arc title.

## Guidelines

- Only create new arcs for significant story threads, not minor events
- Prefer updating existing arcs over creating duplicates
- Set `expected_outcome` based on narrative trajectory
- If no arcs are relevant to this message, return `{"arcs": []}`
