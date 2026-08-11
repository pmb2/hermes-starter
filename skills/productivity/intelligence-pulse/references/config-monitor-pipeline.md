# Config-Driven Web Search Monitoring Pipeline

## Architecture

A config-driven pipeline that runs categorized web searches, scores results for relevance, and stores findings for downstream consumption (alert bridge, daily digest).

## Core Files

- `monitoring/config.yaml` — Category definitions, search queries per category, output paths
- `monitoring/run_monitor.py` — Reads config, runs DuckDuckGo + Google News RSS searches, scores, dedups, stores
- `monitoring/findings/latest.json` — Most recent run's findings (ALL categories if run together)
- `monitoring/findings/history.jsonl` — Append-only log of all findings (fingerprint-deduped)

## Config Structure

```yaml
monitor:
  enabled_categories:
    - domain_one          # descriptive domain name, not strategic bucket
    - domain_two
    - opportunity_signals # wildcard catch-all — always include one

  search_queries:
    domain_one:
      - "specific search query one"
      - "specific search query two"
    domain_two:
      - "another query"
    opportunity_signals:
      - "broad trend query"
      - "adjacent market query"
      - "wildcard opportunity query"

  check_interval_hours: 24
  max_results_per_query: 5
  output_dir: "monitoring/findings/"
  state_file: "monitoring/monitor_state.json"
```

## Category Naming Rule

Name categories by the **domain they describe** (`fl_land_intel`, `govcon_c2c_intel`), not by which strategic track they serve. This keeps monitoring flexible across shifting priorities.

## Relevance Scoring

The scoring function in `run_monitor.py` uses keyword matching per category. Business categories score lower (0.30-0.60) because they lack the name-bonus keywords (e.g., "Trump") that inflate political/celebrity categories. Set category-specific thresholds in downstream consumers.

## Running

```bash
# Run all enabled categories
python monitoring/run_monitor.py

# Run specific categories (each overwrites latest.json!)
python monitoring/run_monitor.py --category fl_land_intel
python monitoring/run_monitor.py --category govcon_c2c_intel

# Run all categories together (preserves latest.json)
python monitoring/run_monitor.py --timeout 300

# Dry run
python monitoring/run_monitor.py --dry-run
```

## Pitfall: Sequential Category Runs Overwrite latest.json

When running categories individually, each invocation overwrites `latest.json` with only that category's results. The append-only `history.jsonl` preserves everything. Downstream consumers should read from history when latest.json is incomplete.

## Finding Storage

Each finding record:
```json
{
  "date": "2026-06-22T10:03:06+00:00",
  "category": "govcon_c2c_intel",
  "source": "duckduckgo",
  "headline": "Table of effective dates for MPT and SAT - Acquisition.GOV",
  "snippet": "Your 2026 guide to the Simplified Acquisition Threshold...",
  "url": "https://www.acquisition.gov/tableofeffectivedatesforMPTandSAT",
  "relevance_score": 0.60,
  "fingerprint": "sha256[:16]"
}
```

## Example: trumpian-accounting-kb (10 categories)

Runs daily at 6:30am ET. Categories:
- 7 Trump/KB: nyag_civil, criminal, trump_org, forbes, djt, real_estate, regulatory
- 3 Business Intel: fl_land_intel, govcon_c2c_intel, opportunity_signals

Cron: `30 6 * * *` runs `cd ${USER_HOME}/trumpian-accounting-kb && python monitoring/run_monitor.py`
