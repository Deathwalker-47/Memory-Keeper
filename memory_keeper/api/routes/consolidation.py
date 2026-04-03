"""State consolidation routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from memory_keeper.api.server import get_store
from memory_keeper.analyzer.state_consolidator import consolidate_facts, apply_consolidation
from memory_keeper.analyzer.llm_client import LLMClient
from memory_keeper.store.sqlite_store import SQLiteStore

router = APIRouter(prefix="/sessions/{session_id}", tags=["consolidation"])


@router.post("/consolidate")
async def consolidate_session_facts(
    session_id: str,
    character_name: str = Query(default="", description="Focus on a specific character"),
    auto_apply: bool = Query(default=False, description="Automatically deactivate redundant facts"),
    store: SQLiteStore = Depends(get_store),
):
    """Analyze session facts for redundancy and conflicts.

    If auto_apply is True, redundant/superseded/conflicting facts will be
    deactivated automatically. Otherwise, returns a plan for review.
    """
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    facts = await store.get_facts(session_id, active_only=True)
    if len(facts) < 2:
        return {
            "status": "no_action_needed",
            "message": "Not enough facts to consolidate",
            "fact_count": len(facts),
        }

    # Serialize facts for the LLM
    facts_dicts = [
        {
            "fact_id": str(f.fact_id),
            "category": f.category.value,
            "subject": f.subject,
            "predicate": f.predicate,
            "object": f.object,
            "confidence": f.confidence,
            "evidence": f.evidence,
        }
        for f in facts
    ]

    # Try to get LLM config from app state
    try:
        config = store.conn  # We need the app config
        # Use a simple client - the endpoint requires a configured LLM
        client = LLMClient(
            provider="openai",
            model="gpt-4",
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="LLM client not configured. Set MK_LLM__API_KEY environment variable.",
        )

    # Run consolidation analysis
    consolidation_result = await consolidate_facts(
        client=client,
        facts=facts_dicts,
        character_name=character_name,
        session_name=session.name,
    )

    # Apply if requested
    apply_result = await apply_consolidation(
        store=store,
        session_id=session_id,
        consolidation_result=consolidation_result,
        auto_apply=auto_apply,
    )

    return {
        "status": "applied" if auto_apply else "plan_ready",
        "analysis": consolidation_result,
        "actions": apply_result,
    }
