"""Async token-bucket rate limiter for global and domain quotas."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from gov_procurement_framework.config import DOMAIN_RATE_LIMITS, GLOBAL_RATE_LIMIT


@dataclass
class TokenBucket:
    rate: float
    capacity: float
    tokens: float
    last_refill: float

    def refill(self) -> None:
        now = time.monotonic()
        elapsed = max(0.0, now - self.last_refill)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now


class RateLimiter:
    """Coordinates global and per-domain token-bucket acquisition."""

    def __init__(
        self,
        global_rate: float = GLOBAL_RATE_LIMIT,
        domain_rates: dict[str, float] | None = None,
    ) -> None:
        domain_config = domain_rates or DOMAIN_RATE_LIMITS
        now = time.monotonic()
        self._global = TokenBucket(
            rate=global_rate,
            capacity=max(1.0, global_rate),
            tokens=max(1.0, global_rate),
            last_refill=now,
        )
        self._domains: dict[str, TokenBucket] = {}
        self._domain_rates = domain_config
        self._lock = asyncio.Lock()

    def _domain_bucket(self, domain: str) -> TokenBucket:
        existing = self._domains.get(domain)
        if existing:
            return existing

        rate = self._domain_rates.get(domain, self._domain_rates.get("default", 1.0))
        now = time.monotonic()
        bucket = TokenBucket(
            rate=rate,
            capacity=max(1.0, rate),
            tokens=max(1.0, rate),
            last_refill=now,
        )
        self._domains[domain] = bucket
        return bucket

    async def acquire(self, domain: str) -> None:
        """Await until one global token and one domain token are available."""
        while True:
            async with self._lock:
                global_bucket = self._global
                domain_bucket = self._domain_bucket(domain)

                global_bucket.refill()
                domain_bucket.refill()

                if global_bucket.tokens >= 1.0 and domain_bucket.tokens >= 1.0:
                    global_bucket.tokens -= 1.0
                    domain_bucket.tokens -= 1.0
                    return

                global_wait = (
                    0.0
                    if global_bucket.tokens >= 1.0
                    else (1.0 - global_bucket.tokens) / global_bucket.rate
                )
                domain_wait = (
                    0.0
                    if domain_bucket.tokens >= 1.0
                    else (1.0 - domain_bucket.tokens) / domain_bucket.rate
                )
                wait_for = max(global_wait, domain_wait, 0.01)

            await asyncio.sleep(wait_for)

