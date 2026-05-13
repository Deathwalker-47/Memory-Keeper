"""Analyzer module for extracting and updating memory entities."""

from memory_keeper.analyzer.llm_client import LLMClient, LLMClientError
from memory_keeper.analyzer.character_analyzer import identify_characters, extract_character_info
from memory_keeper.analyzer.fact_extractor import extract_facts
from memory_keeper.analyzer.relationship_extractor import extract_relationships
from memory_keeper.analyzer.drift_detector import detect_drift
from memory_keeper.analyzer.embeddings import generate_embedding, compute_similarity
from memory_keeper.analyzer.state_consolidator import consolidate_facts, apply_consolidation
from memory_keeper.analyzer.narrator_analyzer import extract_narrator_state
from memory_keeper.analyzer.arc_extractor import extract_narrative_arcs
from memory_keeper.analyzer.narrator_drift_detector import detect_narrator_drift

__all__ = [
    "LLMClient",
    "LLMClientError",
    "identify_characters",
    "extract_character_info",
    "extract_facts",
    "extract_relationships",
    "detect_drift",
    "generate_embedding",
    "compute_similarity",
    "consolidate_facts",
    "apply_consolidation",
    "extract_narrator_state",
    "extract_narrative_arcs",
    "detect_narrator_drift",
]
