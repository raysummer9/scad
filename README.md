# Government Procurement Framework

Production-oriented, async-first scraping framework for government procurement sources.

<!-- Optional: replace owner/repo once remote is created -->
<!-- [![CI](https://github.com/owner/repo/actions/workflows/ci.yml/badge.svg)](https://github.com/owner/repo/actions/workflows/ci.yml) -->

## Start Here (Non-Technical)

If you want a plain-language explanation of what this project does and how to run it:

- See `NON_TECHNICAL_GUIDE.md`

## Quick Setup

1. Create and activate a virtual environment.
2. Install dependencies:
   - `python3 -m pip install -r requirements.txt`
3. Optional dev tooling (lint + CI parity):
   - `python3 -m pip install -r requirements-dev.txt`

## Run

- Guided mode (recommended):
  - `PYTHONPATH="." python3 -m gov_procurement_framework.cli scrape --export both --limit 10`
  - Then choose:
    - Country (from available countries)
    - Ministry (from ministries found in that country's records)
- Guided mode with preset country (skips country prompt):
  - `PYTHONPATH="." python3 -m gov_procurement_framework.cli scrape --country nigeria --export both --limit 10`
- Advanced source mode (optional):
  - `PYTHONPATH="." python3 -m gov_procurement_framework.cli scrape --source kenya_ppra --export both --limit 10`

## Supported Sources

- `kenya_ppra`: `https://tenders.go.ke/api/active-tenders`
- `nigeria_bpp`: multi-feed aggregator currently using:
  - `https://publicprocurement.ng/feed/`
  - `https://publicprocurement.ng/category/tender/feed/`
  - `https://publicprocurement.ng/category/pre-qualification-notice/feed/`
  - `https://publicprocurement.ng/category/expression-of-interest-eoi/feed/`
  - `https://publicprocurement.ng/category/general-procurement-notice/feed/`
- `uk_contracts`: `https://www.contractsfinder.service.gov.uk/Notices/RssFeed`
- `us_sam`: currently uses a placeholder endpoint for pipeline testing (`https://jsonplaceholder.typicode.com/posts`)

## Data Structure

All normalized output now follows this hierarchy:

- `Country -> State -> Ministry -> Tender -> Winning Company -> Company Details`

In JSON, each record includes:

- `country`, `state`, `ministry`
- `tender` (id, title, budget, dates, category, description, documents)
- `winning_company` (name, nested `company_details`)

## Add a New Source

- Auto-generate and register:
  - `python3 scripts/new_scraper.py --source-key kenya_ppra --source-url https://tenders.go.ke/api/active-tenders`

## Test

- Run test suite:
  - `PYTHONPATH="." python3 -m unittest discover -s tests -p "test_*.py" -v`
- Run lint:
  - `ruff check .`
- Local smoke check (CLI entrypoint):
  - `PYTHONPATH="." python3 -m gov_procurement_framework.cli --help`

## Developer Commands

- Install runtime deps:
  - `make install`
- Install dev deps:
  - `make install-dev`
- Lint:
  - `make lint`
- Tests:
  - `make test`
- Smoke:
  - `make smoke`
- Full local CI parity:
  - `make ci-local`

## Release Checklist

- Confirm branch is up to date and CI is green (`lint`, `test`, `smoke`).
- Run local parity before release:
  - `make ci-local`
- Validate a live scrape path for at least one source:
  - `PYTHONPATH="." python3 -m gov_procurement_framework.cli scrape --export both --limit 5`
- Review output artifacts:
  - `output/*.json` and `output/*.csv` contain valid unified schema rows.
- Review operational logs:
  - `logs/scraper.log`, `logs/error.log`, `logs/performance.log`
- Update documentation/changelog with new sources, behavior changes, and migration notes.
- Tag release version and publish.
