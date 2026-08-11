# Direct SQLite Query Pattern for CLI-Limited Tools

When a project's CLI tools don't support date-filtered output (e.g. `leads --limit 10` with no `--days` flag), the CLI returns all-time data — making daily/weekly delta detection impossible from CLI alone.

**Fallback:** query the project's SQLite database(s) directly with SQL for accurate date-bounded aggregation.

## When to Use

- The CLI command lacks a `--days` or `--since` filter
- The output shows data from months ago but you need today/yesterday counts
- You need to aggregate by source/category across date boundaries
- You need to compare two time windows (today vs yesterday)

## Discovery

```python
from pathlib import Path
import sqlite3

# Find all SQLite databases in the project tree
db_dir = Path("/path/to/project")
db_files = list(db_dir.rglob("*.db")) + list(db_dir.rglob("*.sqlite"))

# Inspect each database
for db_path in db_files:
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    tables = c.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    print(f"{db_path}: tables={[t[0] for t in tables]}")
    conn.close()
```

## Date-Bounded Aggregation (Standard Pattern)

```python
import sqlite3
from datetime import datetime, timezone, timedelta

today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

conn = sqlite3.connect("path/to/data.db")
c = conn.cursor()

# Count today's leads by source
rows = c.execute("""
    SELECT source, COUNT(*) as cnt
    FROM lead_events
    WHERE created_at >= ? AND created_at < ?
    GROUP BY source
""", (today, yesterday)).fetchall()

# Group by date for any table with a date column
rows = c.execute("""
    SELECT strftime('%Y-%m-%d', created_at) as dt, COUNT(*) as cnt
    FROM lead_events
    GROUP BY dt ORDER BY dt DESC LIMIT 10
""").fetchall()
```

## Watch for Separate DBs

A project may have multiple databases serving different purposes. Example from Website Landlord:

| DB | Purpose | Key Tables |
|----|---------|------------|
| `data/landlord.db` | Lead events, calls, forms, route decisions | `lead_events`, `call_events`, `form_submissions`, `route_decisions` |
| `data/leads/leads.db` | Scraped business prospects from Google Maps | `leads` (uses `scraped_at`, not `created_at`) |

Always check column names — date columns vary (`created_at`, `scraped_at`, `updated_at`, `checked_at`).

## For Systems Without --days Flag

If a CLI tool's only filtering option is `--limit`, you cannot get accurate daily counts from the CLI alone. The `--limit` just returns the N most recent total — if the system has 4 total leads from 2 months ago, `--limit 10` shows those same 4 regardless of date.

**Direct DB query is the only reliable way** to answer "how many leads today vs yesterday?" in this scenario.

## Pitfalls

- **Date column name differs by table** — `lead_events` uses `created_at`, `leads` uses `scraped_at`. Always `PRAGMA table_info(table)` first to discover column names.
- **Date format varies** — some stores use ISO 8601 (`2026-07-12T01:02:05Z`), others use without `Z` or with timezone offset. `strftime('%Y-%m-%d', col)` handles most formats.
- **SQLite row factory** — `sqlite3.Row` enables dict-like access but `dict(row)` fails on some versions. Use `{k: row[k] for k in row.keys()}` as fallback.
- **LIKE for date prefix matching** — `WHERE created_at LIKE '2026-07-12%'` is simpler than date range comparisons when both formats are ISO 8601.
- **Database may not exist** — if the project hasn't run its init/setup yet, `.db` files may be missing. Gracefully handle FileNotFoundError.
- **Case-sensitivity** — SQLite identifiers are case-insensitive, but column name casing matters when using `row[k]` dict access.
