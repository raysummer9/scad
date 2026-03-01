"""Proxy pool management with rotation and health tracking."""

from __future__ import annotations

import os
from dataclasses import dataclass

from gov_procurement_framework.config import PROXY_FAILURE_THRESHOLD


@dataclass(frozen=True)
class ProxyConfig:
    """Canonical proxy representation."""

    id: str
    url: str


class ProxyManager:
    """Round-robin proxy selection with failure thresholds."""

    def __init__(
        self,
        proxies: list[str] | None = None,
        proxy_file: str | None = None,
    ) -> None:
        sources = proxies or self._load_from_file(proxy_file) or self._load_from_env()
        self._proxies: list[ProxyConfig] = [
            ProxyConfig(id=f"proxy_{idx}", url=value.strip())
            for idx, value in enumerate(sources)
            if value and value.strip()
        ]
        self._index = 0
        self._failures: dict[str, int] = {proxy.id: 0 for proxy in self._proxies}
        self._disabled: set[str] = set()

    def _load_from_file(self, proxy_file: str | None) -> list[str]:
        if not proxy_file:
            return []
        with open(proxy_file, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]

    def _load_from_env(self) -> list[str]:
        raw = os.getenv("PROXIES", "")
        if not raw:
            return []
        return [part.strip() for part in raw.split(",") if part.strip()]

    def get_proxy(self) -> dict[str, str] | None:
        """Return next healthy proxy in round-robin order."""
        if not self._proxies:
            return None

        healthy = [proxy for proxy in self._proxies if proxy.id not in self._disabled]
        if not healthy:
            # Fallback to direct connection if all proxies are unhealthy.
            return None

        selected = healthy[self._index % len(healthy)]
        self._index = (self._index + 1) % len(healthy)
        return {"id": selected.id, "url": selected.url}

    def report_success(self, proxy: dict[str, str] | None) -> None:
        if not proxy:
            return
        proxy_id = proxy.get("id")
        if not proxy_id:
            return
        self._failures[proxy_id] = 0
        self._disabled.discard(proxy_id)

    def report_failure(self, proxy: dict[str, str] | None) -> None:
        if not proxy:
            return
        proxy_id = proxy.get("id")
        if not proxy_id:
            return
        current = self._failures.get(proxy_id, 0) + 1
        self._failures[proxy_id] = current
        if current >= PROXY_FAILURE_THRESHOLD:
            self._disabled.add(proxy_id)

