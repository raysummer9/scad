"""Base contract for all government procurement source scrapers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from gov_procurement_framework.core.logger import get_logger
from gov_procurement_framework.core.request_engine import RequestEngine


class BaseScraper(ABC):
    """
    Source scraper contract.

    Concrete scrapers must implement:
    - fetch(): source-specific API/page retrieval
    - parse(): source-specific parsing
    - normalize(): mapping into unified tender schema
    """

    source_name = "unknown_source"

    def __init__(self, request_engine: RequestEngine, logger_name: str = "gov_procurement") -> None:
        self.request_engine = request_engine
        self.logger = get_logger(logger_name)

    @abstractmethod
    async def fetch(self, limit: int | None = None) -> Any:
        """Fetch raw source data."""

    @abstractmethod
    async def parse(self, raw_data: Any) -> Any:
        """Parse source data into intermediate representation."""

    @abstractmethod
    async def normalize(self, parsed_data: Any) -> list[dict[str, Any]]:
        """Normalize parsed data into unified tender schema."""

    async def run(self, limit: int | None = None) -> list[dict[str, Any]]:
        """
        Execute fetch -> parse -> normalize lifecycle.
        """
        raw_data = await self.fetch(limit=limit)
        parsed_data = await self.parse(raw_data)
        normalized = await self.normalize(parsed_data)
        self.logger.info(
            "scraper_lifecycle_completed",
            extra={
                "extra_payload": {
                    "source": self.source_name,
                    "records": len(normalized),
                }
            },
        )
        return normalized

