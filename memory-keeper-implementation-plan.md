# Memory Keeper - Complete Implementation Guide

## Project Overview

Memory Keeper is a standalone, LLM-agnostic memory management service designed to maintain persistent, coherent character state in roleplay chat applications. It provides a unified memory backend that other applications (like SillyTavern) can query and update.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     SillyTavern Chat                        │
│              (or other roleplay application)                │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│           Memory Keeper JavaScript Adapter                  │
│         (Intercepts messages, manages state)                │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP/REST API
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Memory Keeper FastAPI Server               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Session Mgmt │  │ Message Queue│  │ Admin Interface  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Analyzer Layer                            │ │
│  │  • Character Identification    • Drift Detection       │ │
│  │  • Behavior Extraction         • State Consolidation   │ │
│  │  • Relationship Discovery      • Embedding Generation  │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Memory Store (SQLite + Embeddings)             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Characters   │  │  Facts       │  │ Relationships    │  │
│  │ Session Data │  │  Events      │  │ Narrative Arcs   │  │
│  │ States       │  │  Drift Logs  │  │ Memory Snapshots │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Core Entity Schema (10 Entity Types)

### 1. Session
The root container for a roleplay scenario. Tracks all characters, facts, and state for a single ongoing narrative.

**Fields:**
- session_id: UUID (primary key)
- name: str (scenario title, e.g., "Crystal Academy Semester 1")
- created_at: datetime
- updated_at: datetime
- archived: bool (soft delete)
- config: dict (session-specific settings)

### 2. Character Identity
Core definition of a character's permanent traits, background, and personality.

**Fields:**
- character_id: UUID
- session_id: UUID (foreign key)
- name: str (character display name)
- tier: enum(PRIMARY, SECONDARY, TERTIARY, NPC)
- core_traits: list[str] (e.g., ["sarcastic", "guarded", "loyal"])
- background: str (character history)
- worldview: str (character beliefs)
- speech_patterns: SpeechPatterns object
- appearance: str (physical description)
- created_at: datetime
- last_modified: datetime
- active: bool

### 3. Behavioral Signature
Captures character voice and behavioral patterns for realistic text generation.

**Fields:**
- signature_id: UUID
- character_id: UUID
- session_id: UUID
- vocabulary_patterns: list[str] (unique words/phrases)
- speech_quirks: list[str] (mannerisms, catchphrases)
- emotional_ranges: dict[emotion, expression_patterns]
- interaction_style: str (how they approach others)
- confidence: float (0-1 measure of consistency)
- last_observed: datetime

### 4. Character State
Current moment-to-moment state for a character (mood, location, current goal).

