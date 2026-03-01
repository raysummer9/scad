"""Centralized runtime configuration for the framework."""

from __future__ import annotations

# Retry behavior
MAX_RETRIES = 3
BASE_BACKOFF_DELAY = 1.0  # seconds

# Rate limiting behavior (tokens per second)
GLOBAL_RATE_LIMIT = 5.0
DOMAIN_RATE_LIMITS = {
    "default": 2.0,
}

# Proxy behavior
PROXY_FAILURE_THRESHOLD = 3

# HTTP behavior
TIMEOUT_SECONDS = 30
DEFAULT_HEADERS = {
    "User-Agent": "GovProcurementFramework/1.0",
}

# Export and logging behavior
EXPORT_DEFAULT_FORMAT = "json"
LOG_LEVEL = "INFO"

