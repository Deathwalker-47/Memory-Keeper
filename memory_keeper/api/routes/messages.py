"""Message processing routes — the main endpoint."""

from fastapi import APIRouter, Depends, HTTPException

from memory_keeper.api.schemas import MessageRequest, MessageResponse
from memory_keeper.api.server import get_store
from memory_keeper.api.pipeline import MessagePipeline
from memory_keeper.config import load_config
from memory_keeper.store.sqlite_store import SQLiteStore

router = APIRouter(prefix="/sessions/{session_id}/messages", tags=["messages"])


def _get_pipeline(store: SQLiteStore) -> MessagePipeline:
    """Create a MessagePipeline with the current config."""
    config = load_config()

    llm_client = None
    if config.analyzer.enabled:
        try:
            from memory_keeper.analyzer.llm_client import LLMClient
            llm_client = LLMClient(config.llm)
        except Exception:
            pass  # LLM not configured; pipeline will skip extraction

    return MessagePipeline(
        store=store,
        llm_client=llm_client,
        analyzer_config=config.analyzer,
    )


@router.post("", response_model=MessageResponse)
async def process_message(
    session_id: str, body: MessageRequest, store: SQLiteStore = Depends(get_store)
):
    """Process a message through the memory pipeline.

    This is the main endpoint. It:
    1. Looks up or creates the character
    2. Retrieves relevant memory context (sync)
    3. Launches async extraction + drift analysis
    4. Returns the memory context immediately
    """
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    pipeline = _get_pipeline(store)

    try:
        result = await pipeline.process_message(
            session_id, body.character_name, body.message_content
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return MessageResponse(**result)
