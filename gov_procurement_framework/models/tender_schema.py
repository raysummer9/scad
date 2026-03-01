"""Unified tender schema helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


REQUIRED_TENDER_KEYS = {
    "source",
    "scraped_at",
    "country",
    "state",
    "ministry",
    "tender",
    "winning_company",
}

REQUIRED_TENDER_NODE_KEYS = {
    "tender_id",
    "title",
    "budget",
    "currency",
    "published_date",
    "closing_date",
    "category",
    "description",
    "documents",
}

REQUIRED_COMPANY_DETAILS_KEYS = {
    "registration_number",
    "address",
    "email",
    "phone",
    "website",
    "country",
    "state",
}

REQUIRED_WINNING_COMPANY_KEYS = {
    "name",
    "company_details",
}


def current_iso_timestamp() -> str:
    """Return timezone-aware ISO8601 timestamp."""
    return datetime.now(timezone.utc).isoformat()


def ensure_tender_schema(record: dict[str, Any]) -> dict[str, Any]:
    """
    Ensure a record matches the hierarchical schema:
    Country -> State -> Ministry -> Tender -> Winning Company -> Company Details
    """
    normalized = {key: record.get(key) for key in REQUIRED_TENDER_KEYS}
    normalized["tender"] = _normalize_tender_node(normalized.get("tender"))
    normalized["winning_company"] = _normalize_winning_company(
        normalized.get("winning_company")
    )

    missing = REQUIRED_TENDER_KEYS.difference(normalized.keys())
    if missing:
        raise ValueError(f"Tender schema missing keys: {sorted(missing)}")

    if normalized.get("country") is None:
        normalized["country"] = "Unknown Country"
    if normalized.get("state") is None:
        normalized["state"] = "Unknown State"
    if normalized.get("ministry") is None:
        normalized["ministry"] = "Unknown Ministry"

    return normalized


def _normalize_tender_node(tender: Any) -> dict[str, Any]:
    raw = tender if isinstance(tender, dict) else {}
    normalized = {key: raw.get(key) for key in REQUIRED_TENDER_NODE_KEYS}
    if normalized.get("documents") is None or not isinstance(normalized.get("documents"), list):
        normalized["documents"] = []
    return normalized


def _normalize_winning_company(company: Any) -> dict[str, Any]:
    raw = company if isinstance(company, dict) else {}
    normalized = {key: raw.get(key) for key in REQUIRED_WINNING_COMPANY_KEYS}
    if normalized.get("name") is None:
        normalized["name"] = "Unknown Company"
    normalized["company_details"] = _normalize_company_details(
        normalized.get("company_details")
    )
    return normalized


def _normalize_company_details(details: Any) -> dict[str, Any]:
    raw = details if isinstance(details, dict) else {}
    return {key: raw.get(key) for key in REQUIRED_COMPANY_DETAILS_KEYS}

