"""CLI entry point for Memory Keeper."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click

from memory_keeper.config import load_config, save_config, get_default_config
from memory_keeper.api.server import create_app
from memory_keeper.store.sqlite_store import SQLiteStore


@click.group()
def cli():
    """Memory Keeper - LLM-agnostic memory management for roleplay applications."""
    pass


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(),
    default=None,
    help="Path to configuration YAML file"
)
@click.option(
    "--host",
    "-h",
    default="127.0.0.1",
    help="Server host"
)
@click.option(
    "--port",
    "-p",
    type=int,
    default=8000,
    help="Server port"
)
@click.option(
    "--reload",
    is_flag=True,
    help="Enable auto-reload on file changes (development)"
)
def serve_command(config: Optional[str], host: str, port: int, reload: bool):
    """Start the Memory Keeper API server."""
    try:
        # Load configuration
        config_path = Path(config) if config else None
        cfg = load_config(config_path)
        
        # Override with CLI args
        cfg.api.host = host
        cfg.api.port = port
        cfg.api.reload = reload
        
        click.echo(f"Starting Memory Keeper API on {host}:{port}...")
        
        # Create and run FastAPI app
        import uvicorn
        app = create_app(cfg)
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level=cfg.api.log_level
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(),
    default="config.yaml",
    help="Path to save configuration"
)
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["simple", "advanced"]),
    default="simple",
    help="Configuration mode"
)
def init_command(config: str, mode: str):
    """Initialize Memory Keeper configuration and database."""
    try:
        config_path = Path(config)
        
        click.echo("Memory Keeper Setup Wizard")
        click.echo("=" * 40)
        
        # Create configuration based on mode
        if mode == "simple":
            click.echo("\nSimple mode: Using defaults for single-character scenario")
            cfg = get_default_config()
        else:
            click.echo("\nAdvanced mode: Customize all settings")
            cfg = get_default_config()
            cfg.mode = "advanced"
        
        # Get LLM provider
        provider = click.prompt(
            "LLM Provider",
            type=click.Choice(["openai", "anthropic", "local"]),
            default="openai"
        )
        cfg.llm.provider = provider
        
        if provider != "local":
            api_key = click.prompt(
                f"{provider.capitalize()} API Key",
                hide_input=True,
                default=""
            )
            if api_key:
                cfg.llm.api_key = api_key
        
        # Get model
        default_model = "gpt-4" if provider == "openai" else "claude-opus"
        model = click.prompt(
            "Model name",
            default=default_model
        )
        cfg.llm.model = model
        
        # Save configuration
        save_config(cfg, config_path)
        click.echo(f"\nConfiguration saved to {config_path}")
        
        # Initialize database
        click.echo("\nInitializing database...")
        async def init_db():
            store = SQLiteStore(db_path=str(cfg.database.sqlite_path))
            await store.initialize()
            await store.close()
        
        asyncio.run(init_db())
        click.echo(f"Database initialized at {cfg.database.sqlite_path}")
        
        click.echo("\nSetup complete! Start server with:")
        click.echo(f"  memory-keeper serve --config {config_path}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("session_id")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    required=True,
    help="Output file path"
)
@click.option(
    "--config",
    "-c",
    type=click.Path(),
    default=None,
    help="Configuration file path"
)
def export_command(session_id: str, output: str, config: Optional[str]):
    """Export a session as JSON."""
    try:
        config_path = Path(config) if config else None
        cfg = load_config(config_path)

        import json
        async def export_session():
            store = SQLiteStore(db_path=str(cfg.database.sqlite_path))
            await store.initialize()

            session = await store.get_session(session_id)
            if not session:
                raise click.ClickException(f"Session '{session_id}' not found")

            characters = await store.get_characters(session_id)
            facts = await store.get_facts(session_id)
            relationships = await store.get_relationships(session_id)
            events = await store.get_events(session_id)
            arcs = await store.get_narrative_arcs(session_id)
            drift_logs = await store.get_drift_logs(session_id)

            data = {
                "session": session.model_dump(mode="json"),
                "characters": [c.model_dump(mode="json") for c in characters],
                "facts": [f.model_dump(mode="json") for f in facts],
                "relationships": [r.model_dump(mode="json") for r in relationships],
                "events": [e.model_dump(mode="json") for e in events],
                "narrative_arcs": [a.model_dump(mode="json") for a in arcs],
                "drift_logs": [d.model_dump(mode="json") for d in drift_logs],
            }

            await store.close()
            return data

        data = asyncio.run(export_session())

        with open(output, "w") as f:
            json.dump(data, f, indent=2, default=str)

        click.echo(f"Session exported to {output}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("input_file")
@click.option(
    "--config",
    "-c",
    type=click.Path(),
    default=None,
    help="Configuration file path"
)
def import_command(input_file: str, config: Optional[str]):
    """Import a session from JSON."""
    try:
        config_path = Path(config) if config else None
        cfg = load_config(config_path)

        import json
        from uuid import UUID
        from memory_keeper.store.models import (
            Session,
            CharacterIdentity,
            CharacterTier,
            Fact,
            FactCategory,
            RelationshipDynamic,
            Event,
            NarrativeArc,
            ArcStatus,
            DriftLog,
            DriftSeverity,
            InconsistencyType,
        )

        with open(input_file) as f:
            data = json.load(f)

        async def do_import():
            store = SQLiteStore(db_path=str(cfg.database.sqlite_path))
            await store.initialize()

            counts = {"characters": 0, "facts": 0, "relationships": 0,
                      "events": 0, "narrative_arcs": 0, "drift_logs": 0}

            # Import session
            session_data = data.get("session")
            if session_data:
                existing = await store.get_session(str(session_data["session_id"]))
                if not existing:
                    session = Session(
                        session_id=UUID(session_data["session_id"]),
                        name=session_data["name"],
                        created_at=session_data.get("created_at"),
                        updated_at=session_data.get("updated_at"),
                        archived=session_data.get("archived", False),
                        config=session_data.get("config", {}),
                    )
                    await store.create_session(session)
                    click.echo(f"Created session: {session.name}")
                else:
                    click.echo(f"Session already exists: {existing.name}")

            # Import characters
            for char_data in data.get("characters", []):
                char = CharacterIdentity(
                    character_id=UUID(char_data["character_id"]),
                    session_id=UUID(char_data["session_id"]),
                    name=char_data["name"],
                    tier=CharacterTier(char_data.get("tier", "primary")),
                    core_traits=char_data.get("core_traits", []),
                    background=char_data.get("background"),
                    worldview=char_data.get("worldview"),
                    speech_patterns=char_data.get("speech_patterns", {}),
                    appearance=char_data.get("appearance"),
                    created_at=char_data.get("created_at"),
                    last_modified=char_data.get("last_modified"),
                    active=char_data.get("active", True),
                )
                await store.create_character(char)
                counts["characters"] += 1

            # Import facts
            for fact_data in data.get("facts", []):
                fact = Fact(
                    fact_id=UUID(fact_data["fact_id"]),
                    session_id=UUID(fact_data["session_id"]),
                    category=FactCategory(fact_data["category"]),
                    subject=fact_data["subject"],
                    predicate=fact_data["predicate"],
                    object=fact_data["object"],
                    evidence=fact_data.get("evidence"),
                    confidence=fact_data.get("confidence", 0.5),
                    active=fact_data.get("active", True),
                    created_at=fact_data.get("created_at"),
                    embedding=fact_data.get("embedding"),
                )
                await store.create_fact(fact)
                counts["facts"] += 1

            # Import relationships
            for rel_data in data.get("relationships", []):
                rel = RelationshipDynamic(
                    relationship_id=UUID(rel_data["relationship_id"]),
                    session_id=UUID(rel_data["session_id"]),
                    from_character=UUID(rel_data["from_character"]),
                    to_character=UUID(rel_data["to_character"]),
                    label=rel_data["label"],
                    trust_level=rel_data.get("trust_level", 0.0),
                    power_balance=rel_data.get("power_balance", 0.0),
                    emotional_undercurrent=rel_data.get("emotional_undercurrent"),
                    history=rel_data.get("history"),
                    last_interaction=rel_data.get("last_interaction"),
                )
                await store.create_relationship(rel)
                counts["relationships"] += 1

            # Import events
            for event_data in data.get("events", []):
                event = Event(
                    event_id=UUID(event_data["event_id"]),
                    session_id=UUID(event_data["session_id"]),
                    involved_characters=[UUID(c) for c in event_data.get("involved_characters", [])],
                    description=event_data["description"],
                    emotional_impact={UUID(k): v for k, v in event_data.get("emotional_impact", {}).items()},
                    timestamp=event_data.get("timestamp"),
                    session_turn=event_data.get("session_turn", 0),
                )
                await store.create_event(event)
                counts["events"] += 1

            # Import narrative arcs
            for arc_data in data.get("narrative_arcs", []):
                arc = NarrativeArc(
                    arc_id=UUID(arc_data["arc_id"]),
                    session_id=UUID(arc_data["session_id"]),
                    title=arc_data["title"],
                    involved_characters=[UUID(c) for c in arc_data.get("involved_characters", [])],
                    current_status=ArcStatus(arc_data.get("current_status", "setup")),
                    beats=arc_data.get("beats", []),
                    expected_outcome=arc_data.get("expected_outcome"),
                )
                await store.create_narrative_arc(arc)
                counts["narrative_arcs"] += 1

            # Import drift logs
            for drift_data in data.get("drift_logs", []):
                drift = DriftLog(
                    drift_id=UUID(drift_data["drift_id"]),
                    character_id=UUID(drift_data["character_id"]),
                    session_id=UUID(drift_data["session_id"]),
                    inconsistency_type=InconsistencyType(drift_data["inconsistency_type"]),
                    detected_in_message=drift_data["detected_in_message"],
                    previous_state=drift_data["previous_state"],
                    conflicting_state=drift_data["conflicting_state"],
                    severity=DriftSeverity(drift_data.get("severity", "minor")),
                    resolution=drift_data.get("resolution"),
                    timestamp=drift_data.get("timestamp"),
                )
                await store.create_drift_log(drift)
                counts["drift_logs"] += 1

            await store.close()
            return counts

        counts = asyncio.run(do_import())
        click.echo(f"Import complete: {counts}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
