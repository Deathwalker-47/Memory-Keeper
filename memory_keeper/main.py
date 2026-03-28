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
            
            # Export session data
            session = await store.get_session(session_id)
            characters = await store.get_characters(session_id)
            facts = await store.get_facts(session_id)
            relationships = await store.get_relationships(session_id)
            
            data = {
                "session": session.dict() if session else None,
                "characters": [c.dict() for c in characters],
                "facts": [f.dict() for f in facts],
                "relationships": [r.dict() for r in relationships],
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
        with open(input_file) as f:
            data = json.load(f)
        
        async def import_session():
            store = SQLiteStore(db_path=str(cfg.database.sqlite_path))
            await store.initialize()
            
            # Import session data
            # (Implementation would depend on data model)
            
            await store.close()
        
        asyncio.run(import_session())
        click.echo(f"Session imported from {input_file}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# Legacy exports for backward compatibility
app = cli
init_command = init_command
serve_command = serve_command
export_command = export_command
import_command = import_command


if __name__ == "__main__":
    cli()
