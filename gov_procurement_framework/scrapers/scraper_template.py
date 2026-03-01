"""Template scraper for onboarding new procurement sources."""

from __future__ import annotations

from typing import Any

from gov_procurement_framework.models.tender_schema import (
    current_iso_timestamp,
    ensure_tender_schema,
)
from gov_procurement_framework.scrapers.base_scraper import BaseScraper


class NewSourceScraper(BaseScraper):
    """
    Copy this class into a new file and rename it.

    Checklist:
    - Set source_name and source_url.
    - Implement source-specific fetch/parse only.
    - Return unified schema records from normalize().
    """

    source_name = "new_source_key"
    source_url = "https://example.gov/procurement-endpoint"

    async def fetch(self, limit: int | None = None) -> dict[str, Any]:
        response = await self.request_engine.request("GET", self.source_url)
        return {"url": response.url, "body": response.body, "limit": limit}

    async def parse(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Parse raw_data["body"] into a list of source-native records.

        Expected return shape example:
        [
            {
                "id": "123",
                "title": "Road Rehabilitation",
                "agency": "Ministry of Works",
                "state": "Nairobi",
                "description": "...",
                "published_date": "2026-03-01",
                "closing_date": "2026-03-20",
                "budget": None,
                "currency": None,
                "category": "works",
                "document_url": "https://example/doc.pdf",
                "winning_company_name": "ABC Infrastructure Ltd",
                "company_registration_number": "CPR/12345",
                "company_address": "42 Main Street",
                "company_email": "contact@abc.example",
                "company_phone": "+254700000000",
                "company_website": "https://abc.example",
                "company_country": "Country Name",
                "company_state": "Nairobi",
            }
        ]
        """
        _ = raw_data
        return []

    async def normalize(self, parsed_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        scraped_at = current_iso_timestamp()
        normalized: list[dict[str, Any]] = []

        for item in parsed_data:
            tender_id = str(item.get("id", "unknown"))
            record = ensure_tender_schema(
                {
                    "source": self.source_name,
                    "scraped_at": scraped_at,
                    "country": "Country Name",
                    "state": item.get("state") or "Unknown State",
                    "ministry": item.get("agency") or "Unknown Ministry",
                    "tender": {
                        "tender_id": f"{self.source_name}-{tender_id}",
                        "title": item.get("title") or "Untitled Tender",
                        "budget": item.get("budget"),
                        "currency": item.get("currency"),
                        "published_date": item.get("published_date"),
                        "closing_date": item.get("closing_date"),
                        "category": item.get("category"),
                        "description": item.get("description"),
                        "documents": [
                            {
                                "name": "source_document",
                                "url": item.get("document_url") or "",
                            }
                        ],
                    },
                    "winning_company": {
                        "name": item.get("winning_company_name") or "Not awarded yet",
                        "company_details": {
                            "registration_number": item.get("company_registration_number"),
                            "address": item.get("company_address"),
                            "email": item.get("company_email"),
                            "phone": item.get("company_phone"),
                            "website": item.get("company_website"),
                            "country": item.get("company_country") or "Country Name",
                            "state": item.get("company_state"),
                        },
                    },
                }
            )
            normalized.append(record)

        return normalized

