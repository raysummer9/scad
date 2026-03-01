"""CSV export implementation for normalized tender records."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


CSV_COLUMNS = [
    "source",
    "scraped_at",
    "country",
    "state",
    "ministry",
    "tender_id",
    "tender_title",
    "tender_budget",
    "tender_currency",
    "tender_published_date",
    "tender_closing_date",
    "tender_category",
    "tender_description",
    "tender_documents",
    "winning_company_name",
    "company_registration_number",
    "company_address",
    "company_email",
    "company_phone",
    "company_website",
    "company_country",
    "company_state",
]


class CsvExporter:
    """Write normalized tender records as flattened CSV rows."""

    def __init__(self, output_dir: str = "output") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, data: list[dict[str, Any]], filename: str) -> None:
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for item in data:
                tender = item.get("tender", {}) if isinstance(item.get("tender"), dict) else {}
                winning_company = (
                    item.get("winning_company", {})
                    if isinstance(item.get("winning_company"), dict)
                    else {}
                )
                company_details = (
                    winning_company.get("company_details", {})
                    if isinstance(winning_company.get("company_details"), dict)
                    else {}
                )

                row: dict[str, Any] = {
                    "source": item.get("source"),
                    "scraped_at": item.get("scraped_at"),
                    "country": item.get("country"),
                    "state": item.get("state"),
                    "ministry": item.get("ministry"),
                    "tender_id": tender.get("tender_id"),
                    "tender_title": tender.get("title"),
                    "tender_budget": tender.get("budget"),
                    "tender_currency": tender.get("currency"),
                    "tender_published_date": tender.get("published_date"),
                    "tender_closing_date": tender.get("closing_date"),
                    "tender_category": tender.get("category"),
                    "tender_description": tender.get("description"),
                    "tender_documents": json.dumps(
                        tender.get("documents", []), ensure_ascii=True
                    ),
                    "winning_company_name": winning_company.get("name"),
                    "company_registration_number": company_details.get("registration_number"),
                    "company_address": company_details.get("address"),
                    "company_email": company_details.get("email"),
                    "company_phone": company_details.get("phone"),
                    "company_website": company_details.get("website"),
                    "company_country": company_details.get("country"),
                    "company_state": company_details.get("state"),
                }
                writer.writerow(row)