**Fields:**
- state_id: UUID
- character_id: UUID
- session_id: UUID
- mood: str (e.g., "tense", "cheerful")
- location: str (current location in world)
- current_goal: str (what they're trying to accomplish)
- recent_memory: str (what happened recently)
- timestamp: datetime

### 5. Fact
World facts or character-specific facts about the roleplay scenario.

**Fields:**
- fact_id: UUID
- session_id: UUID
- category: enum(WORLD, CHARACTER, RELATIONSHIP, PLOT)
- subject: str (entity the fact is about)
- predicate: str (relationship type)
- object: str (target entity)
- evidence: str (where this fact came from)
- confidence: float (0-1)
- active: bool (can be deactivated if proven false)
- created_at: datetime
- embedding: vector (for semantic search)

### 6. Event
Significant narrative events that shaped character arcs.

**Fields:**
- event_id: UUID
- session_id: UUID
- involved_characters: list[UUID]
- description: str
- emotional_impact: dict[character_id, emotional_effect]
- timestamp: datetime (story time)
- session_turn: int (order in message sequence)

### 7. Relationship Dynamic
Tracks relationship state between characters.

**Fields:**
- relationship_id: UUID
- session_id: UUID
- from_character: UUID
- to_character: UUID
- label: str (e.g., "reluctant allies", "secret lovers")
- trust_level: float (-1 to 1, -1 = complete distrust, 1 = complete trust)
- power_balance: float (-1 to 1, -1 = from_char weaker, 1 = from_char stronger)
- emotional_undercurrent: str (hidden feelings)
- history: str (relationship timeline)
- last_interaction: datetime

### 8. Narrative Arc
High-level story structure and plot threads.

**Fields:**
- arc_id: UUID
- session_id: UUID
- title: str
- involved_characters: list[UUID]
- current_status: enum(SETUP, DEVELOPMENT, CLIMAX, RESOLUTION, CLOSED)
- beats: list[str] (story milestones)
- expected_outcome: str (where this should lead)

### 9. Drift Log
Tracks character inconsistencies (AI drift).

**Fields:**
- drift_id: UUID
- character_id: UUID
- session_id: UUID
- inconsistency_type: enum(TRAIT, RELATIONSHIP, KNOWLEDGE, BEHAVIOR)
- detected_in_message: str (the message that revealed drift)
- previous_state: str (what we knew before)
- conflicting_state: str (the new contradiction)
- severity: enum(MINOR, MODERATE, SEVERE)
- resolution: str (how it was resolved)
- timestamp: datetime

### 10. Memory Snapshot
Point-in-time backup of entire session state for rollback.

**Fields:**
- snapshot_id: UUID
- session_id: UUID
- timestamp: datetime
- snapshot_data: json (complete serialization of session state)
- created_by: str (user who triggered snapshot)
- notes: str (reason for snapshot)

## Message Processing Loop

```
Message arrives in SillyTavern
    ↓
Adapter intercepts & extracts:
  • Sender (character name)
  • Content (message text)
  • System context (location, etc.)
    ↓
Adapter sends to Memory Keeper API
    ↓
Memory Keeper:
  1. Identify character (fuzzy match against known characters)
  2. Extract new facts/relationships
  3. Detect character inconsistencies (drift)
  4. Update character state
  5. Consolidate memory if needed
    ↓
Memory Keeper responds with:
  • Character memory context
  • Detected contradictions
  • Suggested story prompt adjustments
    ↓
Adapter injects memory context into system prompt
    ↓
LLM generates response with proper character voice
    ↓
Message sent back to chat
    ↓
[Loop continues]
```

## Rollback System

The rollback system allows reverting to previous session states if character drift becomes unmanageable.

### Snapshot Creation
- Automatic snapshots every N messages (configurable)
- Manual snapshots on demand via admin UI
- Snapshots include full serialization of all entities

### Rollback Process
1. User requests rollback to specific snapshot
2. System validates snapshot integrity
3. All post-snapshot entities are marked as superseded
4. New entities from snapshot are reactivated
5. Continue from that point forward

## Configuration System

Memory Keeper supports three configuration tiers:

### Simple Mode
- Auto-configured for single-character scenarios
- Minimal setup required
- All advanced features enabled but non-intrusive
- Perfect for writers using a single character

### Advanced Mode
- Full customization of all parameters
- Per-character configuration
- Custom analyzer prompts
- Integration with external memory systems

### Custom Mode
- Direct YAML configuration
- Environment variable overrides
- Custom storage backends
- Custom LLM providers

## Key Implementation Details

### Analyzer
The analyzer transforms raw messages into structured memory entities.

**Key Functions:**
- `extract_character_info()`: Identify character speaking and extract key traits
- `extract_relationships()`: Detect and evolve relationship dynamics
- `extract_facts()`: Pull world-building information from dialogue
- `detect_drift()`: Identify inconsistencies in character behavior
- `consolidate_state()`: Merge redundant facts and resolve conflicts

### Store
The persistent memory backend handling all CRUD operations.

**Key Operations:**
- Session lifecycle (create, list, get, update, delete/archive)
- Character CRUD with embedding generation
- Fact management with activation/deactivation
- Semantic search over facts using embeddings
- Snapshot creation and rollback

### API
FastAPI-based REST interface.

**Endpoints:**
- POST `/sessions` - Create session
- GET `/sessions` - List sessions
- GET `/sessions/{session_id}` - Get session details
- POST `/sessions/{session_id}/messages` - Process message
- GET `/sessions/{session_id}/characters` - List characters
- POST `/sessions/{session_id}/characters` - Add character
- GET `/sessions/{session_id}/memory` - Retrieve memory context
- POST `/sessions/{session_id}/snapshots` - Create snapshot
- POST `/sessions/{session_id}/rollback/{snapshot_id}` - Rollback

## Development Roadmap

### Sprint 1: Foundation (Week 1-2)
- Project setup and dependency installation
- Data model definition in Pydantic
- SQLite schema and migrations
- Basic CRUD store operations

### Sprint 2: Analyzer (Week 3-4)
- Prompt engineering for all analyzer functions
- Character identification and tier classification
- Relationship extraction
- Drift detection implementation

### Sprint 3: API Layer (Week 5-6)
- FastAPI server setup
- All REST endpoints
- Message processing pipeline
- Integration tests

### Sprint 4: SillyTavern Adapter (Week 7-8)
- JavaScript extension structure
- Message interception
- Context injection
- Settings UI

### Sprint 5: Rollback & Polish (Week 9-10)
- Snapshot system
- Rollback functionality
- Installation scripts
- Documentation

### Sprint 6: Testing & Release (Week 11+)
- Comprehensive test suite
- Performance optimization
- Bug fixes
- Release preparation

## Success Metrics

✓ Core entities persisting reliably in SQLite
✓ Message flow working end-to-end
✓ Character identification accurate >95% of time
✓ Drift detection catching inconsistencies
✓ Relationship dynamics evolving realistically
✓ Rollback system restoring state correctly
✓ Installation process smooth on multiple OS
✓ Test coverage >80%
