"""Logging utilities for memov."""

import logging
import os
import sys


def setup_logging(loc: str, level: str = "INFO") -> None:
    """Configure logging for the application with improved setup."""
    # Ensure .mem directory exists
    mem_dir = os.path.join(loc, ".mem")
    os.makedirs(mem_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers to avoid duplication
    root_logger.handlers.clear()

    # File handler for debug messages
    log_path = os.path.join(mem_dir, "mem.log")
    file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s:%(lineno)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Console handler for user-facing messages
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
