# Cron Health Scan Patterns (PATH-independent)

Verified 2026-08-05 while debugging `dream_cycle.py` (Hermes Dream Cycle cron job).
These patterns make cron-state reads reliable inside ANY environment — including
the cron runner itself, where `hermes` is NOT on PATH.

## Rule 1: Never shell out to `hermes cron list` from a cron-run script

Inside the cron runner environment PATH is minimal; `hermes cron list` returns
empty, so a `grep -c '[active]'` probe reports **0 active jobs** while 68 run.
This silently breaks every inventory/watchdog that counts via the CLI.

## Rule 2: Read `~/AppData/Local/hermes/cron/jobs.json` directly

Python `json.load` — no subprocess. Job entry keys that matter:

| Key | Meaning / gotcha |
|---|---|
| `enabled` | primary gate — `False` even when `paused_at` is null |
| `state` | `scheduled` (96), `completed` (one-shot done), or null |
| `paused_at` | null for enabled jobs; not the disable indicator |
| `last_status` | `ok` / `error` / `scheduled` (never ran) |
| `last_error` | full error string from the most recent failed run |
| `model_snapshot` / `provider_snapshot` | values baked in at creation — compare against current global config to detect drift |
| `schedule` | dict with `kind` (interval/cron) + `display` |

Active-count filter that matches the CLI's `[active]` total:
```python
active = [j for j in jobs if j.get("enabled")
          and j.get("state") in ("scheduled", "idle", None)
          and not j.get("paused_at")]
```
(Aug 2026: 98 total in jobs.json → 68 active; CLI shows the same 68.)

## Failure taxonomy (error signatures + classification)

Classify `last_error` strings by substring — verified against a real fleet:

| Class | Signature | Counts seen |
|---|---|---|
| config-drift spend guard | `Skipped to prevent unintended spend` / `config drifted` | 6 jobs |
| rate-limit / quota | `HTTP 429` or `Monthly usage limit reached. Resets in N days` | 12 jobs |
| idle timeout | `idle for 600s (limit 600s) — waiting for non-streaming API response` | 3 jobs |
| script timeout | `Script timed out after 3600s` | 1 job |
| MSYS script-path bug | `code 127` + `/bin/bash: C:Users/<you>...` (backslashes stripped) | 3 jobs |
| script exit code | `Script exited with code 1/2` | 2 jobs |
| connection | `Connection error.` | 1 job |

Key insight: `last_status` alone under-reports — a job can show `last_status: ok`
while a stale `last_error` persists from an earlier failed run. Scan `last_error`,
not just `last_status`.

## Config-drift spend guard (drift-blocked jobs)

When the global inference config changes (e.g. model `auto/best-coding` →
`gpt-5.6-sol`), every UNPINNED job fails its tick with
`RuntimeError: Skipped to prevent unintended spend ... job is unpinned`.
Deliberate spend guard, not an outage. Remediation per the error message:
`cronjob action=update job_id=<id> provider=<provider> model=<model>` (pin to
current config) or pin the original snapshot values to preserve behavior.
Pinning is a spend-relevant decision — report with the exact command, let the
user choose, unless explicitly authorized to align with the global config.

## Bulk scan recipe (one pass over jobs.json)

```python
import json
from pathlib import Path
from collections import Counter

jobs = json.loads((Path.home() / "AppData/Local/hermes/cron/jobs.json")
                  .read_text(encoding="utf-8"))
items = jobs.get("jobs", jobs)
if isinstance(items, dict):
    items = list(items.values())

print("states:", Counter(j.get("state") for j in items))
print("last_status:", Counter(str(j.get("last_status")) for j in items if j.get("last_status")))
for j in items:
    err = str(j.get("last_error") or "")
    if err:
        print(j.get("id"), "|", j.get("name"), "|", err[:120])
```

## Worked example

`~/AppData/Local/hermes/scripts/dream_cycle.py` was fixed to use these patterns:
`list_cron_jobs()` reads jobs.json (CLI fallback), `scan_cron_health()` classifies
`last_error` into the taxonomy above and reports per-class counts. Re-run it after
any fleet-wide config change to see drift/429 fallout in one shot.
