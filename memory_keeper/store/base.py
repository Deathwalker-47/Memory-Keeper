"""Abstract base for memory store backends."""

from abc import ABC, abstractmethod
from typing import List, Optional

from memory_keeper.store.models import (
    Session,
    CharacterIdentity,
    CharacterState,
    NarratorState,
    Fact,
    RelationshipDynamic,
    Event,
    NarrativeArc,
    DriftLog,
    BehavioralSignature,
    MemorySnapshot,
)


class BaseStore(ABC):
    """Abstract interface that every store backend must implement."""

    @abstractmethod
    async def initialize(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    # ── Session ──────────────────────────────────────────────

    @abstractmethod
    async def create_session(self, session: Session) -> Session: ...

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Session]: ...

    @abstractmethod
    async def list_sessions(self) -> List[Session]: ...

    @abstractmethod
    async def update_session(self, session: Session) -> Session: ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> None: ...

    @abstractmethod
    async def increment_message_count(self, session_id: str) -> int: ...

    # ── Character ────────────────────────────────────────────

    @abstractmethod
    async def create_character(self, character: CharacterIdentity) -> CharacterIdentity: ...

    @abstractmethod
    async def get_character(self, character_id: str) -> Optional[CharacterIdentity]: ...

    @abstractmethod
    async def get_characters(self, session_id: str) -> List[CharacterIdentity]: ...

    @abstractmethod
    async def find_character_by_name(self, session_id: str, name: str) -> Optional[CharacterIdentity]: ...

    @abstractmethod
    async def update_character(self, character: CharacterIdentity) -> CharacterIdentity: ...

    # ── Character State ──────────────────────────────────────

    @abstractmethod
    async def upsert_character_state(self, state: CharacterState) -> CharacterState: ...

    @abstractmethod
    async def get_character_state(self, character_id: str, session_id: str) -> Optional[CharacterState]: ...

    # ── Narrator State ───────────────────────────────────────

    @abstractmethod
    async def upsert_narrator_state(self, state: NarratorState) -> NarratorState: ...

    @abstractmethod
    async def get_narrator_state(self, session_id: str) -> Optional[NarratorState]: ...

    @abstractmethod
    async def clear_session_narrator_states(self, session_id: str) -> None: ...

    # ── Behavioral Signature ─────────────────────────────────

    @abstractmethod
    async def create_behavioral_signature(self, sig: BehavioralSignature) -> BehavioralSignature: ...

    @abstractmethod
    async def get_behavioral_signature(self, character_id: str, session_id: str) -> Optional[BehavioralSignature]: ...

    @abstractmethod
    async def update_behavioral_signature(self, sig: BehavioralSignature) -> BehavioralSignature: ...

    # ── Fact ─────────────────────────────────────────────────

    @abstractmethod
    async def create_fact(self, fact: Fact) -> Fact: ...

    @abstractmethod
    async def get_facts(self, session_id: str, active_only: bool = True) -> List[Fact]: ...

    @abstractmethod
    async def deactivate_fact(self, fact_id: str) -> None: ...

    # ── Event ────────────────────────────────────────────────

    @abstractmethod
    async def create_event(self, event: Event) -> Event: ...

    @abstractmethod
    async def get_event(self, event_id: str) -> Optional[Event]: ...

    @abstractmethod
    async def get_events(self, session_id: str) -> List[Event]: ...

    # ── Relationship ─────────────────────────────────────────

    @abstractmethod
    async def create_relationship(self, rel: RelationshipDynamic) -> RelationshipDynamic: ...

    @abstractmethod
    async def get_relationship(self, from_char: str, to_char: str, session_id: str) -> Optional[RelationshipDynamic]: ...

    @abstractmethod
    async def get_relationships(self, session_id: str) -> List[RelationshipDynamic]: ...

    @abstractmethod
    async def update_relationship(self, rel: RelationshipDynamic) -> RelationshipDynamic: ...

    # ── Narrative Arc ────────────────────────────────────────

    @abstractmethod
    async def create_narrative_arc(self, arc: NarrativeArc) -> NarrativeArc: ...

    @abstractmethod
    async def get_narrative_arc(self, arc_id: str) -> Optional[NarrativeArc]: ...

    @abstractmethod
    async def get_narrative_arcs(self, session_id: str) -> List[NarrativeArc]: ...

    @abstractmethod
    async def update_narrative_arc(self, arc: NarrativeArc) -> NarrativeArc: ...

    # ── Drift Log ────────────────────────────────────────────

    @abstractmethod
    async def create_drift_log(self, drift: DriftLog) -> DriftLog: ...

    @abstractmethod
    async def get_drift_logs(self, session_id: str, character_id: Optional[str] = None) -> List[DriftLog]: ...

    # ── Snapshot ─────────────────────────────────────────────

    @abstractmethod
    async def create_snapshot(self, snapshot: MemorySnapshot) -> MemorySnapshot: ...

    @abstractmethod
    async def get_snapshot(self, snapshot_id: str) -> Optional[MemorySnapshot]: ...

    @abstractmethod
    async def list_snapshots(self, session_id: str) -> List[MemorySnapshot]: ...

    @abstractmethod
    async def delete_oldest_snapshots(self, session_id: str, keep: int = 10) -> None: ...

    # ── Bulk clear (rollback) ────────────────────────────────

    @abstractmethod
    async def clear_session_characters(self, session_id: str) -> None: ...

    @abstractmethod
    async def clear_session_facts(self, session_id: str) -> None: ...

    @abstractmethod
    async def clear_session_relationships(self, session_id: str) -> None: ...

    @abstractmethod
    async def clear_session_events(self, session_id: str) -> None: ...

    @abstractmethod
    async def clear_session_narrative_arcs(self, session_id: str) -> None: ...

    @abstractmethod
    async def clear_session_drift_logs(self, session_id: str) -> None: ...

    @abstractmethod
    async def clear_session_character_states(self, session_id: str) -> None: ...

    @abstractmethod
    async def clear_session_behavioral_signatures(self, session_id: str) -> None: ...

    async def clear_session_data(self, session_id: str) -> None:
        """Clear all entity data for a session (used during rollback)."""
        await self.clear_session_character_states(session_id)
        await self.clear_session_behavioral_signatures(session_id)
        await self.clear_session_narrator_states(session_id)
        await self.clear_session_drift_logs(session_id)
        await self.clear_session_events(session_id)
        await self.clear_session_narrative_arcs(session_id)
        await self.clear_session_relationships(session_id)
        await self.clear_session_facts(session_id)
        await self.clear_session_characters(session_id)

    # ── Embedding search ─────────────────────────────────────

    @abstractmethod
    async def search_facts_by_embedding(
        self, session_id: str, query_embedding: List[float], limit: int = 10
    ) -> List[Fact]: ...
