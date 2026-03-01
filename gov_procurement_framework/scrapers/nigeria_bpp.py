"""Nigeria Bureau of Public Procurement scraper."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from typing import Any

from gov_procurement_framework.models.tender_schema import (
    current_iso_timestamp,
    ensure_tender_schema,
)
from gov_procurement_framework.scrapers.base_scraper import BaseScraper


class NigeriaBppScraper(BaseScraper):
    """Scrapes procurement tenders from multiple Nigeria-focused feeds."""

    source_name = "nigeria_bpp"
    source_feeds = [
        {
            "name": "Public Procurement NG (All)",
            "url": "https://publicprocurement.ng/feed/",
        },
        {
            "name": "Public Procurement NG (Tender)",
            "url": "https://publicprocurement.ng/category/tender/feed/",
        },
        {
            "name": "Public Procurement NG (Pre-Qualification Notice)",
            "url": "https://publicprocurement.ng/category/pre-qualification-notice/feed/",
        },
        {
            "name": "Public Procurement NG (Expression of Interest)",
            "url": "https://publicprocurement.ng/category/expression-of-interest-eoi/feed/",
        },
        {
            "name": "Public Procurement NG (General Procurement Notice)",
            "url": "https://publicprocurement.ng/category/general-procurement-notice/feed/",
        },
    ]

    async def fetch(self, limit: int | None = None) -> dict[str, Any]:
        feeds: list[dict[str, str]] = []
        for feed in self.source_feeds:
            try:
                response = await self.request_engine.request("GET", feed["url"])
                feeds.append(
                    {
                        "feed_name": feed["name"],
                        "feed_url": feed["url"],
                        "body": response.body,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                self.logger.warning(
                    "nigeria_feed_fetch_failed",
                    extra={
                        "extra_payload": {
                            "source": self.source_name,
                            "feed_name": feed["name"],
                            "feed_url": feed["url"],
                            "error": str(exc),
                        }
                    },
                )
        return {"feeds": feeds, "limit": limit}

    async def parse(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        feeds = raw_data.get("feeds", [])
        limit = raw_data.get("limit")

        items: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for feed in feeds:
            body = feed.get("body", "")
            if not body:
                continue

            try:
                root = ET.fromstring(body)
            except ET.ParseError:
                self.logger.warning(
                    "source_parse_failed",
                    extra={
                        "extra_payload": {
                            "source": self.source_name,
                            "detail": "Unable to parse XML feed body.",
                            "feed_name": feed.get("feed_name"),
                            "feed_url": feed.get("feed_url"),
                        }
                    },
                )
                continue

            for node in root.findall(".//item"):
                title = (node.findtext("title") or "").strip()
                link = (node.findtext("link") or "").strip()
                pub_date = (node.findtext("pubDate") or "").strip()
                description = (node.findtext("description") or "").strip()
                content_id = self._content_id(title=title, link=link)
                if content_id in seen_ids:
                    continue
                seen_ids.add(content_id)

                items.append(
                    {
                        "title": title,
                        "url": link,
                        "published_date": pub_date,
                        "description": description,
                        "feed_name": feed.get("feed_name"),
                        "feed_url": feed.get("feed_url"),
                        "entity": self._extract_entity_from_title(title),
                        "content_id": content_id,
                    }
                )
                if limit is not None and len(items) >= limit:
                    return items

        return items

    async def normalize(self, parsed_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        scraped_at = current_iso_timestamp()
        for item in parsed_data:
            ministry = item.get("entity") or "Unknown Ministry"
            tender_id = f"ng-{item.get('content_id') or 'unknown'}"
            record = ensure_tender_schema(
                {
                    "source": self.source_name,
                    "scraped_at": scraped_at,
                    "country": "Nigeria",
                    "state": self._infer_state_from_title(item.get("title")),
                    "ministry": ministry,
                    "tender": {
                        "tender_id": tender_id,
                        "title": item.get("title") or "Untitled Tender",
                        "budget": None,
                        "currency": None,
                        "published_date": item.get("published_date"),
                        "closing_date": None,
                        "category": "procurement",
                        "description": item.get("description"),
                        "documents": [
                            {
                                "name": item.get("feed_name") or "source_notice",
                                "url": item.get("url") or "",
                            },
                            {
                                "name": "source_feed",
                                "url": item.get("feed_url") or "",
                            },
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
                            "country": "Nigeria",
                            "state": "Federal",
                        },
                    },
                }
            )
            normalized.append(record)
        return normalized

    @staticmethod
    def _content_id(title: str, link: str) -> str:
        raw = (link or title or "").strip()
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _extract_entity_from_title(title: str | None) -> str | None:
        if not title:
            return None
        parts = re.split(r"\s*-\s*", title, maxsplit=1)
        if not parts:
            return None
        entity = parts[0].strip()
        return entity or None

    @staticmethod
    def _infer_state_from_title(title: str | None) -> str:
        if not title:
            return "Federal"
        upper_title = title.upper()
        state_hints = [
            "ABIA",
            "ADAMAWA",
            "AKWA IBOM",
            "ANAMBRA",
            "BAUCHI",
            "BAYELSA",
            "BENUE",
            "BORNO",
            "CROSS RIVER",
            "DELTA",
            "EBONYI",
            "EDO",
            "EKITI",
            "ENUGU",
            "GOMBE",
            "IMO",
            "JIGAWA",
            "KADUNA",
            "KANO",
            "KATSINA",
            "KEBBI",
            "KOGI",
            "KWARA",
            "LAGOS",
            "NASARAWA",
            "NIGER",
            "OGUN",
            "ONDO",
            "OSUN",
            "OYO",
            "PLATEAU",
            "RIVERS",
            "SOKOTO",
            "TARABA",
            "YOBE",
            "ZAMFARA",
            "FCT",
            "ABUJA",
        ]
        for hint in state_hints:
            if hint in upper_title:
                return "FCT Abuja" if hint in {"FCT", "ABUJA"} else hint.title()
        return "Federal"

