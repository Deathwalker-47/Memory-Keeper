"""SQLite implementation of the memory store."""

import json
import math
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import aiosqlite

from memory_keeper.store.models import (
    Session,
    CharacterIdentity,
    CharacterTier,
    Fact,
    FactCategory,
    CharacterState,
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


class SQLiteStore:
    """SQLite-based implementation of memory store."""
    
    def __init__(self, db_path: str = "memory_keeper.db"):
        """Initialize store with database path."""
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None
    
    async def initialize(self) -> None:
        """Initialize database and create schema."""
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        
        # Create tables
        await self._create_schema()
    
    async def close(self) -> None:
        """Close database connection."""
        if self.conn:
            await self.conn.close()
    
    async def _create_schema(self) -> None:
        """Create database schema."""
        schema = """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            archived INTEGER DEFAULT 0,
            config TEXT DEFAULT '{}'
        );
        
        CREATE TABLE IF NOT EXISTS characters (
            character_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            name TEXT NOT NULL,
            tier TEXT DEFAULT 'primary',
            core_traits TEXT DEFAULT '[]',
            background TEXT,
            worldview TEXT,
            speech_patterns TEXT DEFAULT '{}',
            appearance TEXT,
            created_at TEXT NOT NULL,
            last_modified TEXT NOT NULL,
            active INTEGER DEFAULT 1,
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
            timestamp TEXT NOT NULL,
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
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            embedding TEXT,
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
            last_interaction TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id),
            FOREIGN KEY (from_character) REFERENCES characters(character_id),
            FOREIGN KEY (to_character) REFERENCES characters(character_id)
        );
        
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            involved_characters TEXT DEFAULT '[]',
            description TEXT NOT NULL,
            emotional_impact TEXT DEFAULT '{}',
            timestamp TEXT NOT NULL,
            session_turn INTEGER DEFAULT 0,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
        
        CREATE TABLE IF NOT EXISTS narrative_arcs (
            arc_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            title TEXT NOT NULL,
            involved_characters TEXT DEFAULT '[]',
            current_status TEXT DEFAULT 'setup',
            beats TEXT DEFAULT '[]',
            expected_outcome TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
        
        CREATE TABLE IF NOT EXISTS drift_logs (
            drift_id TEXT PRIMARY KEY,
            character_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            inconsistency_type TEXT NOT NULL,
            detected_in_message TEXT NOT NULL,
            previous_state TEXT NOT NULL,
            conflicting_state TEXT NOT NULL,
            severity TEXT DEFAULT 'minor',
            resolution TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (character_id) REFERENCES characters(character_id),
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
        
        CREATE TABLE IF NOT EXISTS memory_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            snapshot_data TEXT NOT NULL,
            created_by TEXT,
            notes TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
        
        CREATE TABLE IF NOT EXISTS behavioral_signatures (
            signature_id TEXT PRIMARY KEY,
            character_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            vocabulary_patterns TEXT DEFAULT '[]',
            speech_quirks TEXT DEFAULT '[]',
            emotional_ranges TEXT DEFAULT '{}',
            interaction_style TEXT,
            confidence REAL DEFAULT 0.5,
            last_observed TEXT NOT NULL,
            FOREIGN KEY (character_id) REFERENCES characters(character_id),
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_characters_session ON characters(session_id);
        CREATE INDEX IF NOT EXISTS idx_facts_session ON facts(session_id);
        CREATE INDEX IF NOT EXISTS idx_relationships_session ON relationships(session_id);
        CREATE INDEX IF NOT EXISTS idx_drift_logs_session ON drift_logs(session_id);
        """
        
        await self.conn.executescript(schema)
        await self.conn.commit()
    
    # Session operations
    async def create_session(self, session: Session) -> Session:
        """Create a new session."""
        await self.conn.execute(
            """
            INSERT INTO sessions (session_id, name, created_at, updated_at, config)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(session.session_id),
                session.name,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
                json.dumps(session.config),
            ),
        )
        await self.conn.commit()
        return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID."""
        cursor = await self.conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        if row:
            return Session(
                session_id=UUID(row["session_id"]),
                name=row["name"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                archived=bool(row["archived"]),
                config=json.loads(row["config"]),
            )
        return None
    
    async def list_sessions(self) -> List[Session]:
        """List all non-archived sessions."""
        cursor = await self.conn.execute(
            "SELECT * FROM sessions WHERE archived = 0 ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        return [
            Session(
                session_id=UUID(row["session_id"]),
                name=row["name"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                archived=bool(row["archived"]),
                config=json.loads(row["config"]),
            )
            for row in rows
        ]
    
    async def update_session(self, session: Session) -> Session:
        """Update an existing session."""
        session.updated_at = __import__("datetime").datetime.utcnow()
        await self.conn.execute(
            """
            UPDATE sessions SET name = ?, updated_at = ?, config = ?
            WHERE session_id = ?
            """,
            (
                session.name,
                session.updated_at.isoformat(),
                json.dumps(session.config),
                str(session.session_id),
            ),
        )
        await self.conn.commit()
        return session
    
    async def delete_session(self, session_id: str) -> None:
        """Soft delete a session."""
        await self.conn.execute(
            "UPDATE sessions SET archived = 1 WHERE session_id = ?",
            (session_id,),
        )
        await self.conn.commit()
    
    # Character operations
    async def create_character(self, character: CharacterIdentity) -> CharacterIdentity:
        """Create a new character."""
        await self.conn.execute(
            """
            INSERT INTO characters
            (character_id, session_id, name, tier, core_traits, background, worldview,
             speech_patterns, appearance, created_at, last_modified, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(character.character_id),
                str(character.session_id),
                character.name,
                character.tier.value,
                json.dumps(character.core_traits),
                character.background,
                character.worldview,
                character.speech_patterns.model_dump_json(),
                character.appearance,
                character.created_at.isoformat(),
                character.last_modified.isoformat(),
                int(character.active),
            ),
        )
        await self.conn.commit()
        return character
    
    async def get_character(self, character_id: str) -> Optional[CharacterIdentity]:
        """Retrieve a character by ID."""
        cursor = await self.conn.execute(
            "SELECT * FROM characters WHERE character_id = ?",
            (character_id,),
        )
        row = await cursor.fetchone()
        if row:
            return CharacterIdentity(
                character_id=UUID(row["character_id"]),
                session_id=UUID(row["session_id"]),
                name=row["name"],
                tier=CharacterTier(row["tier"]),
                core_traits=json.loads(row["core_traits"]),
                background=row["background"],
                worldview=row["worldview"],
                speech_patterns=__import__("json").loads(row["speech_patterns"]),
                appearance=row["appearance"],
                created_at=row["created_at"],
                last_modified=row["last_modified"],
                active=bool(row["active"]),
            )
        return None
    
    async def get_characters(self, session_id: str) -> List[CharacterIdentity]:
        """List all active characters in a session."""
        cursor = await self.conn.execute(
            "SELECT * FROM characters WHERE session_id = ? AND active = 1",
            (str(session_id),),
        )
        rows = await cursor.fetchall()
        characters = []
        for row in rows:
            characters.append(
                CharacterIdentity(
                    character_id=UUID(row["character_id"]),
                    session_id=UUID(row["session_id"]),
                    name=row["name"],
                    tier=CharacterTier(row["tier"]),
                    core_traits=json.loads(row["core_traits"]),
                    background=row["background"],
                    worldview=row["worldview"],
                    speech_patterns=__import__("json").loads(row["speech_patterns"]),
                    appearance=row["appearance"],
                    created_at=row["created_at"],
                    last_modified=row["last_modified"],
                    active=bool(row["active"]),
                )
            )
        return characters
    
    async def find_character_by_name(
        self, session_id: str, name: str
    ) -> Optional[CharacterIdentity]:
        """Find a character by name (case-insensitive)."""
        cursor = await self.conn.execute(
            "SELECT * FROM characters WHERE session_id = ? AND LOWER(name) = LOWER(?)",
            (str(session_id), name),
        )
        row = await cursor.fetchone()
        if row:
            return CharacterIdentity(
                character_id=UUID(row["character_id"]),
                session_id=UUID(row["session_id"]),
                name=row["name"],
                tier=CharacterTier(row["tier"]),
                core_traits=json.loads(row["core_traits"]),
                background=row["background"],
                worldview=row["worldview"],
                speech_patterns=__import__("json").loads(row["speech_patterns"]),
                appearance=row["appearance"],
                created_at=row["created_at"],
                last_modified=row["last_modified"],
                active=bool(row["active"]),
            )
        return None
    
    # Fact operations
    async def create_fact(self, fact: Fact) -> Fact:
        """Create a new fact."""
        await self.conn.execute(
            """
            INSERT INTO facts
            (fact_id, session_id, category, subject, predicate, object, evidence,
             confidence, active, created_at, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(fact.fact_id),
                str(fact.session_id),
                fact.category.value,
                fact.subject,
                fact.predicate,
                fact.object,
                fact.evidence,
                fact.confidence,
                int(fact.active),
                fact.created_at.isoformat(),
                json.dumps(fact.embedding) if fact.embedding else None,
            ),
        )
        await self.conn.commit()
        return fact
    
    async def get_facts(
        self, session_id: str, active_only: bool = True
    ) -> List[Fact]:
        """Get facts for a session."""
        query = "SELECT * FROM facts WHERE session_id = ?"
        params = [str(session_id)]
        
        if active_only:
            query += " AND active = 1"
        
        cursor = await self.conn.execute(query, params)
        rows = await cursor.fetchall()
        
        facts = []
        for row in rows:
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
                    active=bool(row["active"]),
                    created_at=row["created_at"],
                    embedding=json.loads(row["embedding"]) if row["embedding"] else None,
                )
            )
        return facts
    
    async def deactivate_fact(self, fact_id: str) -> None:
        """Deactivate a fact."""
        await self.conn.execute(
            "UPDATE facts SET active = 0 WHERE fact_id = ?",
            (fact_id,),
        )
        await self.conn.commit()
    
    # Relationship operations
    async def create_relationship(self, rel: RelationshipDynamic) -> RelationshipDynamic:
        """Create a new relationship."""
        await self.conn.execute(
            """
            INSERT INTO relationships
            (relationship_id, session_id, from_character, to_character, label,
             trust_level, power_balance, emotional_undercurrent, history, last_interaction)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(rel.relationship_id),
                str(rel.session_id),
                str(rel.from_character),
                str(rel.to_character),
                rel.label,
                rel.trust_level,
                rel.power_balance,
                rel.emotional_undercurrent,
                rel.history,
                rel.last_interaction.isoformat(),
            ),
        )
        await self.conn.commit()
        return rel
    
    async def get_relationship(
        self, from_char: str, to_char: str, session_id: str
    ) -> Optional[RelationshipDynamic]:
        """Get relationship between two characters."""
        cursor = await self.conn.execute(
            """
            SELECT * FROM relationships
            WHERE session_id = ? AND from_character = ? AND to_character = ?
            """,
            (str(session_id), str(from_char), str(to_char)),
        )
        row = await cursor.fetchone()
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
        cursor = await self.conn.execute(
            "SELECT * FROM relationships WHERE session_id = ?",
            (str(session_id),),
        )
        rows = await cursor.fetchall()
        
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
    
    # Character state operations
    async def upsert_character_state(self, state: CharacterState) -> CharacterState:
        """Insert or update character state."""
        existing = await self.get_character_state(
            str(state.character_id), str(state.session_id)
        )
        
        if existing:
            await self.conn.execute(
                """
                UPDATE character_states
                SET mood = ?, location = ?, current_goal = ?, recent_memory = ?, timestamp = ?
                WHERE character_id = ? AND session_id = ?
                """,
                (
                    state.mood,
                    state.location,
                    state.current_goal,
                    state.recent_memory,
                    state.timestamp.isoformat(),
                    str(state.character_id),
                    str(state.session_id),
                ),
            )
        else:
            await self.conn.execute(
                """
                INSERT INTO character_states
                (state_id, character_id, session_id, mood, location, current_goal,
                 recent_memory, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(state.state_id),
                    str(state.character_id),
                    str(state.session_id),
                    state.mood,
                    state.location,
                    state.current_goal,
                    state.recent_memory,
                    state.timestamp.isoformat(),
                ),
            )
        
        await self.conn.commit()
        return state
    
    async def get_character_state(
        self, character_id: str, session_id: str
    ) -> Optional[CharacterState]:
        """Get current state of a character."""
        cursor = await self.conn.execute(
            """
            SELECT * FROM character_states
            WHERE character_id = ? AND session_id = ?
            ORDER BY timestamp DESC LIMIT 1
            """,
            (character_id, session_id),
        )
        row = await cursor.fetchone()
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

    # Character update
    async def update_character(self, character: CharacterIdentity) -> CharacterIdentity:
        """Update an existing character."""
        character.last_modified = datetime.utcnow()
        await self.conn.execute(
            """
            UPDATE characters
            SET name = ?, tier = ?, core_traits = ?, background = ?, worldview = ?,
                speech_patterns = ?, appearance = ?, last_modified = ?, active = ?
            WHERE character_id = ?
            """,
            (
                character.name,
                character.tier.value,
                json.dumps(character.core_traits),
                character.background,
                character.worldview,
                character.speech_patterns.model_dump_json(),
                character.appearance,
                character.last_modified.isoformat(),
                int(character.active),
                str(character.character_id),
            ),
        )
        await self.conn.commit()
        return character

    # Relationship update
    async def update_relationship(self, rel: RelationshipDynamic) -> RelationshipDynamic:
        """Update an existing relationship."""
        rel.last_interaction = datetime.utcnow()
        await self.conn.execute(
            """
            UPDATE relationships
            SET label = ?, trust_level = ?, power_balance = ?,
                emotional_undercurrent = ?, history = ?, last_interaction = ?
            WHERE relationship_id = ?
            """,
            (
                rel.label,
                rel.trust_level,
                rel.power_balance,
                rel.emotional_undercurrent,
                rel.history,
                rel.last_interaction.isoformat(),
                str(rel.relationship_id),
            ),
        )
        await self.conn.commit()
        return rel

    # Event operations
    async def create_event(self, event: Event) -> Event:
        """Create a new event."""
        await self.conn.execute(
            """
            INSERT INTO events
            (event_id, session_id, involved_characters, description,
             emotional_impact, timestamp, session_turn)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(event.event_id),
                str(event.session_id),
                json.dumps([str(c) for c in event.involved_characters]),
                event.description,
                json.dumps({str(k): v for k, v in event.emotional_impact.items()}),
                event.timestamp.isoformat(),
                event.session_turn,
            ),
        )
        await self.conn.commit()
        return event

    async def get_event(self, event_id: str) -> Optional[Event]:
        """Retrieve an event by ID."""
        cursor = await self.conn.execute(
            "SELECT * FROM events WHERE event_id = ?", (event_id,)
        )
        row = await cursor.fetchone()
        if row:
            return self._row_to_event(row)
        return None

    async def get_events(self, session_id: str) -> List[Event]:
        """Get all events in a session."""
        cursor = await self.conn.execute(
            "SELECT * FROM events WHERE session_id = ? ORDER BY session_turn ASC",
            (str(session_id),),
        )
        rows = await cursor.fetchall()
        return [self._row_to_event(row) for row in rows]

    def _row_to_event(self, row) -> Event:
        """Convert a database row to an Event model."""
        return Event(
            event_id=UUID(row["event_id"]),
            session_id=UUID(row["session_id"]),
            involved_characters=[UUID(c) for c in json.loads(row["involved_characters"])],
            description=row["description"],
            emotional_impact={
                UUID(k): v for k, v in json.loads(row["emotional_impact"]).items()
            },
            timestamp=row["timestamp"],
            session_turn=row["session_turn"],
        )

    # Narrative arc operations
    async def create_narrative_arc(self, arc: NarrativeArc) -> NarrativeArc:
        """Create a new narrative arc."""
        await self.conn.execute(
            """
            INSERT INTO narrative_arcs
            (arc_id, session_id, title, involved_characters, current_status,
             beats, expected_outcome)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(arc.arc_id),
                str(arc.session_id),
                arc.title,
                json.dumps([str(c) for c in arc.involved_characters]),
                arc.current_status.value,
                json.dumps(arc.beats),
                arc.expected_outcome,
            ),
        )
        await self.conn.commit()
        return arc

    async def get_narrative_arcs(self, session_id: str) -> List[NarrativeArc]:
        """Get all narrative arcs in a session."""
        cursor = await self.conn.execute(
            "SELECT * FROM narrative_arcs WHERE session_id = ?",
            (str(session_id),),
        )
        rows = await cursor.fetchall()
        return [self._row_to_arc(row) for row in rows]

    async def update_narrative_arc(self, arc: NarrativeArc) -> NarrativeArc:
        """Update a narrative arc."""
        await self.conn.execute(
            """
            UPDATE narrative_arcs
            SET title = ?, involved_characters = ?, current_status = ?,
                beats = ?, expected_outcome = ?
            WHERE arc_id = ?
            """,
            (
                arc.title,
                json.dumps([str(c) for c in arc.involved_characters]),
                arc.current_status.value,
                json.dumps(arc.beats),
                arc.expected_outcome,
                str(arc.arc_id),
            ),
        )
        await self.conn.commit()
        return arc

    def _row_to_arc(self, row) -> NarrativeArc:
        """Convert a database row to a NarrativeArc model."""
        return NarrativeArc(
            arc_id=UUID(row["arc_id"]),
            session_id=UUID(row["session_id"]),
            title=row["title"],
            involved_characters=[UUID(c) for c in json.loads(row["involved_characters"])],
            current_status=ArcStatus(row["current_status"]),
            beats=json.loads(row["beats"]),
            expected_outcome=row["expected_outcome"],
        )

    # Drift log operations
    async def create_drift_log(self, drift: DriftLog) -> DriftLog:
        """Create a new drift log entry."""
        await self.conn.execute(
            """
            INSERT INTO drift_logs
            (drift_id, character_id, session_id, inconsistency_type,
             detected_in_message, previous_state, conflicting_state,
             severity, resolution, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(drift.drift_id),
                str(drift.character_id),
                str(drift.session_id),
                drift.inconsistency_type.value,
                drift.detected_in_message,
                drift.previous_state,
                drift.conflicting_state,
                drift.severity.value,
                drift.resolution,
                drift.timestamp.isoformat(),
            ),
        )
        await self.conn.commit()
        return drift

    async def get_drift_logs(
        self, session_id: str, character_id: Optional[str] = None
    ) -> List[DriftLog]:
        """Get drift logs for a session, optionally filtered by character."""
        query = "SELECT * FROM drift_logs WHERE session_id = ?"
        params: list = [str(session_id)]

        if character_id:
            query += " AND character_id = ?"
            params.append(str(character_id))

        query += " ORDER BY timestamp DESC"
        cursor = await self.conn.execute(query, params)
        rows = await cursor.fetchall()
        return [
            DriftLog(
                drift_id=UUID(row["drift_id"]),
                character_id=UUID(row["character_id"]),
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

    # Behavioral signature operations
    async def create_behavioral_signature(self, sig: BehavioralSignature) -> BehavioralSignature:
        """Create a new behavioral signature."""
        await self.conn.execute(
            """
            INSERT INTO behavioral_signatures
            (signature_id, character_id, session_id, vocabulary_patterns,
             speech_quirks, emotional_ranges, interaction_style, confidence, last_observed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(sig.signature_id),
                str(sig.character_id),
                str(sig.session_id),
                json.dumps(sig.vocabulary_patterns),
                json.dumps(sig.speech_quirks),
                json.dumps(sig.emotional_ranges),
                sig.interaction_style,
                sig.confidence,
                sig.last_observed.isoformat(),
            ),
        )
        await self.conn.commit()
        return sig

    async def get_behavioral_signature(
        self, character_id: str, session_id: str
    ) -> Optional[BehavioralSignature]:
        """Get behavioral signature for a character."""
        cursor = await self.conn.execute(
            """
            SELECT * FROM behavioral_signatures
            WHERE character_id = ? AND session_id = ?
            """,
            (str(character_id), str(session_id)),
        )
        row = await cursor.fetchone()
        if row:
            return self._row_to_signature(row)
        return None

    async def update_behavioral_signature(self, sig: BehavioralSignature) -> BehavioralSignature:
        """Update a behavioral signature."""
        sig.last_observed = datetime.utcnow()
        await self.conn.execute(
            """
            UPDATE behavioral_signatures
            SET vocabulary_patterns = ?, speech_quirks = ?, emotional_ranges = ?,
                interaction_style = ?, confidence = ?, last_observed = ?
            WHERE signature_id = ?
            """,
            (
                json.dumps(sig.vocabulary_patterns),
                json.dumps(sig.speech_quirks),
                json.dumps(sig.emotional_ranges),
                sig.interaction_style,
                sig.confidence,
                sig.last_observed.isoformat(),
                str(sig.signature_id),
            ),
        )
        await self.conn.commit()
        return sig

    def _row_to_signature(self, row) -> BehavioralSignature:
        """Convert a database row to a BehavioralSignature model."""
        return BehavioralSignature(
            signature_id=UUID(row["signature_id"]),
            character_id=UUID(row["character_id"]),
            session_id=UUID(row["session_id"]),
            vocabulary_patterns=json.loads(row["vocabulary_patterns"]),
            speech_quirks=json.loads(row["speech_quirks"]),
            emotional_ranges=json.loads(row["emotional_ranges"]),
            interaction_style=row["interaction_style"],
            confidence=row["confidence"],
            last_observed=row["last_observed"],
        )

    # Memory snapshot operations
    async def create_snapshot(self, snapshot: MemorySnapshot) -> MemorySnapshot:
        """Create a memory snapshot."""
        await self.conn.execute(
            """
            INSERT INTO memory_snapshots
            (snapshot_id, session_id, timestamp, snapshot_data, created_by, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(snapshot.snapshot_id),
                str(snapshot.session_id),
                snapshot.timestamp.isoformat(),
                json.dumps(snapshot.snapshot_data),
                snapshot.created_by,
                snapshot.notes,
            ),
        )
        await self.conn.commit()
        return snapshot

    async def get_snapshot(self, snapshot_id: str) -> Optional[MemorySnapshot]:
        """Retrieve a snapshot by ID."""
        cursor = await self.conn.execute(
            "SELECT * FROM memory_snapshots WHERE snapshot_id = ?",
            (snapshot_id,),
        )
        row = await cursor.fetchone()
        if row:
            return self._row_to_snapshot(row)
        return None

    async def list_snapshots(self, session_id: str) -> List[MemorySnapshot]:
        """List all snapshots for a session."""
        cursor = await self.conn.execute(
            "SELECT * FROM memory_snapshots WHERE session_id = ? ORDER BY timestamp DESC",
            (str(session_id),),
        )
        rows = await cursor.fetchall()
        return [self._row_to_snapshot(row) for row in rows]

    def _row_to_snapshot(self, row) -> MemorySnapshot:
        """Convert a database row to a MemorySnapshot model."""
        return MemorySnapshot(
            snapshot_id=UUID(row["snapshot_id"]),
            session_id=UUID(row["session_id"]),
            timestamp=row["timestamp"],
            snapshot_data=json.loads(row["snapshot_data"]),
            created_by=row["created_by"],
            notes=row["notes"],
        )

    async def delete_oldest_snapshots(self, session_id: str, keep: int = 10) -> None:
        """Delete oldest snapshots beyond the keep limit."""
        cursor = await self.conn.execute(
            """
            SELECT snapshot_id FROM memory_snapshots
            WHERE session_id = ? ORDER BY timestamp DESC
            """,
            (str(session_id),),
        )
        rows = await cursor.fetchall()
        if len(rows) > keep:
            to_delete = [row["snapshot_id"] for row in rows[keep:]]
            placeholders = ",".join("?" * len(to_delete))
            await self.conn.execute(
                f"DELETE FROM memory_snapshots WHERE snapshot_id IN ({placeholders})",
                to_delete,
            )
            await self.conn.commit()

    # Embedding search
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
