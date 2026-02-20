"""
Logging configuration for the Polymarket Position Monitor.
"""
from __future__ import annotations

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger with a consistent format."""
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt=date_fmt))

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers if called multiple times
    if not root.handlers:
        root.addHandler(handler)
    else:
        root.handlers = [handler]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
