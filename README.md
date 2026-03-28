# Memory Keeper

A standalone, LLM-agnostic memory management service for maintaining persistent, coherent character state in roleplay chat applications.

## Overview

Memory Keeper solves a critical problem in AI roleplay: **character inconsistency**. When using large language models for roleplay, characters often "drift" from their established personalities, forget key facts, or contradict previous statements. Memory Keeper acts as a persistent memory backend that learns character personalities and maintains narrative consistency.

### Key Features

- **Persistent Character Memory**: Store and retrieve character traits, relationships, and facts
- **Drift Detection**: Automatically identify when characters behave inconsistently
- **Semantic Search**: Find relevant memories using embeddings
- **Relationship Tracking**: Monitor dynamic relationships between characters
- **Session Snapshots**: Save and rollback to previous session states
- **Multi-Character Support**: Manage multiple characters in a single roleplay session
- **LLM Agnostic**: Works with any LLM backend (OpenAI, Anthropic, local, etc.)

## Architecture

Memory Keeper consists of:

1. **FastAPI Backend**: REST API server for memory operations
2. **SQLite Store**: Persistent storage of character data and facts
3. **Analyzer**: LLM-powered extraction of character information from messages
4. **SillyTavern Adapter**: JavaScript extension for seamless integration with SillyTavern

## Installation

### Prerequisites

- Python 3.10 or higher
- pip or conda for package management

### Quick Start

1. Clone the repository:
```bash
git clone https://github.com/memory-keeper/memory-keeper.git
cd memory-keeper
```

2. Run the installation script:
   - **Windows**: `scripts\install.bat`
   - **Linux/macOS**: `bash scripts/install.sh`

3. Configure your LLM provider:
```bash
memory-keeper init
```

4. Start the server:
```bash
memory-keeper serve
```

5. Install the SillyTavern extension:
   - Copy `adapters/sillytavern/` to your SillyTavern extensions directory
   - Restart SillyTavern
   - Configure the extension to point to your Memory Keeper server

## Configuration

Memory Keeper supports three configuration modes:

### Simple Mode (Default)
Perfect for single-character scenarios with minimal setup:
```bash
memory-keeper init --mode simple
```

### Advanced Mode
Full customization of all parameters:
```bash
memory-keeper init --mode advanced
```

### Custom Mode
Direct YAML configuration for advanced users. Copy `config.example.yaml` to `config.yaml` and customize.

## Core Entities

Memory Keeper tracks 10 entity types:

1. **Session**: Root container for a roleplay scenario
2. **Character Identity**: Core definition of character traits and background
3. **Character State**: Current moment-to-moment state (mood, location, goal)
4. **Fact**: World facts or character-specific knowledge
5. **Event**: Significant narrative events
6. **Relationship Dynamic**: Relationship state between characters
7. **Narrative Arc**: High-level story structure
8. **Drift Log**: Detected character inconsistencies
9. **Behavioral Signature**: Character voice and behavioral patterns
10. **Memory Snapshot**: Point-in-time backup for rollback

## API Endpoints

### Sessions
- `POST /sessions` - Create a new session
- `GET /sessions` - List all sessions
- `GET /sessions/{session_id}` - Get session details
- `DELETE /sessions/{session_id}` - Archive a session

### Characters
- `POST /sessions/{session_id}/characters` - Create character
- `GET /sessions/{session_id}/characters` - List characters
- `GET /sessions/{session_id}/characters/{character_id}` - Get character
- `PUT /sessions/{session_id}/characters/{character_id}` - Update character

### Messages
- `POST /sessions/{session_id}/messages` - Process a message

### Facts
- `POST /sessions/{session_id}/facts` - Create fact
- `GET /sessions/{session_id}/facts` - List facts
- `DELETE /sessions/{session_id}/facts/{fact_id}` - Deactivate fact

### Relationships
- `POST /sessions/{session_id}/relationships` - Create relationship
- `GET /sessions/{session_id}/relationships` - List relationships
- `GET /sessions/{session_id}/relationships/{from_char}/{to_char}` - Get relationship

### Memory
- `GET /sessions/{session_id}/memory` - Get memory context for character
- `POST /sessions/{session_id}/snapshots` - Create snapshot
- `POST /sessions/{session_id}/rollback/{snapshot_id}` - Rollback to snapshot

## Usage Example

### Creating a Session

```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "Crystal Academy Campaign"}'
```

### Creating a Character

```bash
curl -X POST http://localhost:8000/sessions/{session_id}/characters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Elena Blackwood",
    "tier": "primary",
    "core_traits": ["sarcastic", "guarded", "loyal"]
  }'
```

### Processing a Message

```bash
curl -X POST http://localhost:8000/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "character_name": "Elena Blackwood",
    "message_content": "I trust no one in this place."
  }'
```

## Development

### Running Tests

```bash
pytest tests/
```

### Running with Auto-Reload

```bash
memory-keeper serve --reload
```

### Code Style

Memory Keeper uses Black for formatting and Ruff for linting:

```bash
black memory_keeper/
ruff check memory_keeper/
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     SillyTavern Chat                        │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP/REST API
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Memory Keeper FastAPI Server               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Analyzer Layer                          │   │
│  │  • Character Identification    • Drift Detection     │   │
│  │  • Behavior Extraction         • State Consolidation │   │
│  │  • Relationship Discovery      • Embedding Gen       │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Memory Store (SQLite + Embeddings)             │
└─────────────────────────────────────────────────────────────┘
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear commit messages

## License

Memory Keeper is licensed under the MIT License. See LICENSE for details.

## Support

For issues, questions, or suggestions, please open a GitHub issue or check the documentation.

## Roadmap

- [x] Core entity models and SQLite store
- [x] Character identification and extraction
- [x] Drift detection
- [x] SillyTavern adapter
- [ ] PostgreSQL backend support
- [ ] MCP server interface for Claude Desktop
- [ ] Advanced relationship analytics
- [ ] Narrative arc tracking
- [ ] Multi-session analysis
- [ ] Web UI for memory management

## Citation

If you use Memory Keeper in your research or projects, please cite:

```bibtex
@software{memory_keeper,
  title = {Memory Keeper: LLM-Agnostic Memory Management for Roleplay},
  author = {Anujith-Claude},
  year = {2026},
  url = {https://github.com/memory-keeper/memory-keeper}
}
```
