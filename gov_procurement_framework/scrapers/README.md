# Adding a New Scraper

Use this process for every new procurement source.

## 1) Create the scraper file

- Copy `scraper_template.py` to `<source_key>.py`.
- Rename class `NewSourceScraper` to a source-specific class name.
- Set:
  - `source_name` (must match CLI registry key)
  - `source_url`

## 2) Implement source logic only

- `fetch()`:
  - Use `self.request_engine.request(...)`.
  - Do not use direct `aiohttp` in scrapers.
- `parse()`:
  - Convert raw response into source-native list items.
  - Do not normalize in this step.
- `normalize()`:
  - Map each parsed item to unified hierarchical schema:
    `Country -> State -> Ministry -> Tender -> Winning Company -> Company Details`.
  - Use `ensure_tender_schema(...)`.

## 3) Register scraper in CLI

In `gov_procurement_framework/cli.py`, update `_build_scraper_registry()`:

```python
from gov_procurement_framework.scrapers.my_source import MySourceScraper

def _build_scraper_registry() -> dict[str, type[BaseScraper]]:
    return {
        "nigeria_bpp": NigeriaBppScraper,
        "us_sam": UsSamScraper,
        "uk_contracts": UkContractsScraper,
        "my_source": MySourceScraper,
    }
```

## 4) Validate quickly

- Lint new files.
- Run compile check:
  - `python3 -m compileall gov_procurement_framework`
- Run CLI smoke test for the new source.

## Fast path (auto-generate + register)

Use the generator script:

- `python3 scripts/new_scraper.py --source-key kenya_ppra --source-url https://example.gov/feed`

This will:
- Create `gov_procurement_framework/scrapers/kenya_ppra.py`
- Add import and registry entry in `gov_procurement_framework/cli.py`

## Rules to Keep

- No retry/proxy/rate-limit logic in scraper files.
- No manual sleeps in scraper files.
- No print statements.
- Return unified tender schema records only.
