"""FastAPI server for Memory Keeper."""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from memory_keeper.config import Config
from memory_keeper.store.sqlite_store import SQLiteStore


# Global store instance
_store: Optional[SQLiteStore] = None


async def get_store() -> SQLiteStore:
    """Get the global store instance."""
    global _store
    if _store is None:
        raise RuntimeError("Store not initialized")
    return _store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle FastAPI lifespan events."""
    global _store
    
    # Startup
    config = app.state.config
    _store = SQLiteStore(db_path=str(config.database.sqlite_path))
    await _store.initialize()
    
    yield
    
    # Shutdown
    if _store:
        await _store.close()


def create_app(config: Config) -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Memory Keeper",
        description="LLM-agnostic memory management service",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    # Store config in app state
    app.state.config = config
    app.state.store = None  # Will be initialized in lifespan
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Health check endpoint
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok"}

    # Include routers
    from memory_keeper.api.routes import (
        sessions_router,
        characters_router,
        facts_router,
        relationships_router,
        messages_router,
        memory_router,
        snapshots_router,
        drift_router,
    )
    app.include_router(sessions_router)
    app.include_router(characters_router)
    app.include_router(facts_router)
    app.include_router(relationships_router)
    app.include_router(messages_router)
    app.include_router(memory_router)
    app.include_router(snapshots_router)
    app.include_router(drift_router)

    return app
