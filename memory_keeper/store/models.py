"""Pydantic models for Memory Keeper entities."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CharacterTier(str, Enum):
    """Character tier classification."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    NPC = "npc"


class FactCategory(str, Enum):
    """Fact category classification."""
    WORLD = "world"
    CHARACTER = "character"
    RELATIONSHIP = "relationship"
    PLOT = "plot"


class DriftSeverity(str, Enum):
    """Severity of detected character drift."""
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"


class InconsistencyType(str, Enum):
    """Type of character inconsistency."""
    TRAIT = "trait"
    RELATIONSHIP = "relationship"
    KNOWLEDGE = "knowledge"
    BEHAVIOR = "behavior"


class ArcStatus(str, Enum):
    """Status of narrative arc."""
    SETUP = "setup"
    DEVELOPMENT = "development"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    CLOSED = "closed"


class SpeechPatterns(BaseModel):
    """Character speech pattern details."""
    vocabulary_level: Optional[str] = Field(None, description="e.g., educated, casual, technical")
    quirks: List[str] = Field(default_factory=list, description="Catchphrases and mannerisms")
    avoids: List[str] = Field(default_factory=list, description="Words/topics they avoid")
    favored_expressions: List[str] = Field(default_factory=list, description="Common expressions")


class Session(BaseModel):
    """Root container for a roleplay scenario."""
    session_id: UUID = Field(default_factory=uuid4)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    archived: bool = False
    config: Dict[str, Any] = Field(default_factory=dict)


class CharacterIdentity(BaseModel):
    """Core definition of a character."""
    character_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    name: str
    tier: CharacterTier = CharacterTier.PRIMARY
    core_traits: List[str] = Field(default_factory=list)
    background: Optional[str] = None
    worldview: Optional[str] = None
    speech_patterns: SpeechPatterns = Field(default_factory=SpeechPatterns)
    appearance: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_modified: datetime = Field(default_factory=datetime.utcnow)
    active: bool = True


class BehavioralSignature(BaseModel):
    """Character behavioral patterns and voice."""
    signature_id: UUID = Field(default_factory=uuid4)
    character_id: UUID
    session_id: UUID
    vocabulary_patterns: List[str] = Field(default_factory=list)
    speech_quirks: List[str] = Field(default_factory=list)
    emotional_ranges: Dict[str, List[str]] = Field(default_factory=dict)
    interaction_style: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    last_observed: datetime = Field(default_factory=datetime.utcnow)


class CharacterState(BaseModel):
    """Current moment-to-moment state of a character."""
    state_id: UUID = Field(default_factory=uuid4)
    character_id: UUID
    session_id: UUID
    mood: Optional[str] = None
    location: Optional[str] = None
    current_goal: Optional[str] = None
    recent_memory: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Fact(BaseModel):
    """World or character fact in the scenario."""
    fact_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    category: FactCategory
    subject: str
    predicate: str
    object: str
    evidence: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    embedding: Optional[List[float]] = None


class Event(BaseModel):
    """Significant narrative event."""
    event_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    involved_characters: List[UUID] = Field(default_factory=list)
    description: str
    emotional_impact: Dict[UUID, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_turn: int = 0


class RelationshipDynamic(BaseModel):
    """Relationship between two characters."""
    relationship_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    from_character: UUID
    to_character: UUID
    label: str
    trust_level: float = Field(default=0.0, ge=-1.0, le=1.0)
    power_balance: float = Field(default=0.0, ge=-1.0, le=1.0)
    emotional_undercurrent: Optional[str] = None
    history: Optional[str] = None
    last_interaction: datetime = Field(default_factory=datetime.utcnow)


class NarrativeArc(BaseModel):
    """High-level story structure."""
    arc_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    title: str
    involved_characters: List[UUID] = Field(default_factory=list)
    current_status: ArcStatus = ArcStatus.SETUP
    beats: List[str] = Field(default_factory=list)
    expected_outcome: Optional[str] = None


class DriftLog(BaseModel):
    """Record of detected character inconsistencies."""
    drift_id: UUID = Field(default_factory=uuid4)
    character_id: UUID
    session_id: UUID
    inconsistency_type: InconsistencyType
    detected_in_message: str
    previous_state: str
    conflicting_state: str
    severity: DriftSeverity = DriftSeverity.MINOR
    resolution: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MemorySnapshot(BaseModel):
    """Point-in-time backup of session state."""
    snapshot_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    snapshot_data: Dict[str, Any]
    created_by: Optional[str] = None
    notes: Optional[str] = None
