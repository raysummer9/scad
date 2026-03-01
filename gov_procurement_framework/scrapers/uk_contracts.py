"""UK Contracts Finder scraper."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from gov_procurement_framework.models.tender_schema import (
    current_iso_timestamp,
    ensure_tender_schema,
)
from gov_procurement_framework.scrapers.base_scraper import BaseScraper


class UkContractsScraper(BaseScraper):
    """Scrapes notices from Contracts Finder RSS feed-like endpoints."""

    source_name = "uk_contracts"
    source_url = "https://www.contractsfinder.service.gov.uk/Notices/RssFeed"

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
            root = ET.fromstring(body)
            for item in root.findall(".//item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                description = (item.findtext("description") or "").strip()
                items.append(
                    {
                        "title": title,
                        "url": link,
                        "published_date": pub_date,
                        "description": description,
                    }
                )
                if limit is not None and len(items) >= limit:
                    break
        except ET.ParseError:
            self.logger.warning(
                "source_parse_failed",
                extra={
                    "extra_payload": {
                        "source": self.source_name,
                        "detail": "Unable to parse XML feed body.",
                    }
                },
            )

        return items

    async def normalize(self, parsed_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        scraped_at = current_iso_timestamp()
        for idx, item in enumerate(parsed_data, start=1):
            record = ensure_tender_schema(
                {
                    "source": self.source_name,
                    "scraped_at": scraped_at,
                    "country": "United Kingdom",
                    "state": "Unknown State",
                    "ministry": "Contracts Finder",
                    "tender": {
                        "tender_id": f"uk-cf-{idx}",
                        "title": item.get("title") or "Untitled Notice",
                        "budget": None,
                        "currency": "GBP",
                        "published_date": item.get("published_date"),
                        "closing_date": None,
                        "category": "public_contract",
                        "description": item.get("description"),
                        "documents": [
                            {"name": "source_notice", "url": item.get("url") or ""}
                        ],
                    },
                    "winning_company": {
                        "name": "Not awarded yet",
                        "company_details": {
                            "registration_number": None,
                            "address": None,
                            "email": None,
                            "phone": None,
                            "website": None,
                            "country": "United Kingdom",
                            "state": "Unknown State",
                        },
                    },
                }
            )
            normalized.append(record)
        return normalized

