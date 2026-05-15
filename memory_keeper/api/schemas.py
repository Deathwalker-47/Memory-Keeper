"""API request/response schemas."""

from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# --- Session schemas ---

class SessionCreate(BaseModel):
    name: str
    config: Dict[str, Any] = Field(default_factory=dict)


class SessionUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


# --- Character schemas ---

class SpeechPatternsInput(BaseModel):
    vocabulary_level: Optional[str] = None
    quirks: List[str] = Field(default_factory=list)
    avoids: List[str] = Field(default_factory=list)
    favored_expressions: List[str] = Field(default_factory=list)


class CharacterCreate(BaseModel):
    name: str
    tier: str = "primary"
    core_traits: List[str] = Field(default_factory=list)
    background: Optional[str] = None
    worldview: Optional[str] = None
    speech_patterns: SpeechPatternsInput = Field(default_factory=SpeechPatternsInput)
    appearance: Optional[str] = None


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    tier: Optional[str] = None
    core_traits: Optional[List[str]] = None
    background: Optional[str] = None
    worldview: Optional[str] = None
    appearance: Optional[str] = None


# --- Fact schemas ---

class FactCreate(BaseModel):
    category: str
    subject: str
    predicate: str
    object: str
    evidence: Optional[str] = None
    confidence: float = 0.5


# --- Relationship schemas ---

class RelationshipCreate(BaseModel):
    from_character: str  # character_id as string
    to_character: str
    label: str
    trust_level: float = 0.0
    power_balance: float = 0.0
    emotional_undercurrent: Optional[str] = None
    history: Optional[str] = None


# --- Message schemas ---

class MessageRequest(BaseModel):
    character_name: str
    message_content: str


class MessageResponse(BaseModel):
    session_id: str
    character_name: str
    memory_context: str
    extraction_status: str = "processing"


# --- Memory context schemas ---

class MemoryContextResponse(BaseModel):
    context: str
    character_name: str
    facts_count: int = 0
    relationships_count: int = 0


# --- Snapshot schemas ---

class SnapshotCreate(BaseModel):
    notes: Optional[str] = None
    created_by: Optional[str] = None


# --- Narrative Arc schemas ---

class ArcCreate(BaseModel):
    title: str
    involved_characters: List[str] = Field(default_factory=list, description="Character IDs")
    current_status: str = "setup"
    beats: List[str] = Field(default_factory=list)
    expected_outcome: Optional[str] = None


class ArcUpdate(BaseModel):
    title: Optional[str] = None
    current_status: Optional[str] = None
    beats: Optional[List[str]] = None
    expected_outcome: Optional[str] = None


# --- Search schemas ---

class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=100)


class SearchResult(BaseModel):
    fact_id: str
    subject: str
    predicate: str
    object: str
    confidence: float
    similarity: float


# --- Drift schemas ---

class DriftCheckRequest(BaseModel):
    character_name: str
    message_content: str
