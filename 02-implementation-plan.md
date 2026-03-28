# Memory Keeper: Implementation Plan

## Overview
This document provides a detailed, step-by-step implementation plan for Memory Keeper. It breaks the system into manageable phases with clear objectives and dependencies.

## Phase 1: Foundation (Weeks 1-2)

### 1.1 Project Setup
- Initialize Python project structure with pyproject.toml
- Set up virtual environment scaffolding
- Configure pytest and testing infrastructure
- Install all required dependencies (FastAPI, SQLite, sentence-transformers, etc.)

### 1.2 Data Models
- Define core Pydantic models in `memory_keeper/store/models.py`:
  - Session, Character Identity, Character State
  - Fact, Event, Relationship Dynamic
  - Narrator State, Drift Log, Memory Snapshot
- Add validation and default values
- Create serialization methods (JSON, embeddings)

### 1.3 Configuration System
- Build `memory_keeper/config.py` with Pydantic ConfigModel
- Support YAML file loading with environment variable override
- Define configuration tiers (simple, advanced, custom)
- Create example config template

### 1.4 Database Layer
- Implement SQLite schema migrations (if using alembic) or hardcoded schema
- Create `memory_keeper/store/sqlite_store.py` base class
- Implement CRUD operations for all entity types
- Add soft delete functionality for sessions
- Implement fact activation/deactivation
- Test all database operations thoroughly

## Phase 2: Core Analyzer (Weeks 3-4)

### 2.1 Prompt Engineering
- Create prompt templates in `memory_keeper/analyzer/prompts/`
- Write system prompts for each analyzer function:
  - Character identification and tier classification
  - Behavior extraction (speech patterns, mannerisms, trait evolution)
  - Relationship dynamic detection
  - Fact extraction from dialogue
  - Drift detection (inconsistency identification)
  - State consolidation
- Test prompts with example data

### 2.2 Analyzer Implementation
- Build `memory_keeper/analyzer/character_analyzer.py`
- Implement `extract_character_info()` function
- Build `memory_keeper/analyzer/drift_detector.py`
- Implement drift detection and consolidation
- Create embedding generation utilities

### 2.3 Integration with LLM
- Set up LLM provider abstraction (OpenAI, local, etc.)
- Implement streaming and async request handling
- Add error handling and retry logic
- Create prompt templating with variable substitution

## Phase 3: API Layer (Weeks 5-6)

### 3.1 FastAPI Setup
- Initialize FastAPI app in `memory_keeper/main.py` and `memory_keeper/api/server.py`
- Configure CORS, middleware, and error handlers
- Set up Uvicorn ASGI server
- Add health check endpoints

### 3.2 REST Routes
- Implement session management routes (create, list, get, update, delete)
- Build character routes (create, list, get, update)
- Create fact routes (add, list, filter, deactivate)
- Build relationship routes (create, list, get)
- Implement memory retrieval routes with semantic search
- Add admin routes (export, import, cleanup)

### 3.3 Message Processing Pipeline
- Build message ingestion endpoint
- Create async message processing queue
- Implement character identification from messages
- Wire analyzer to API layer
- Add response generation with context

### 3.4 Testing
- Write unit tests for each route
- Test error cases and validation
- Create integration tests for message flow

## Phase 4: SillyTavern Adapter (Weeks 7-8)

### 4.1 Extension Structure
- Create `adapters/sillytavern/` directory structure
- Write `manifest.json` with extension metadata
- Build `index.js` main extension file
- Create `style.css` for UI elements

### 4.2 SillyTavern Integration
- Hook into SillyTavern message send/receive events
- Implement character detection from chat context
- Add memory context injection into system prompt
- Create settings UI for Memory Keeper server configuration
- Build memory preview/editing UI

### 4.3 Testing
- Test in actual SillyTavern instance
- Verify message flow and state updates
- Test with multiple characters in same chat

## Phase 5: Rollback System (Week 9)

### 5.1 Snapshot Implementation
- Implement session snapshot creation in store
- Create snapshot serialization
- Build snapshot storage mechanism

### 5.2 Rollback Functionality
- Implement session state rollback to previous snapshot
- Add rollback history and versioning
- Create rollback UI in adapter
- Test rollback with various scenarios

## Phase 6: Simple Mode & Installation (Week 10)

### 6.1 Simple Mode
- Implement simplified configuration option
- Auto-configure defaults for single-character scenario
- Skip advanced memory management features
- Provide preset profiles (writer, roleplay, storytelling)

### 6.2 Installation Scripts
- Write Windows install script (`scripts/install.bat`)
- Write Linux/macOS install script (`scripts/install.sh`)
- Create setup wizard (`memory_keeper init` command)
- Test installation on fresh systems

### 6.3 Documentation
- Write user guide for Memory Keeper
- Create SillyTavern adapter setup guide
- Document configuration options
- Provide example workflows

## Phase 7: Testing & Iteration (Week 11+)

### 7.1 Comprehensive Testing
- Unit tests for all modules
- Integration tests for full message flow
- End-to-end tests with SillyTavern
- Performance testing with large memory stores

### 7.2 Bug Fixes & Optimization
- Profile code for performance bottlenecks
- Optimize database queries
- Implement caching where beneficial
- Fix integration issues

### 7.3 Polish & Release
- Final documentation review
- Example session walkthroughs
- Release artifacts (wheels, installers)
- Community feedback incorporation

## Key Implementation Principles

1. **Async-First**: All I/O operations should be async using asyncio
2. **Type Safety**: Use Pydantic models and type hints throughout
3. **Error Handling**: Graceful degradation with informative error messages
4. **Testing**: Unit tests for business logic, integration tests for workflows
5. **Modularity**: Keep analyzer, store, and API concerns separate
6. **Extensibility**: Allow pluggable LLM providers and storage backends

## Dependencies & Tools

- **FastAPI**: Web framework
- **aiosqlite**: Async SQLite driver
- **pydantic**: Data validation
- **sentence-transformers**: Embedding generation
- **httpx**: Async HTTP client for LLM APIs
- **pytest**: Testing framework
- **python-dotenv**: Environment configuration

## Success Criteria

- All CRUD operations tested and working
- Message flow from SillyTavern to Memory Keeper and back
- Character identification and memory retrieval functional
- Drift detection identifying inconsistencies
- Rollback system preserving and restoring session state
- Installation scripts working on Windows, Linux, macOS
- Comprehensive test coverage (>80%)
- Documentation complete and clear
