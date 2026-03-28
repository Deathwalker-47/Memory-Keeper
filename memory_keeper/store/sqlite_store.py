"""SQLite implementation of the memory store."""

import json
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
    DriftLog,
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
                character.speech_patterns.json(),
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
