"""API route modules."""

from memory_keeper.api.routes.sessions import router as sessions_router
from memory_keeper.api.routes.characters import router as characters_router
from memory_keeper.api.routes.facts import router as facts_router
from memory_keeper.api.routes.relationships import router as relationships_router
from memory_keeper.api.routes.messages import router as messages_router
from memory_keeper.api.routes.memory import router as memory_router
from memory_keeper.api.routes.snapshots import router as snapshots_router
from memory_keeper.api.routes.drift import router as drift_router

__all__ = [
    "sessions_router",
    "characters_router",
    "facts_router",
    "relationships_router",
    "messages_router",
    "memory_router",
    "snapshots_router",
    "drift_router",
]
