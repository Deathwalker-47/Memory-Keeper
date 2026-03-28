"""Embedding generation for semantic search."""

import math
from typing import List, Optional

# Lazy-loaded model singleton
_model = None
_model_name = None


def load_embedding_model(model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    """Load the sentence-transformers model (lazy singleton).

    Only loads the model once; subsequent calls with the same name return cached.
    """
    global _model, _model_name
    if _model is not None and _model_name == model_name:
        return _model

    from sentence_transformers import SentenceTransformer

    _model = SentenceTransformer(model_name)
    _model_name = model_name
    return _model


def generate_embedding(
    text: str,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> List[float]:
    """Generate an embedding vector for the given text."""
    model = load_embedding_model(model_name)
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def compute_similarity(embedding_a: List[float], embedding_b: List[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    if len(embedding_a) != len(embedding_b):
        return 0.0
    dot = sum(a * b for a, b in zip(embedding_a, embedding_b))
    norm_a = math.sqrt(sum(a * a for a in embedding_a))
    norm_b = math.sqrt(sum(b * b for b in embedding_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
