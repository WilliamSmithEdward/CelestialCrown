"""Centralized logging configuration for the game."""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Initialize global logging with consistent formatting."""
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module."""
    return logging.getLogger(name)
