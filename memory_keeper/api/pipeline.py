"""Message processing pipeline — the core orchestration layer."""

import asyncio
import logging
from typing import Optional
from uuid import UUID

from memory_keeper.analyzer.llm_client import LLMClient
from memory_keeper.analyzer.character_analyzer import identify_characters, extract_character_info
from memory_keeper.analyzer.fact_extractor import extract_facts
from memory_keeper.analyzer.relationship_extractor import extract_relationships
from memory_keeper.analyzer.drift_detector import detect_drift
from memory_keeper.api.context_formatter import format_memory_context
from memory_keeper.config import AnalyzerConfig
from memory_keeper.store.models import (
    CharacterIdentity,
    CharacterTier,
    SpeechPatterns,
    Fact,
    FactCategory,
    RelationshipDynamic,
    CharacterState,
    DriftLog,
    DriftSeverity,
    InconsistencyType,
    MemorySnapshot,
)
from memory_keeper.store.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class MessagePipeline:
    """Orchestrates the full message processing flow.

    Sync retrieval → return context → async extraction + drift analysis.
    """

    def __init__(
        self,
        store: SQLiteStore,
        llm_client: Optional[LLMClient],
        analyzer_config: AnalyzerConfig,
    ):
        self.store = store
        self.llm_client = llm_client
        self.analyzer_config = analyzer_config

    async def process_message(
        self, session_id: str, character_name: str, message_content: str
    ) -> dict:
        """Process a message through the full pipeline.

        1. Look up or create character
        2. Retrieve relevant memory context (sync)
        3. Launch async extraction + drift analysis tasks
        4. Return context immediately
        """
        session = await self.store.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Find or auto-create character
        character = await self.store.find_character_by_name(session_id, character_name)
        if not character:
            character = CharacterIdentity(
                session_id=UUID(session_id),
                name=character_name,
                tier=CharacterTier.SECONDARY,
            )
            await self.store.create_character(character)

        # SYNC: Retrieve memory context
        context = await self._build_context(session_id, character)

        # ASYNC: Launch extraction and drift analysis in background
        if self.llm_client and self.analyzer_config.enabled:
            asyncio.create_task(
                self._async_extraction(
                    session_id, character, message_content, session.name
                )
            )

        return {
            "session_id": session_id,
            "character_name": character.name,
            "memory_context": context,
            "extraction_status": "processing" if self.llm_client else "skipped",
        }

    async def _build_context(
        self, session_id: str, character: CharacterIdentity
    ) -> str:
        """Build the memory context block for prompt injection."""
        state = await self.store.get_character_state(
            str(character.character_id), session_id
        )
        facts = await self.store.get_facts(session_id)
        relationships = await self.store.get_relationships(session_id)
        arcs = await self.store.get_narrative_arcs(session_id)
        drift_logs = await self.store.get_drift_logs(
            session_id, str(character.character_id)
        )

        all_chars = await self.store.get_characters(session_id)
        char_names = {str(c.character_id): c.name for c in all_chars}

        return format_memory_context(
            character=character,
            state=state,
            facts=facts,
            relationships=relationships,
            arcs=arcs,
            drift_warnings=drift_logs[:5],
            character_names=char_names,
        )

    async def _async_extraction(
        self,
        session_id: str,
        character: CharacterIdentity,
        message: str,
        session_name: str,
    ) -> None:
        """Run all extraction and drift analysis in the background."""
        try:
            # Run extractors concurrently
            tasks = []

            if self.analyzer_config.extract_facts:
                tasks.append(self._extract_and_store_facts(
                    session_id, character, message, session_name
                ))

            if self.analyzer_config.extract_relationships:
                tasks.append(self._extract_and_store_relationships(
                    session_id, character, message
                ))

            if self.analyzer_config.detect_drift:
                tasks.append(self._detect_and_store_drift(
                    session_id, character, message
                ))

            # Also extract character info to update state
            tasks.append(self._extract_and_update_state(
                session_id, character, message
            ))

            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Async extraction failed for session {session_id}: {e}")

    async def _extract_and_store_facts(
        self, session_id: str, character: CharacterIdentity, message: str, session_name: str
    ) -> None:
        """Extract facts and store them."""
        raw_facts = await extract_facts(
            self.llm_client, message, character.name, session_name
        )
        for raw in raw_facts:
            if raw.get("confidence", 0) >= self.analyzer_config.fact_confidence_threshold:
                try:
                    fact = Fact(
                        session_id=UUID(session_id),
                        category=FactCategory(raw.get("category", "world")),
                        subject=raw["subject"],
                        predicate=raw["predicate"],
                        object=raw["object"],
                        evidence=raw.get("evidence"),
                        confidence=raw.get("confidence", 0.5),
                    )
                    await self.store.create_fact(fact)
                except Exception as e:
                    logger.warning(f"Failed to store fact: {e}")

    async def _extract_and_store_relationships(
        self, session_id: str, character: CharacterIdentity, message: str
    ) -> None:
        """Extract relationships and store/update them."""
        all_chars = await self.store.get_characters(session_id)
        other_names = [c.name for c in all_chars if c.name != character.name]
        existing_rels = await self.store.get_relationships(session_id)

        existing_rel_dicts = [
            {"label": r.label, "trust_level": r.trust_level}
            for r in existing_rels
            if str(r.from_character) == str(character.character_id)
        ]

        raw_rels = await extract_relationships(
            self.llm_client, message, character.name, other_names, existing_rel_dicts
        )

        for raw in raw_rels:
            target_name = raw.get("target_character")
            if not target_name:
                continue

            target = await self.store.find_character_by_name(session_id, target_name)
            if not target:
                # Auto-create secondary character
                target = CharacterIdentity(
                    session_id=UUID(session_id),
                    name=target_name,
                    tier=CharacterTier.SECONDARY,
                )
                await self.store.create_character(target)

            try:
                # Check if relationship exists
                existing = await self.store.get_relationship(
                    str(character.character_id), str(target.character_id), session_id
                )
                if existing:
                    existing.label = raw.get("label", existing.label)
                    existing.trust_level = raw.get("trust_level", existing.trust_level)
                    existing.power_balance = raw.get("power_balance", existing.power_balance)
                    existing.emotional_undercurrent = raw.get(
                        "emotional_undercurrent", existing.emotional_undercurrent
                    )
                    await self.store.update_relationship(existing)
                else:
                    rel = RelationshipDynamic(
                        session_id=UUID(session_id),
                        from_character=character.character_id,
                        to_character=target.character_id,
                        label=raw.get("label", "unknown"),
                        trust_level=raw.get("trust_level", 0.0),
                        power_balance=raw.get("power_balance", 0.0),
                        emotional_undercurrent=raw.get("emotional_undercurrent"),
                    )
                    await self.store.create_relationship(rel)
            except Exception as e:
                logger.warning(f"Failed to store relationship: {e}")

    async def _detect_and_store_drift(
        self, session_id: str, character: CharacterIdentity, message: str
    ) -> None:
        """Run drift detection and store results."""
        facts = await self.store.get_facts(session_id)
        relationships = await self.store.get_relationships(session_id)
        sig = await self.store.get_behavioral_signature(
            str(character.character_id), session_id
        )

        profile = {
            "character_name": character.name,
            "core_traits": character.core_traits,
            "known_facts": [
                f"{f.subject} {f.predicate} {f.object}" for f in facts[:10]
            ],
            "relationships": [r.label for r in relationships[:10]],
            "previous_behavior": sig.interaction_style if sig else "No data yet.",
        }

        result = await detect_drift(self.llm_client, message, profile)

        if result.get("inconsistencies_detected"):
            for item in result.get("drift_items", []):
                try:
                    severity_map = {
                        "minor": DriftSeverity.MINOR,
                        "moderate": DriftSeverity.MODERATE,
                        "severe": DriftSeverity.SEVERE,
                    }
                    type_map = {
                        "trait": InconsistencyType.TRAIT,
                        "knowledge": InconsistencyType.KNOWLEDGE,
                        "relationship": InconsistencyType.RELATIONSHIP,
                        "behavior": InconsistencyType.BEHAVIOR,
                    }
                    drift = DriftLog(
                        character_id=character.character_id,
                        session_id=UUID(session_id),
                        inconsistency_type=type_map.get(
                            item.get("type", "behavior"), InconsistencyType.BEHAVIOR
                        ),
                        detected_in_message=message[:500],
                        previous_state=item.get("description", ""),
                        conflicting_state=item.get("evidence_from_message", ""),
                        severity=severity_map.get(
                            result.get("severity", "minor"), DriftSeverity.MINOR
                        ),
                    )
                    await self.store.create_drift_log(drift)
                except Exception as e:
                    logger.warning(f"Failed to store drift log: {e}")

    async def _extract_and_update_state(
        self, session_id: str, character: CharacterIdentity, message: str
    ) -> None:
        """Extract character info and update their state."""
        try:
            info = await extract_character_info(self.llm_client, message, character.name)
            state = CharacterState(
                character_id=character.character_id,
                session_id=UUID(session_id),
                mood=info.get("emotional_state"),
                current_goal=(
                    info["inferred_goals"][0] if info.get("inferred_goals") else None
                ),
            )
            await self.store.upsert_character_state(state)
        except Exception as e:
            logger.warning(f"Failed to update character state: {e}")
