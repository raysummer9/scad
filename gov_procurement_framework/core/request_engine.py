"""Async HTTP request orchestration with retries, proxies, and rate limiting."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import aiohttp

from gov_procurement_framework.config import DEFAULT_HEADERS, TIMEOUT_SECONDS
from gov_procurement_framework.core.logger import get_logger
from gov_procurement_framework.core.proxy_manager import ProxyManager
from gov_procurement_framework.core.rate_limiter import RateLimiter
from gov_procurement_framework.core.retry_engine import RetryEngine

RETRYABLE_STATUS_CODES = {403, 429, 500, 502, 503, 504}


class RetryableHttpStatusError(Exception):
    """Raised for status codes that should trigger retry."""

    def __init__(self, status: int, url: str) -> None:
        super().__init__(f"Retryable HTTP status {status} for {url}")
        self.status = status
        self.url = url


@dataclass
class RawResponse:
    url: str
    status: int
    headers: dict[str, str]
    body: str
    retry_count: int
    proxy_used: str | None


class RequestEngine:
    """Responsible for all HTTP request cross-cutting concerns."""

    def __init__(
        self,
        proxy_manager: ProxyManager,
        rate_limiter: RateLimiter,
        retry_engine: RetryEngine,
        logger_name: str = "gov_procurement",
    ) -> None:
        self.proxy_manager = proxy_manager
        self.rate_limiter = rate_limiter
        self.retry_engine = retry_engine
        self.logger = get_logger(logger_name)

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        timeout_seconds: int = TIMEOUT_SECONDS,
        session: aiohttp.ClientSession | None = None,
    ) -> RawResponse:
        domain = urlparse(url).netloc or "default"
        request_headers = {**DEFAULT_HEADERS, **(headers or {})}
        own_session = session is None
        active_session = session or aiohttp.ClientSession()

        start_time = time.monotonic()
        last_proxy: dict[str, str] | None = None

        async def _operation(attempt: int) -> RawResponse:
            nonlocal last_proxy
            await self.rate_limiter.acquire(domain)
            last_proxy = self.proxy_manager.get_proxy()
            proxy_url = last_proxy["url"] if last_proxy else None

            async with active_session.request(
                method=method.upper(),
                url=url,
                headers=request_headers,
                params=params,
                data=data,
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=timeout_seconds),
            ) as response:
                body = await response.text()
                if response.status in RETRYABLE_STATUS_CODES:
                    raise RetryableHttpStatusError(response.status, url)

                self.proxy_manager.report_success(last_proxy)
                duration_ms = int((time.monotonic() - start_time) * 1000)
                self.logger.info(
                    "request_completed",
                    extra={
                        "extra_payload": {
                            "url": url,
                            "status": response.status,
                            "proxy": proxy_url,
                            "duration_ms": duration_ms,
                            "retry_count": attempt,
                        }
                    },
                )
                return RawResponse(
                    url=str(response.url),
                    status=response.status,
                    headers=dict(response.headers),
                    body=body,
                    retry_count=attempt,
                    proxy_used=proxy_url,
                )

        async def _on_retry(next_attempt: int, exc: Exception) -> None:
            self.proxy_manager.report_failure(last_proxy)
            self.logger.warning(
                "request_retry",
                extra={
                    "extra_payload": {
                        "url": url,
                        "error": str(exc),
                        "next_attempt": next_attempt,
                        "proxy": last_proxy["url"] if last_proxy else None,
                    }
                },
            )

        def _should_retry(exc: Exception) -> bool:
            if isinstance(exc, RetryableHttpStatusError):
                return True
            if isinstance(exc, asyncio.TimeoutError):
                return True
            if isinstance(exc, aiohttp.ClientConnectionError):
                return True
            if isinstance(exc, aiohttp.ClientPayloadError):
                return True
            return False

        try:
            return await self.retry_engine.run(
                operation=_operation,
                should_retry=_should_retry,
                on_retry=_on_retry,
            )
        except Exception as exc:  # noqa: BLE001
            duration_ms = int((time.monotonic() - start_time) * 1000)
            self.logger.error(
                "request_failed",
                extra={
                    "extra_payload": {
                        "url": url,
                        "status": getattr(exc, "status", None),
                        "proxy": last_proxy["url"] if last_proxy else None,
                        "duration_ms": duration_ms,
                        "retry_count": self.retry_engine.max_retries,
                        "error": str(exc),
                    }
                },
            )
            raise
        finally:
            if own_session:
                await active_session.close()

