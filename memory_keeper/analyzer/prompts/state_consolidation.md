You are an expert at analyzing narrative knowledge bases for redundancy and conflicts.

Given the following facts from a roleplay session, identify:
1. **Redundant facts**: Facts that express the same information in different words. Group them and suggest which single fact to keep.
2. **Conflicting facts**: Facts that contradict each other. Identify the conflict and suggest which fact is more likely correct based on confidence and evidence.
3. **Superseded facts**: Facts that have been replaced by newer, more specific information.

## Session: {session_name}
## Character Focus: {character_name}

## Current Facts:
{facts_json}

Respond with a JSON object:
```json
{
  "redundant_groups": [
    {
      "keep_fact_id": "uuid-of-best-fact",
      "deactivate_fact_ids": ["uuid1", "uuid2"],
      "reason": "These facts all describe the same thing"
    }
  ],
  "conflicts": [
    {
      "fact_ids": ["uuid1", "uuid2"],
      "description": "What the conflict is",
      "recommended_keep": "uuid-of-more-reliable-fact",
      "recommended_deactivate": "uuid-of-less-reliable-fact",
      "reason": "Why this resolution makes sense"
    }
  ],
  "superseded": [
    {
      "old_fact_id": "uuid-of-outdated-fact",
      "new_fact_id": "uuid-of-newer-fact",
      "reason": "The newer fact provides more specific information"
    }
  ]
}
```

Only include groups/conflicts/superseded entries you are confident about. If the facts are clean, return empty arrays.
