"""Kenya PPRA scraper using the PPIP active tenders endpoint."""

from __future__ import annotations

import json
from typing import Any

from gov_procurement_framework.models.tender_schema import (
    current_iso_timestamp,
    ensure_tender_schema,
)
from gov_procurement_framework.scrapers.base_scraper import BaseScraper


class KenyaPpraScraper(BaseScraper):
    """Scrapes active tenders from Kenya PPIP (PPRA-linked public portal)."""

    source_name = "kenya_ppra"
    source_url = "https://tenders.go.ke/api/active-tenders"
    source_base_url = "https://tenders.go.ke"
    default_page_size = 10

    async def fetch(self, limit: int | None = None) -> dict[str, Any]:
        """
        Fetch active tenders with page traversal when a higher limit is requested.
        """
        target = limit if limit is not None and limit > 0 else self.default_page_size
        page = 1
        rows: list[dict[str, Any]] = []

        while len(rows) < target:
            response = await self.request_engine.request(
                "GET",
                self.source_url,
                params={"page": page},
            )
            payload = json.loads(response.body)
            page_rows = payload.get("data", [])
            if not isinstance(page_rows, list) or not page_rows:
                break

            rows.extend(item for item in page_rows if isinstance(item, dict))
            if not payload.get("next_page_url"):
                break
            page += 1

        return {"items": rows[:target], "limit": limit}

    async def parse(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        items = raw_data.get("items", [])
        parsed: list[dict[str, Any]] = []
        for item in items:
            pe = item.get("pe") if isinstance(item.get("pe"), dict) else {}
            category = (
                item.get("procurement_category")
                if isinstance(item.get("procurement_category"), dict)
                else {}
            )

            parsed.append(
                {
                    "id": item.get("id"),
                    "ocid": item.get("ocid"),
                    "tender_ref": item.get("tender_ref"),
                    "title": item.get("title"),
                    "agency": pe.get("name"),
                    "description": item.get("description"),
                    "published_date": item.get("published_at"),
                    "closing_date": item.get("close_at"),
                    "budget": item.get("tender_fee"),
                    "currency": "KES",
                    "category": category.get("title"),
                    "documents": item.get("documents", []),
                }
            )
        return parsed

    async def normalize(self, parsed_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        scraped_at = current_iso_timestamp()
        normalized: list[dict[str, Any]] = []

        for item in parsed_data:
            tender_id = (
                str(item.get("ocid"))
                if item.get("ocid")
                else (str(item.get("tender_ref")) if item.get("tender_ref") else str(item.get("id", "unknown")))
            )
            raw_documents = item.get("documents", [])
            documents: list[dict[str, str]] = []
            if isinstance(raw_documents, list):
                for doc in raw_documents:
                    if not isinstance(doc, dict):
                        continue
                    doc_url = str(doc.get("url") or "").strip()
                    if doc_url.startswith("/"):
                        doc_url = f"{self.source_base_url}{doc_url}"
                    documents.append(
                        {
                            "name": str(doc.get("description") or "tender_document"),
                            "url": doc_url,
                        }
                    )

            if not documents:
                documents = [
                    {
                        "name": "tender_page",
                        "url": f"{self.source_base_url}/tenders/{item.get('id')}",
                    }
                ]

            record = ensure_tender_schema(
                {
                    "source": self.source_name,
                    "scraped_at": scraped_at,
                    "country": "Kenya",
                    "state": "Unknown State",
                    "ministry": item.get("agency") or "Unknown Ministry",
                    "tender": {
                        "tender_id": tender_id,
                        "title": item.get("title") or "Untitled Tender",
                        "budget": str(item.get("budget")) if item.get("budget") is not None else None,
                        "currency": item.get("currency"),
                        "published_date": item.get("published_date"),
                        "closing_date": item.get("closing_date"),
                        "category": item.get("category"),
                        "description": item.get("description"),
                        "documents": documents,
                    },
                    "winning_company": {
                        "name": "Not awarded yet",
                        "company_details": {
                            "registration_number": None,
                            "address": None,
                            "email": None,
                            "phone": None,
                            "website": None,
                            "country": "Kenya",
                            "state": "Unknown State",
                        },
                    },
                }
            )
            normalized.append(record)

        return normalized

