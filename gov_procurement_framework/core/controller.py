"""Framework orchestrator for scraper execution lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from gov_procurement_framework.core.logger import get_logger
from gov_procurement_framework.core.proxy_manager import ProxyManager
from gov_procurement_framework.core.rate_limiter import RateLimiter
from gov_procurement_framework.core.request_engine import RequestEngine
from gov_procurement_framework.core.retry_engine import RetryEngine
from gov_procurement_framework.scrapers.base_scraper import BaseScraper

Exporter = Callable[[list[dict[str, Any]], str], None]
ScraperFactory = Callable[[RequestEngine], BaseScraper]


class Controller:
    """Dependency-injection orchestrator for scraper runtime."""

    def __init__(
        self,
        *,
        proxy_manager: ProxyManager | None = None,
        rate_limiter: RateLimiter | None = None,
        retry_engine: RetryEngine | None = None,
        request_engine: RequestEngine | None = None,
        logger_name: str = "gov_procurement",
    ) -> None:
        self.logger = get_logger(logger_name)
        self.proxy_manager = proxy_manager or ProxyManager()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.retry_engine = retry_engine or RetryEngine()
        self.request_engine = request_engine or RequestEngine(
            proxy_manager=self.proxy_manager,
            rate_limiter=self.rate_limiter,
            retry_engine=self.retry_engine,
            logger_name=logger_name,
        )

    async def run_scraper(
        self,
        scraper_factory: ScraperFactory,
        *,
        limit: int | None = None,
        exporter: Exporter | None = None,
        export_filename: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Build and execute scraper lifecycle, then optionally export data.
        """
        scraper = scraper_factory(self.request_engine)

        try:
            normalized = await scraper.run(limit=limit)
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "scraper_execution_failed",
                extra={
                    "extra_payload": {
                        "source": scraper.source_name,
                        "error": str(exc),
                    }
                },
            )
            raise

        if exporter and export_filename:
            exporter(normalized, export_filename)
            self.logger.info(
                "scraper_export_completed",
                extra={
                    "extra_payload": {
                        "source": scraper.source_name,
                        "records": len(normalized),
                        "filename": export_filename,
                    }
                },
            )

        self.logger.info(
            "scraper_execution_completed",
            extra={
                "extra_payload": {
                    "source": scraper.source_name,
                    "records": len(normalized),
                }
            },
        )
        return normalized

