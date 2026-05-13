"""PostgreSQL implementation of the memory store using asyncpg."""

import json
import math
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import asyncpg

from memory_keeper.store.base import BaseStore
from memory_keeper.store.models import (
    Session,
    CharacterIdentity,
    CharacterTier,
    Fact,
    FactCategory,
    CharacterState,
    NarratorState,
    RelationshipDynamic,
    Event,
    NarrativeArc,
    ArcStatus,
    DriftLog,
    DriftSeverity,
    InconsistencyType,
    MemorySnapshot,
    BehavioralSignature,
)


class PostgresStore(BaseStore):
    """PostgreSQL-based implementation of memory store."""

    def __init__(self, dsn: str, min_pool: int = 2, max_pool: int = 10):
        """Initialize store with connection DSN and pool settings."""
        self.dsn = dsn
        self.min_pool = min_pool
        self.max_pool = max_pool
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        """Initialize connection pool and create schema."""
        self.pool = await asyncpg.create_pool(
            self.dsn, min_size=self.min_pool, max_size=self.max_pool
        )
        async with self.pool.acquire() as conn:
            await self._create_schema(conn)

    async def close(self) -> None:
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()

    async def _create_schema(self, conn: asyncpg.Connection) -> None:
        """Create database schema."""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                message_count INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL,
                archived BOOLEAN DEFAULT FALSE,
                config JSONB DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS characters (
                character_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                name TEXT NOT NULL,
                tier TEXT DEFAULT 'primary',
                core_traits JSONB DEFAULT '[]',
                background TEXT,
                worldview TEXT,
                speech_patterns JSONB DEFAULT '{}',
                appearance TEXT,
                created_at TIMESTAMPTZ NOT NULL,
                last_modified TIMESTAMPTZ NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS character_states (
                state_id TEXT PRIMARY KEY,
                character_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                mood TEXT,
                location TEXT,
                current_goal TEXT,
                recent_memory TEXT,
                timestamp TIMESTAMPTZ NOT NULL,
                UNIQUE (character_id, session_id),
                FOREIGN KEY (character_id) REFERENCES characters(character_id),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS facts (
                fact_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                category TEXT NOT NULL,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                evidence TEXT,
                confidence REAL DEFAULT 0.5,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL,
                embedding JSONB,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS relationships (
                relationship_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                from_character TEXT NOT NULL,
                to_character TEXT NOT NULL,
                label TEXT NOT NULL,
                trust_level REAL DEFAULT 0,
                power_balance REAL DEFAULT 0,
                emotional_undercurrent TEXT,
                history TEXT,
                last_interaction TIMESTAMPTZ NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                FOREIGN KEY (from_character) REFERENCES characters(character_id),
                FOREIGN KEY (to_character) REFERENCES characters(character_id)
            );

            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                involved_characters JSONB DEFAULT '[]',
                description TEXT NOT NULL,
                emotional_impact JSONB DEFAULT '{}',
                timestamp TIMESTAMPTZ NOT NULL,
                session_turn INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS narrative_arcs (
                arc_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                title TEXT NOT NULL,
                involved_characters JSONB DEFAULT '[]',
                current_status TEXT DEFAULT 'setup',
                beats JSONB DEFAULT '[]',
                expected_outcome TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS drift_logs (
                drift_id TEXT PRIMARY KEY,
                character_id TEXT,
                session_id TEXT NOT NULL,
                inconsistency_type TEXT NOT NULL,
                detected_in_message TEXT NOT NULL,
                previous_state TEXT NOT NULL,
                conflicting_state TEXT NOT NULL,
                severity TEXT DEFAULT 'minor',
                resolution TEXT,
                timestamp TIMESTAMPTZ NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS memory_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                snapshot_data JSONB NOT NULL,
                created_by TEXT,
                notes TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS behavioral_signatures (
                signature_id TEXT PRIMARY KEY,
                character_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                vocabulary_patterns JSONB DEFAULT '[]',
                speech_quirks JSONB DEFAULT '[]',
                emotional_ranges JSONB DEFAULT '{}',
                interaction_style TEXT,
                confidence REAL DEFAULT 0.5,
                last_observed TIMESTAMPTZ NOT NULL,
                FOREIGN KEY (character_id) REFERENCES characters(character_id),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS narrator_states (
                narrator_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL UNIQUE,
                tense TEXT,
                perspective TEXT,
                description_density TEXT,
                pacing TEXT,
                tone TEXT,
                timestamp TIMESTAMPTZ NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE INDEX IF NOT EXISTS idx_characters_session ON characters(session_id);
            CREATE INDEX IF NOT EXISTS idx_facts_session ON facts(session_id);
            CREATE INDEX IF NOT EXISTS idx_relationships_session ON relationships(session_id);
            CREATE INDEX IF NOT EXISTS idx_drift_logs_session ON drift_logs(session_id);
            CREATE INDEX IF NOT EXISTS idx_narrator_states_session ON narrator_states(session_id);
        """)

    # ── Row conversion helpers ───────────────────────────────

    @staticmethod
    def _row_to_session(row: asyncpg.Record) -> Session:
        """Convert a database row to a Session model."""
        return Session(
            session_id=UUID(row["session_id"]),
            name=row["name"],
            message_count=row["message_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            archived=row["archived"],
            config=json.loads(row["config"]) if isinstance(row["config"], str) else row["config"],
        )

    @staticmethod
    def _row_to_character(row: asyncpg.Record) -> CharacterIdentity:
        """Convert a database row to a CharacterIdentity model."""
        speech = row["speech_patterns"]
        if isinstance(speech, str):
            speech = json.loads(speech)
        return CharacterIdentity(
            character_id=UUID(row["character_id"]),
            session_id=UUID(row["session_id"]),
            name=row["name"],
            tier=CharacterTier(row["tier"]),
            core_traits=json.loads(row["core_traits"]) if isinstance(row["core_traits"], str) else row["core_traits"],
            background=row["background"],
            worldview=row["worldview"],
            speech_patterns=speech,
            appearance=row["appearance"],
            created_at=row["created_at"],
            last_modified=row["last_modified"],
            active=row["active"],
        )

    @staticmethod
    def _row_to_event(row: asyncpg.Record) -> Event:
        """Convert a database row to an Event model."""
        involved = row["involved_characters"]
        if isinstance(involved, str):
            involved = json.loads(involved)
        impact = row["emotional_impact"]
        if isinstance(impact, str):
            impact = json.loads(impact)
        return Event(
            event_id=UUID(row["event_id"]),
            session_id=UUID(row["session_id"]),
            involved_characters=[UUID(c) for c in involved],
            description=row["description"],
            emotional_impact={UUID(k): v for k, v in impact.items()},
            timestamp=row["timestamp"],
            session_turn=row["session_turn"],
        )

    @staticmethod
    def _row_to_arc(row: asyncpg.Record) -> NarrativeArc:
        """Convert a database row to a NarrativeArc model."""
        involved = row["involved_characters"]
        if isinstance(involved, str):
            involved = json.loads(involved)
        beats = row["beats"]
        if isinstance(beats, str):
            beats = json.loads(beats)
        return NarrativeArc(
            arc_id=UUID(row["arc_id"]),
            session_id=UUID(row["session_id"]),
            title=row["title"],
            involved_characters=[UUID(c) for c in involved],
            current_status=ArcStatus(row["current_status"]),
            beats=beats,
            expected_outcome=row["expected_outcome"],
        )

    @staticmethod
    def _row_to_signature(row: asyncpg.Record) -> BehavioralSignature:
        """Convert a database row to a BehavioralSignature model."""
        vocab = row["vocabulary_patterns"]
        if isinstance(vocab, str):
            vocab = json.loads(vocab)
        quirks = row["speech_quirks"]
        if isinstance(quirks, str):
            quirks = json.loads(quirks)
        ranges = row["emotional_ranges"]
        if isinstance(ranges, str):
            ranges = json.loads(ranges)
        return BehavioralSignature(
            signature_id=UUID(row["signature_id"]),
            character_id=UUID(row["character_id"]),
            session_id=UUID(row["session_id"]),
            vocabulary_patterns=vocab,
            speech_quirks=quirks,
            emotional_ranges=ranges,
            interaction_style=row["interaction_style"],
            confidence=row["confidence"],
            last_observed=row["last_observed"],
        )

    @staticmethod
    def _row_to_snapshot(row: asyncpg.Record) -> MemorySnapshot:
        """Convert a database row to a MemorySnapshot model."""
        data = row["snapshot_data"]
        if isinstance(data, str):
            data = json.loads(data)
        return MemorySnapshot(
            snapshot_id=UUID(row["snapshot_id"]),
            session_id=UUID(row["session_id"]),
            timestamp=row["timestamp"],
            snapshot_data=data,
            created_by=row["created_by"],
            notes=row["notes"],
        )

    # ── Session operations ───────────────────────────────────

    async def create_session(self, session: Session) -> Session:
        """Create a new session."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sessions (session_id, name, message_count, created_at, updated_at, config)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                str(session.session_id),
                session.name,
                session.message_count,
                session.created_at,
                session.updated_at,
                json.dumps(session.config),
            )
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM sessions WHERE session_id = $1",
                session_id,
            )
        if row:
            return self._row_to_session(row)
        return None

    async def list_sessions(self) -> List[Session]:
        """List all non-archived sessions."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM sessions WHERE archived = FALSE ORDER BY updated_at DESC"
            )
        return [self._row_to_session(row) for row in rows]

    async def update_session(self, session: Session) -> Session:
        """Update an existing session."""
        session.updated_at = datetime.utcnow()
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE sessions SET name = $1, updated_at = $2, config = $3
                WHERE session_id = $4
                """,
                session.name,
                session.updated_at,
                json.dumps(session.config),
                str(session.session_id),
            )
        return session

    async def delete_session(self, session_id: str) -> None:
        """Soft delete a session."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE sessions SET archived = TRUE WHERE session_id = $1",
                session_id,
            )

    async def increment_message_count(self, session_id: str) -> int:
        """Increment and return the new message count."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE sessions SET message_count = message_count + 1
                WHERE session_id = $1
                RETURNING message_count
                """,
                session_id,
            )
        return row["message_count"]

    # ── Character operations ─────────────────────────────────

    async def create_character(self, character: CharacterIdentity) -> CharacterIdentity:
        """Create a new character."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO characters
                (character_id, session_id, name, tier, core_traits, background, worldview,
                 speech_patterns, appearance, created_at, last_modified, active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                str(character.character_id),
                str(character.session_id),
                character.name,
                character.tier.value,
                json.dumps(character.core_traits),
                character.background,
                character.worldview,
                character.speech_patterns.model_dump_json(),
                character.appearance,
                character.created_at,
                character.last_modified,
                character.active,
            )
        return character

    async def get_character(self, character_id: str) -> Optional[CharacterIdentity]:
        """Retrieve a character by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM characters WHERE character_id = $1",
                character_id,
            )
        if row:
            return self._row_to_character(row)
        return None

    async def get_characters(self, session_id: str) -> List[CharacterIdentity]:
        """List all active characters in a session."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM characters WHERE session_id = $1 AND active = TRUE",
                str(session_id),
            )
        return [self._row_to_character(row) for row in rows]

    async def find_character_by_name(
        self, session_id: str, name: str
    ) -> Optional[CharacterIdentity]:
        """Find a character by name (case-insensitive)."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM characters WHERE session_id = $1 AND LOWER(name) = LOWER($2)",
                str(session_id),
                name,
            )
        if row:
            return self._row_to_character(row)
        return None

    async def update_character(self, character: CharacterIdentity) -> CharacterIdentity:
        """Update an existing character."""
        character.last_modified = datetime.utcnow()
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE characters
                SET name = $1, tier = $2, core_traits = $3, background = $4, worldview = $5,
                    speech_patterns = $6, appearance = $7, last_modified = $8, active = $9
                WHERE character_id = $10
                """,
                character.name,
                character.tier.value,
                json.dumps(character.core_traits),
                character.background,
                character.worldview,
                character.speech_patterns.model_dump_json(),
                character.appearance,
                character.last_modified,
                character.active,
                str(character.character_id),
            )
        return character

    # ── Character State operations ───────────────────────────

    async def upsert_character_state(self, state: CharacterState) -> CharacterState:
        """Insert or update character state."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO character_states
                (state_id, character_id, session_id, mood, location, current_goal,
                 recent_memory, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (character_id, session_id) DO UPDATE SET
                    mood = EXCLUDED.mood,
                    location = EXCLUDED.location,
                    current_goal = EXCLUDED.current_goal,
                    recent_memory = EXCLUDED.recent_memory,
                    timestamp = EXCLUDED.timestamp
                """,
                str(state.state_id),
                str(state.character_id),
                str(state.session_id),
                state.mood,
                state.location,
                state.current_goal,
                state.recent_memory,
                state.timestamp,
            )
        return state

    async def get_character_state(
        self, character_id: str, session_id: str
    ) -> Optional[CharacterState]:
        """Get current state of a character."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM character_states
                WHERE character_id = $1 AND session_id = $2
                ORDER BY timestamp DESC LIMIT 1
                """,
                character_id,
                session_id,
            )
        if row:
            return CharacterState(
                state_id=UUID(row["state_id"]),
                character_id=UUID(row["character_id"]),
                session_id=UUID(row["session_id"]),
                mood=row["mood"],
                location=row["location"],
                current_goal=row["current_goal"],
                recent_memory=row["recent_memory"],
                timestamp=row["timestamp"],
            )
        return None

    # ── Narrator State operations ────────────────────────────

    async def upsert_narrator_state(self, state: NarratorState) -> NarratorState:
        """Insert or replace narrator state for a session (one per session)."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO narrator_states
                (narrator_id, session_id, tense, perspective, description_density,
                 pacing, tone, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (session_id) DO UPDATE SET
                    narrator_id = EXCLUDED.narrator_id,
                    tense = EXCLUDED.tense,
                    perspective = EXCLUDED.perspective,
                    description_density = EXCLUDED.description_density,
                    pacing = EXCLUDED.pacing,
                    tone = EXCLUDED.tone,
                    timestamp = EXCLUDED.timestamp
                """,
                str(state.narrator_id),
                str(state.session_id),
                state.tense,
                state.perspective,
                state.description_density,
                state.pacing,
                state.tone,
                state.timestamp,
            )
        return state

    async def get_narrator_state(self, session_id: str) -> Optional[NarratorState]:
        """Get narrator state for a session."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM narrator_states WHERE session_id = $1 ORDER BY timestamp DESC LIMIT 1",
                session_id,
            )
        if not row:
            return None
        return NarratorState(
            narrator_id=UUID(row["narrator_id"]),
            session_id=UUID(row["session_id"]),
            tense=row["tense"],
            perspective=row["perspective"],
            description_density=row["description_density"],
            pacing=row["pacing"],
            tone=row["tone"],
            timestamp=row["timestamp"],
        )

    async def clear_session_narrator_states(self, session_id: str) -> None:
        """Delete narrator state for a session."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM narrator_states WHERE session_id = $1",
                str(session_id),
            )

    # ── Behavioral Signature operations ──────────────────────

    async def create_behavioral_signature(self, sig: BehavioralSignature) -> BehavioralSignature:
        """Create a new behavioral signature."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO behavioral_signatures
                (signature_id, character_id, session_id, vocabulary_patterns,
                 speech_quirks, emotional_ranges, interaction_style, confidence, last_observed)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                str(sig.signature_id),
                str(sig.character_id),
                str(sig.session_id),
                json.dumps(sig.vocabulary_patterns),
                json.dumps(sig.speech_quirks),
                json.dumps(sig.emotional_ranges),
                sig.interaction_style,
                sig.confidence,
                sig.last_observed,
            )
        return sig

    async def get_behavioral_signature(
        self, character_id: str, session_id: str
    ) -> Optional[BehavioralSignature]:
        """Get behavioral signature for a character."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM behavioral_signatures
                WHERE character_id = $1 AND session_id = $2
                """,
                str(character_id),
                str(session_id),
            )
        if row:
            return self._row_to_signature(row)
        return None

    async def update_behavioral_signature(self, sig: BehavioralSignature) -> BehavioralSignature:
        """Update a behavioral signature."""
        sig.last_observed = datetime.utcnow()
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE behavioral_signatures
                SET vocabulary_patterns = $1, speech_quirks = $2, emotional_ranges = $3,
                    interaction_style = $4, confidence = $5, last_observed = $6
                WHERE signature_id = $7
                """,
                json.dumps(sig.vocabulary_patterns),
                json.dumps(sig.speech_quirks),
                json.dumps(sig.emotional_ranges),
                sig.interaction_style,
                sig.confidence,
                sig.last_observed,
                str(sig.signature_id),
            )
        return sig

    # ── Fact operations ──────────────────────────────────────

    async def create_fact(self, fact: Fact) -> Fact:
        """Create a new fact."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO facts
                (fact_id, session_id, category, subject, predicate, object, evidence,
                 confidence, active, created_at, embedding)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                str(fact.fact_id),
                str(fact.session_id),
                fact.category.value,
                fact.subject,
                fact.predicate,
                fact.object,
                fact.evidence,
                fact.confidence,
                fact.active,
                fact.created_at,
                json.dumps(fact.embedding) if fact.embedding else None,
            )
        return fact

    async def get_facts(
        self, session_id: str, active_only: bool = True
    ) -> List[Fact]:
        """Get facts for a session."""
        if active_only:
            query = "SELECT * FROM facts WHERE session_id = $1 AND active = TRUE"
        else:
            query = "SELECT * FROM facts WHERE session_id = $1"

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, str(session_id))

        facts = []
        for row in rows:
            embedding = row["embedding"]
            if embedding is not None and isinstance(embedding, str):
                embedding = json.loads(embedding)
            facts.append(
                Fact(
                    fact_id=UUID(row["fact_id"]),
                    session_id=UUID(row["session_id"]),
                    category=FactCategory(row["category"]),
                    subject=row["subject"],
                    predicate=row["predicate"],
                    object=row["object"],
                    evidence=row["evidence"],
                    confidence=row["confidence"],
                    active=row["active"],
                    created_at=row["created_at"],
                    embedding=embedding,
                )
            )
        return facts

    async def deactivate_fact(self, fact_id: str) -> None:
        """Deactivate a fact."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE facts SET active = FALSE WHERE fact_id = $1",
                fact_id,
            )

    # ── Event operations ─────────────────────────────────────

    async def create_event(self, event: Event) -> Event:
        """Create a new event."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO events
                (event_id, session_id, involved_characters, description,
                 emotional_impact, timestamp, session_turn)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                str(event.event_id),
                str(event.session_id),
                json.dumps([str(c) for c in event.involved_characters]),
                event.description,
                json.dumps({str(k): v for k, v in event.emotional_impact.items()}),
                event.timestamp,
                event.session_turn,
            )
        return event

    async def get_event(self, event_id: str) -> Optional[Event]:
        """Retrieve an event by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM events WHERE event_id = $1",
                event_id,
            )
        if row:
            return self._row_to_event(row)
        return None

    async def get_events(self, session_id: str) -> List[Event]:
        """Get all events in a session."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM events WHERE session_id = $1 ORDER BY session_turn ASC",
                str(session_id),
            )
        return [self._row_to_event(row) for row in rows]

    # ── Relationship operations ──────────────────────────────

    async def create_relationship(self, rel: RelationshipDynamic) -> RelationshipDynamic:
        """Create a new relationship."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO relationships
                (relationship_id, session_id, from_character, to_character, label,
                 trust_level, power_balance, emotional_undercurrent, history, last_interaction)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                str(rel.relationship_id),
                str(rel.session_id),
                str(rel.from_character),
                str(rel.to_character),
                rel.label,
                rel.trust_level,
                rel.power_balance,
                rel.emotional_undercurrent,
                rel.history,
                rel.last_interaction,
            )
        return rel

    async def get_relationship(
        self, from_char: str, to_char: str, session_id: str
    ) -> Optional[RelationshipDynamic]:
        """Get relationship between two characters."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM relationships
                WHERE session_id = $1 AND from_character = $2 AND to_character = $3
                """,
                str(session_id),
                str(from_char),
                str(to_char),
            )
        if row:
            return RelationshipDynamic(
                relationship_id=UUID(row["relationship_id"]),
                session_id=UUID(row["session_id"]),
                from_character=UUID(row["from_character"]),
                to_character=UUID(row["to_character"]),
                label=row["label"],
                trust_level=row["trust_level"],
                power_balance=row["power_balance"],
                emotional_undercurrent=row["emotional_undercurrent"],
                history=row["history"],
                last_interaction=row["last_interaction"],
            )
        return None

    async def get_relationships(self, session_id: str) -> List[RelationshipDynamic]:
        """Get all relationships in a session."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM relationships WHERE session_id = $1",
                str(session_id),
            )
        rels = []
        for row in rows:
            rels.append(
                RelationshipDynamic(
                    relationship_id=UUID(row["relationship_id"]),
                    session_id=UUID(row["session_id"]),
                    from_character=UUID(row["from_character"]),
                    to_character=UUID(row["to_character"]),
                    label=row["label"],
                    trust_level=row["trust_level"],
                    power_balance=row["power_balance"],
                    emotional_undercurrent=row["emotional_undercurrent"],
                    history=row["history"],
                    last_interaction=row["last_interaction"],
                )
            )
        return rels

    async def update_relationship(self, rel: RelationshipDynamic) -> RelationshipDynamic:
        """Update an existing relationship."""
        rel.last_interaction = datetime.utcnow()
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE relationships
                SET label = $1, trust_level = $2, power_balance = $3,
                    emotional_undercurrent = $4, history = $5, last_interaction = $6
                WHERE relationship_id = $7
                """,
                rel.label,
                rel.trust_level,
                rel.power_balance,
                rel.emotional_undercurrent,
                rel.history,
                rel.last_interaction,
                str(rel.relationship_id),
            )
        return rel

    # ── Narrative Arc operations ─────────────────────────────

    async def create_narrative_arc(self, arc: NarrativeArc) -> NarrativeArc:
        """Create a new narrative arc."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO narrative_arcs
                (arc_id, session_id, title, involved_characters, current_status,
                 beats, expected_outcome)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                str(arc.arc_id),
                str(arc.session_id),
                arc.title,
                json.dumps([str(c) for c in arc.involved_characters]),
                arc.current_status.value,
                json.dumps(arc.beats),
                arc.expected_outcome,
            )
        return arc

    async def get_narrative_arcs(self, session_id: str) -> List[NarrativeArc]:
        """Get all narrative arcs in a session."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM narrative_arcs WHERE session_id = $1",
                str(session_id),
            )
        return [self._row_to_arc(row) for row in rows]

    async def update_narrative_arc(self, arc: NarrativeArc) -> NarrativeArc:
        """Update a narrative arc."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE narrative_arcs
                SET title = $1, involved_characters = $2, current_status = $3,
                    beats = $4, expected_outcome = $5
                WHERE arc_id = $6
                """,
                arc.title,
                json.dumps([str(c) for c in arc.involved_characters]),
                arc.current_status.value,
                json.dumps(arc.beats),
                arc.expected_outcome,
                str(arc.arc_id),
            )
        return arc

    # ── Drift Log operations ─────────────────────────────────

    async def create_drift_log(self, drift: DriftLog) -> DriftLog:
        """Create a new drift log entry."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO drift_logs
                (drift_id, character_id, session_id, inconsistency_type,
                 detected_in_message, previous_state, conflicting_state,
                 severity, resolution, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                str(drift.drift_id),
                str(drift.character_id) if drift.character_id else None,
                str(drift.session_id),
                drift.inconsistency_type.value,
                drift.detected_in_message,
                drift.previous_state,
                drift.conflicting_state,
                drift.severity.value,
                drift.resolution,
                drift.timestamp,
            )
        return drift

    async def get_drift_logs(
        self, session_id: str, character_id: Optional[str] = None
    ) -> List[DriftLog]:
        """Get drift logs for a session, optionally filtered by character."""
        async with self.pool.acquire() as conn:
            if character_id:
                rows = await conn.fetch(
                    """
                    SELECT * FROM drift_logs
                    WHERE session_id = $1 AND character_id = $2
                    ORDER BY timestamp DESC
                    """,
                    str(session_id),
                    str(character_id),
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM drift_logs WHERE session_id = $1 ORDER BY timestamp DESC",
                    str(session_id),
                )
        return [
            DriftLog(
                drift_id=UUID(row["drift_id"]),
                character_id=UUID(row["character_id"]) if row["character_id"] else None,
                session_id=UUID(row["session_id"]),
                inconsistency_type=InconsistencyType(row["inconsistency_type"]),
                detected_in_message=row["detected_in_message"],
                previous_state=row["previous_state"],
                conflicting_state=row["conflicting_state"],
                severity=DriftSeverity(row["severity"]),
                resolution=row["resolution"],
                timestamp=row["timestamp"],
            )
            for row in rows
        ]

    # ── Memory Snapshot operations ───────────────────────────

    async def create_snapshot(self, snapshot: MemorySnapshot) -> MemorySnapshot:
        """Create a memory snapshot."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO memory_snapshots
                (snapshot_id, session_id, timestamp, snapshot_data, created_by, notes)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                str(snapshot.snapshot_id),
                str(snapshot.session_id),
                snapshot.timestamp,
                json.dumps(snapshot.snapshot_data),
                snapshot.created_by,
                snapshot.notes,
            )
        return snapshot

    async def get_snapshot(self, snapshot_id: str) -> Optional[MemorySnapshot]:
        """Retrieve a snapshot by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM memory_snapshots WHERE snapshot_id = $1",
                snapshot_id,
            )
        if row:
            return self._row_to_snapshot(row)
        return None

    async def list_snapshots(self, session_id: str) -> List[MemorySnapshot]:
        """List all snapshots for a session."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM memory_snapshots WHERE session_id = $1 ORDER BY timestamp DESC",
                str(session_id),
            )
        return [self._row_to_snapshot(row) for row in rows]

    async def delete_oldest_snapshots(self, session_id: str, keep: int = 10) -> None:
        """Delete oldest snapshots beyond the keep limit."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT snapshot_id FROM memory_snapshots
                WHERE session_id = $1 ORDER BY timestamp DESC
                """,
                str(session_id),
            )
            if len(rows) > keep:
                to_delete = [row["snapshot_id"] for row in rows[keep:]]
                await conn.execute(
                    "DELETE FROM memory_snapshots WHERE snapshot_id = ANY($1::text[])",
                    to_delete,
                )

    # ── Bulk clear operations (for rollback) ─────────────────

    async def clear_session_characters(self, session_id: str) -> None:
        """Delete all characters for a session."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM characters WHERE session_id = $1",
                str(session_id),
            )

    async def clear_session_facts(self, session_id: str) -> None:
        """Delete all facts for a session."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM facts WHERE session_id = $1",
                str(session_id),
            )

    async def clear_session_relationships(self, session_id: str) -> None:
        """Delete all relationships for a session."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM relationships WHERE session_id = $1",
                str(session_id),
            )

    async def clear_session_events(self, session_id: str) -> None:
        """Delete all events for a session."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM events WHERE session_id = $1",
                str(session_id),
            )

    async def clear_session_narrative_arcs(self, session_id: str) -> None:
        """Delete all narrative arcs for a session."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM narrative_arcs WHERE session_id = $1",
                str(session_id),
            )

    async def clear_session_drift_logs(self, session_id: str) -> None:
        """Delete all drift logs for a session."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM drift_logs WHERE session_id = $1",
                str(session_id),
            )

    async def clear_session_character_states(self, session_id: str) -> None:
        """Delete all character states for a session."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM character_states WHERE session_id = $1",
                str(session_id),
            )

    async def clear_session_behavioral_signatures(self, session_id: str) -> None:
        """Delete all behavioral signatures for a session."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM behavioral_signatures WHERE session_id = $1",
                str(session_id),
            )

    # ── Embedding search ─────────────────────────────────────

    async def search_facts_by_embedding(
        self, session_id: str, query_embedding: List[float], limit: int = 10
    ) -> List[Fact]:
        """Search facts by cosine similarity to a query embedding."""
        facts = await self.get_facts(str(session_id), active_only=True)
        scored = []
        for fact in facts:
            if fact.embedding:
                sim = self._cosine_similarity(query_embedding, fact.embedding)
                scored.append((sim, fact))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [fact for _, fact in scored[:limit]]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
