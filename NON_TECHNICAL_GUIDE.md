# Government Tender Project (Simple Guide)

## What this project is

This project is a tool that helps collect public government tender opportunities from different websites and put them into one clean, easy-to-use list.

Think of it like a smart assistant that:
- Visits tender websites for you
- Collects tender information
- Organizes everything into one standard format
- Saves the results into files you can open and share

## What it does

When you run this tool, it can:
- Pull tender notices from supported sources (for example, Kenya PPRA)
- Standardize the information (title, agency, deadline, etc.)
- Save results as:
  - JSON (good for systems/software)
  - CSV (good for Excel/Sheets)
- Keep activity logs so you can track what happened

## Data structure we use

- **Country -> State -> Ministry -> Tender -> Winning Company -> Company Details**

In simple terms:
- Each record starts with location and government unit (`country`, `state`, `ministry`)
- Then the tender itself (title, deadline, documents, etc.)
- Then the winning company (or "Not awarded yet")
- Then company details (address, contact, registration, and related fields)

## Available websites we can scrape right now

These are the current built-in sources:

- **Kenya PPRA / PPIP (Kenya)**  
  Website/API: `https://tenders.go.ke/api/active-tenders`
- **BPP Procurement Feed (Nigeria)**  
  Website/feed: `https://www.bpp.gov.ng/category/procurement/feed/`
- **Contracts Finder Feed (United Kingdom)**  
  Website/feed: `https://www.contractsfinder.service.gov.uk/Notices/RssFeed`

### Important note about US source

The `us_sam` scraper is currently wired to a placeholder demo endpoint for testing structure:

- `https://jsonplaceholder.typicode.com/posts`

This means it is useful for testing the pipeline, but it is **not** currently pulling live SAM.gov production notices.

## Why this is useful

Without this tool, you usually have to check many websites manually, copy details by hand, and clean inconsistent data.

With this tool, the process is faster, more consistent, and easier to repeat.

## How it works (in simple words)

The project is split into small parts that each do one job:

- **Collector**: fetches tender data from a source website
- **Safety layer**: handles internet slowdowns, retries failed requests, and controls request speed
- **Organizer**: converts source-specific data into one common structure
- **Exporter**: saves clean results into files (JSON/CSV)
- **Command tool**: lets you start everything from one simple command

This design makes it easier to add new tender sources later without rebuilding everything.

## What files you get after running

After a successful run, you will usually see:

- `output/...json` and/or `output/...csv`  
  (the tender results)
- `logs/scraper.log`  
  (general run events)
- `logs/error.log`  
  (errors, if any)
- `logs/performance.log`  
  (timing/performance details)

## How to run it (step by step)

### 1) Open terminal in the project folder

Make sure your terminal is inside this project folder.

### 2) Set up dependencies (one-time setup)

If using the provided virtual environment approach:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

### 3) Run a quick check (optional but recommended)

```bash
make ci-local
```

This runs lint checks, tests, and a quick command check.

### 4) Run a real scrape

Run this command:

```bash
PYTHONPATH="." .venv/bin/python -m gov_procurement_framework.cli scrape --export both --limit 10
```

Then follow the prompts:
- Choose country (from available countries)
- Choose ministry (from available ministries in that country)

After you select both, the tool generates output files.

### 5) Open results

Check the `output/` folder for files created during the run.

## Common questions

### "Can we add more countries/sources?"

Yes. The project is built to support more sources.  
A helper script can generate a new scraper file and register it automatically.

### "Do I need to understand coding to use it?"

Not deeply. If someone sets it up once, day-to-day use can be as simple as running one command and opening the output files.

### "What if something fails?"

The system keeps logs and has built-in retry and stability features.  
If something still fails, check the `logs/error.log` file first.

## Simple summary

This project is an automated tender data assistant: it collects, cleans, and saves procurement opportunities so teams can work from one trusted, consistent dataset.
