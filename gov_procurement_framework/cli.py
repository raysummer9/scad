"""Command-line interface for framework orchestration."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import re
from typing import Any

from gov_procurement_framework.config import EXPORT_DEFAULT_FORMAT
from gov_procurement_framework.core.controller import Controller
from gov_procurement_framework.core.logger import get_logger
from gov_procurement_framework.core.proxy_manager import ProxyManager
from gov_procurement_framework.exporters.csv_exporter import CsvExporter
from gov_procurement_framework.exporters.json_exporter import JsonExporter
from gov_procurement_framework.scrapers.base_scraper import BaseScraper
from gov_procurement_framework.scrapers.kenya_ppra import KenyaPpraScraper
from gov_procurement_framework.scrapers.nigeria_bpp import NigeriaBppScraper
from gov_procurement_framework.scrapers.uk_contracts import UkContractsScraper
from gov_procurement_framework.scrapers.us_sam import UsSamScraper

SOURCE_COUNTRY_MAP = {
    "kenya_ppra": "Kenya",
    "nigeria_bpp": "Nigeria",
    "uk_contracts": "United Kingdom",
    "us_sam": "United States",
}
ALL_MINISTRIES_OPTION = "All ministries"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Government procurement scraping CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape = subparsers.add_parser("scrape", help="Run scraper for a source")
    scrape.add_argument(
        "--source",
        required=False,
        help="Source key from registry or 'all'. Omit for guided country/ministry selection.",
    )
    scrape.add_argument(
        "--country",
        required=False,
        help="Preset country for guided mode (e.g. nigeria). Skips country prompt.",
    )
    scrape.add_argument(
        "--export",
        choices=["json", "csv", "both"],
        default=EXPORT_DEFAULT_FORMAT,
        help="Export format",
    )
    scrape.add_argument("--limit", type=int, default=None, help="Record limit")
    scrape.add_argument(
        "--proxy-file",
        default=None,
        help="Path to newline-separated proxy file",
    )
    return parser


def _build_filename(source: str, extension: str) -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y_%m_%d")
    return f"{source}_{date_part}.{extension}"


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "_", lowered)
    return lowered.strip("_") or "unknown"


def _prompt_choice(label: str, options: list[str]) -> str:
    if not options:
        raise ValueError(f"No options available for {label}")
    lines = [f"Choose {label}:"]
    for idx, option in enumerate(options, start=1):
        lines.append(f"{idx}) {option}")
    lines.append("Enter number: ")
    prompt = "\n".join(lines)

    while True:
        raw = input(prompt).strip()
        if not raw.isdigit():
            continue
        idx = int(raw)
        if 1 <= idx <= len(options):
            return options[idx - 1]


def _resolve_country_choice(raw_country: str, available_countries: list[str]) -> str:
    normalized_map = {
        _slugify(country): country for country in available_countries
    }
    key = _slugify(raw_country)
    if key in normalized_map:
        return normalized_map[key]
    raise ValueError(
        f"Unknown country preset: {raw_country}. "
        f"Available: {', '.join(sorted(available_countries))}"
    )


def _resolve_sources(requested_source: str, known_sources: list[str]) -> list[str]:
    if requested_source == "all":
        return known_sources
    if requested_source not in known_sources:
        raise ValueError(f"Unknown source: {requested_source}")
    return [requested_source]


def _build_scraper_registry() -> dict[str, type[BaseScraper]]:
    return {
        "kenya_ppra": KenyaPpraScraper,
        "nigeria_bpp": NigeriaBppScraper,
        "uk_contracts": UkContractsScraper,
        "us_sam": UsSamScraper,
    }


async def _fetch_records_for_sources(
    controller: Controller,
    registry: dict[str, type[BaseScraper]],
    sources: list[str],
    limit: int | None,
    logger_name: str = "gov_procurement",
) -> list[dict[str, Any]]:
    logger = get_logger(logger_name)
    all_records: list[dict[str, Any]] = []
    for source in sources:
        scraper_cls = registry.get(source)
        if scraper_cls is None:
            continue

        def scraper_factory(request_engine, cls=scraper_cls):
            return cls(request_engine)

        try:
            source_records = await controller.run_scraper(scraper_factory, limit=limit)
            all_records.extend(source_records)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "scraper_source_failed",
                extra={
                    "extra_payload": {
                        "source": source,
                        "error": str(exc),
                    }
                },
            )
    return all_records


def _group_sources_by_country(sources: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for source in sources:
        country = SOURCE_COUNTRY_MAP.get(source, "Unknown Country")
        grouped.setdefault(country, []).append(source)
    return grouped


async def _run_interactive_scrape(
    args: argparse.Namespace,
    controller: Controller,
    registry: dict[str, type[BaseScraper]],
    json_exporter: JsonExporter,
    csv_exporter: CsvExporter,
) -> int:
    logger = get_logger("gov_procurement")
    grouped = _group_sources_by_country(sorted(registry.keys()))
    available_countries = sorted(grouped.keys())
    if args.country:
        selected_country = _resolve_country_choice(args.country, available_countries)
    else:
        selected_country = _prompt_choice("country", available_countries)
    country_sources = grouped[selected_country]

    records = await _fetch_records_for_sources(
        controller=controller,
        registry=registry,
        sources=country_sources,
        limit=args.limit,
    )
    if not records:
        print("No records found for selected country.")
        print("Try another country.")
        logger.error(
            "interactive_no_records",
            extra={
                "extra_payload": {
                    "country": selected_country,
                    "detail": "No records available for selected country.",
                }
            },
        )
        return 1

    ministries = sorted(
        {
            str(record.get("ministry")).strip()
            for record in records
            if record.get("ministry")
        }
    )
    if not ministries:
        print("No ministries found.")
        print("Try another country.")
        logger.error(
            "interactive_no_ministries",
            extra={
                "extra_payload": {
                    "country": selected_country,
                    "detail": "No ministry values found in records.",
                }
            },
        )
        return 1

    ministry_options = [ALL_MINISTRIES_OPTION, *ministries]
    selected_ministry = _prompt_choice("ministry", ministry_options)
    if selected_ministry == ALL_MINISTRIES_OPTION:
        filtered_records = records
        output_base = f"{_slugify(selected_country)}_all_ministries"
    else:
        filtered_records = [
            record for record in records if str(record.get("ministry")).strip() == selected_ministry
        ]
        output_base = f"{_slugify(selected_country)}_{_slugify(selected_ministry)}"
    if not filtered_records:
        print("No records found for selected country.")
        print("No ministries found.")
        print("Try another country.")
        logger.error(
            "interactive_no_records_after_filter",
            extra={
                "extra_payload": {
                    "country": selected_country,
                    "ministry": selected_ministry,
                }
            },
        )
        return 1

    if args.export in ("json", "both"):
        json_exporter.export(filtered_records, _build_filename(output_base, "json"))
    if args.export in ("csv", "both"):
        csv_exporter.export(filtered_records, _build_filename(output_base, "csv"))
    return 0


async def _run_scrape_command(args: argparse.Namespace) -> int:
    proxy_manager = ProxyManager(proxy_file=args.proxy_file)
    controller = Controller(proxy_manager=proxy_manager)

    json_exporter = JsonExporter()
    csv_exporter = CsvExporter()

    registry = _build_scraper_registry()
    if args.source:
        requested_sources = _resolve_sources(args.source, sorted(registry.keys()))
        for source in requested_sources:
            records = await _fetch_records_for_sources(
                controller=controller,
                registry=registry,
                sources=[source],
                limit=args.limit,
            )
            if args.export in ("json", "both"):
                json_exporter.export(records, _build_filename(source, "json"))
            if args.export in ("csv", "both"):
                csv_exporter.export(records, _build_filename(source, "csv"))
        return 0

    return await _run_interactive_scrape(
        args=args,
        controller=controller,
        registry=registry,
        json_exporter=json_exporter,
        csv_exporter=csv_exporter,
    )


async def _dispatch(args: argparse.Namespace) -> int:
    if args.command == "scrape":
        return await _run_scrape_command(args)
    raise ValueError(f"Unsupported command: {args.command}")


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    try:
        return asyncio.run(_dispatch(args))
    except Exception as exc:  # noqa: BLE001
        logger = get_logger("gov_procurement")
        logger.error(
            "cli_execution_failed",
            extra={"extra_payload": {"error": str(exc)}},
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

