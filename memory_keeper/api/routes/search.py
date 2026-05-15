"""Semantic search routes."""

from fastapi import APIRouter, Depends, HTTPException

from memory_keeper.api.schemas import SearchRequest, SearchResult
from memory_keeper.api.server import get_store, get_config
from memory_keeper.config import Config
from memory_keeper.store.base import BaseStore

router = APIRouter(prefix="/sessions/{session_id}/search", tags=["search"])


@router.post("", response_model=list[SearchResult])
async def search_facts(
    session_id: str,
    body: SearchRequest,
    store: BaseStore = Depends(get_store),
    config: Config = Depends(get_config),
):
    """Search facts by semantic similarity.

    Generates an embedding for the query text and finds the most similar facts.
    Requires the sentence-transformers library to be installed.
    """
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not config.database.enable_embeddings:
        raise HTTPException(status_code=400, detail="Embeddings are disabled in config")

    try:
        from memory_keeper.analyzer.embeddings import generate_embedding
        query_embedding = generate_embedding(
            body.query, model_name=config.database.embedding_model
        )
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="sentence-transformers not installed. Install with: pip install sentence-transformers",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {e}")

    results = await store.search_facts_by_embedding(
        session_id, query_embedding, limit=body.limit
    )

    if not results:
        return []

    from memory_keeper.analyzer.embeddings import compute_similarity
    return [
        SearchResult(
            fact_id=str(f.fact_id),
            subject=f.subject,
            predicate=f.predicate,
            object=f.object,
            confidence=f.confidence,
            similarity=compute_similarity(query_embedding, f.embedding) if f.embedding else 0.0,
        )
        for f in results
    ]
