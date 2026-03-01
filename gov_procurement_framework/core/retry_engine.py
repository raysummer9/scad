"""Reusable async retry wrapper with exponential backoff."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from aiohttp import ClientError

from gov_procurement_framework.config import BASE_BACKOFF_DELAY, MAX_RETRIES

T = TypeVar("T")


class RetryEngine:
    """Execute an async operation with retry policy and backoff."""

    def __init__(
        self,
        max_retries: int = MAX_RETRIES,
        base_backoff_delay: float = BASE_BACKOFF_DELAY,
    ) -> None:
        self.max_retries = max_retries
        self.base_backoff_delay = base_backoff_delay

    async def run(
        self,
        operation: Callable[[int], Awaitable[T]],
        should_retry: Callable[[Exception], bool] | None = None,
        on_retry: Callable[[int, Exception], Awaitable[None] | None] | None = None,
    ) -> T:
        attempt = 0
        while True:
            try:
                return await operation(attempt)
            except Exception as exc:  # noqa: BLE001
                policy = should_retry or self._default_should_retry
                retryable = policy(exc)
                if not retryable or attempt >= self.max_retries:
                    raise

                if on_retry:
                    maybe_awaitable = on_retry(attempt + 1, exc)
                    if maybe_awaitable is not None:
                        await maybe_awaitable

                delay = self.base_backoff_delay * (2**attempt)
                await asyncio.sleep(delay)
                attempt += 1

    @staticmethod
    def _default_should_retry(exc: Exception) -> bool:
        return isinstance(exc, (TimeoutError, ClientError))

