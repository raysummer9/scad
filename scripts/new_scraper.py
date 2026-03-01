"""Generate and register a new scraper from template."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRAPERS_DIR = ROOT / "gov_procurement_framework" / "scrapers"
TEMPLATE_PATH = SCRAPERS_DIR / "scraper_template.py"
CLI_PATH = ROOT / "gov_procurement_framework" / "cli.py"


def snake_to_pascal(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_") if part)


def validate_source_key(source_key: str) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", source_key):
        raise ValueError(
            "source_key must match pattern: [a-z][a-z0-9_]* "
            "(example: kenya_ppra)"
        )


def render_scraper(template_text: str, source_key: str, source_url: str) -> str:
    class_name = f"{snake_to_pascal(source_key)}Scraper"
    text = template_text.replace("class NewSourceScraper(BaseScraper):", f"class {class_name}(BaseScraper):")
    text = text.replace('source_name = "new_source_key"', f'source_name = "{source_key}"')
    text = text.replace('source_url = "https://example.gov/procurement-endpoint"', f'source_url = "{source_url}"')
    return text


def insert_import(cli_text: str, source_key: str, class_name: str) -> str:
    import_line = f"from gov_procurement_framework.scrapers.{source_key} import {class_name}"
    if import_line in cli_text:
        return cli_text

    marker = "from gov_procurement_framework.scrapers.base_scraper import BaseScraper"
    if marker not in cli_text:
        raise ValueError("Could not find scraper import marker in cli.py")

    return cli_text.replace(marker, f"{marker}\n{import_line}")


def insert_registry_entry(cli_text: str, source_key: str, class_name: str) -> str:
    entry = f'        "{source_key}": {class_name},'
    if entry in cli_text:
        return cli_text

    pattern = r"(def _build_scraper_registry\(\) -> dict\[str, type\[BaseScraper\]\]:\n\s+return \{\n)([\s\S]*?)(\n\s+\})"
    match = re.search(pattern, cli_text)
    if not match:
        raise ValueError("Could not locate _build_scraper_registry block in cli.py")

    prefix, body, suffix = match.group(1), match.group(2), match.group(3)
    lines = [line for line in body.splitlines() if line.strip()]
    lines.append(entry)
    lines = sorted(lines)
    new_body = "\n".join(lines)
    return f"{cli_text[:match.start()]}{prefix}{new_body}{suffix}{cli_text[match.end():]}"


def update_cli(source_key: str) -> None:
    class_name = f"{snake_to_pascal(source_key)}Scraper"
    cli_text = CLI_PATH.read_text(encoding="utf-8")
    cli_text = insert_import(cli_text, source_key, class_name)
    cli_text = insert_registry_entry(cli_text, source_key, class_name)
    CLI_PATH.write_text(cli_text, encoding="utf-8")


def create_scraper(source_key: str, source_url: str, overwrite: bool) -> Path:
    template_text = TEMPLATE_PATH.read_text(encoding="utf-8")
    rendered = render_scraper(template_text, source_key, source_url)

    output_path = SCRAPERS_DIR / f"{source_key}.py"
    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"{output_path} already exists. Use --overwrite to replace it."
        )

    output_path.write_text(rendered, encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a new scraper from template and register it in CLI."
    )
    parser.add_argument("--source-key", required=True, help="Snake_case source key")
    parser.add_argument("--source-url", required=True, help="Base source endpoint URL")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite scraper file if it already exists",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_source_key(args.source_key)

    create_scraper(args.source_key, args.source_url, args.overwrite)
    update_cli(args.source_key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

