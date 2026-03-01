"""Structured JSON logging utilities for scraping runtime."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gov_procurement_framework.config import LOG_LEVEL


class JsonFormatter(logging.Formatter):
    """Format log records as one-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        extras = getattr(record, "extra_payload", None)
        if isinstance(extras, dict):
            payload.update(extras)
        return json.dumps(payload, ensure_ascii=True)


def _file_handler(path: Path) -> logging.FileHandler:
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(JsonFormatter())
    return handler


def get_logger(name: str = "gov_procurement", logs_dir: str = "logs") -> logging.Logger:
    """
    Return a logger configured for scraper, error, and performance logs.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)
    logger.propagate = False

    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)

    scraper_handler = _file_handler(logs_path / "scraper.log")
    error_handler = _file_handler(logs_path / "error.log")
    perf_handler = _file_handler(logs_path / "performance.log")

    error_handler.setLevel(logging.ERROR)

    logger.addHandler(scraper_handler)
    logger.addHandler(error_handler)
    logger.addHandler(perf_handler)
    return logger

