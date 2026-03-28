"""Configuration system for Memory Keeper."""

import os
from pathlib import Path
from typing import Optional, Literal

import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    
    provider: Literal["openai", "anthropic", "local"] = "openai"
    model: str = Field(default="gpt-4", description="Model name/ID")
    api_key: Optional[str] = Field(default=None, description="API key (or use env var)")
    api_base: Optional[str] = Field(default=None, description="Custom API base URL")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000)


class AnalyzerConfig(BaseModel):
    """Analyzer behavior configuration."""
    
    enabled: bool = True
    extract_facts: bool = True
    extract_relationships: bool = True
    detect_drift: bool = True
    consolidate_memory: bool = True
    drift_sensitivity: Literal["low", "medium", "high"] = "medium"
    fact_confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)


class DatabaseConfig(BaseModel):
    """Database configuration."""
    
    backend: Literal["sqlite", "postgres"] = "sqlite"
    sqlite_path: Path = Field(default=Path("memory_keeper.db"))
    postgres_url: Optional[str] = Field(default=None)
    enable_embeddings: bool = True
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"


class SessionConfig(BaseModel):
    """Session management configuration."""
    
    auto_snapshot_interval: int = Field(default=25, description="Snapshot every N messages")
    max_snapshots_per_session: int = Field(default=10)
    soft_delete: bool = True
    archive_after_days: Optional[int] = None


class APIConfig(BaseModel):
    """API server configuration."""
    
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    cors_origins: list[str] = Field(default=["*"])
    log_level: Literal["debug", "info", "warning", "error"] = "info"


class Config(BaseModel):
    """Main Memory Keeper configuration."""
    
    mode: Literal["simple", "advanced", "custom"] = "simple"
    llm: LLMConfig = Field(default_factory=LLMConfig)
    analyzer: AnalyzerConfig = Field(default_factory=AnalyzerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from YAML file with environment variable overrides."""
    config_dict = {}
    
    # Load from file if provided
    if config_path and config_path.exists():
        with open(config_path) as f:
            config_dict = yaml.safe_load(f) or {}
    
    # Override with environment variables
    # Format: MK_<SECTION>__<KEY>=value
    for key, value in os.environ.items():
        if key.startswith("MK_"):
            # Parse nested structure: MK_llm__api_key -> llm.api_key
            parts = key[3:].lower().split("__")
            current = config_dict
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
    
    return Config(**config_dict)


def get_default_config() -> Config:
    """Get default configuration for simple mode."""
    return Config(mode="simple")


def save_config(config: Config, path: Path) -> None:
    """Save configuration to YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(config.dict(), f, default_flow_style=False)
