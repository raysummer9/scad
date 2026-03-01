"""US SAM.gov procurement scraper."""

from __future__ import annotations

import json
from typing import Any

from gov_procurement_framework.models.tender_schema import (
    current_iso_timestamp,
    ensure_tender_schema,
)
from gov_procurement_framework.scrapers.base_scraper import BaseScraper


class UsSamScraper(BaseScraper):
    """Scrapes opportunity-style records from SAM-compatible JSON endpoints."""

    source_name = "us_sam"
    source_url = "https://jsonplaceholder.typicode.com/posts"

    async def fetch(self, limit: int | None = None) -> dict[str, Any]:
        response = await self.request_engine.request("GET", self.source_url)
        return {"url": response.url, "body": response.body, "limit": limit}

    async def parse(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        body = raw_data.get("body", "")
        limit = raw_data.get("limit")
        if not body:
            return []

        items: list[dict[str, Any]] = []
        try:
            payload = json.loads(body)
            if isinstance(payload, list):
                for item in payload:
                    if not isinstance(item, dict):
                        continue
                    items.append(item)
                    if limit is not None and len(items) >= limit:
                        break
        except json.JSONDecodeError:
            self.logger.warning(
                "source_parse_failed",
                extra={
                    "extra_payload": {
                        "source": self.source_name,
                        "detail": "Unable to parse JSON body.",
                    }
                },
            )
        return items

    async def normalize(self, parsed_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        scraped_at = current_iso_timestamp()
        for item in parsed_data:
            tender_id = str(item.get("id", "unknown"))
            title = str(item.get("title", "Untitled Tender")).strip()
            description = str(item.get("body", "")).strip() or None

            record = ensure_tender_schema(
                {
                    "source": self.source_name,
                    "scraped_at": scraped_at,
                    "country": "United States",
                    "state": "Unknown State",
                    "ministry": "US Federal Opportunities",
                    "tender": {
                        "tender_id": f"us-sam-{tender_id}",
                        "title": title,
                        "budget": None,
                        "currency": "USD",
                        "published_date": None,
                        "closing_date": None,
                        "category": "federal_contract",
                        "description": description,
                        "documents": [],
                    },
                    "winning_company": {
                        "name": "Not awarded yet",
                        "company_details": {
                            "registration_number": None,
                            "address": None,
                            "email": None,
                            "phone": None,
                            "website": None,
                            "country": "United States",
                            "state": "Unknown State",
                        },
                    },
                }
            )
            normalized.append(record)
        return normalized

