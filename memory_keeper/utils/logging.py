"""Logging configuration for Memory Keeper."""

import logging
import sys
from typing import Literal

import loguru


def setup_logging(
    level: Literal["debug", "info", "warning", "error"] = "info",
    format_string: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
) -> None:
    """Configure logging for Memory Keeper."""
    
    # Remove default handler
    loguru.logger.remove()
    
    # Add new handler with custom format
    loguru.logger.add(
        sys.stderr,
        format=format_string,
        level=level.upper(),
        colorize=True,
    )
    
    # Configure standard logging to use loguru
    logging.basicConfig(handlers=[loguru.logger], level=level.upper())


def get_logger(name: str) -> loguru.Logger:
    """Get a logger instance."""
    return loguru.logger.bind(name=name)
