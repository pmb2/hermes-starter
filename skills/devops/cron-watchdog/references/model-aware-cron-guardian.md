# Model-Aware Cron Guardian

A companion pattern to the Cron Watchdog. While the watchdog handles schedule-level
monitoring (missed jobs after restart), the Guardian handles model-level availability:
pausing ALL LLM-dependent jobs when the API is down and resuming them when it recovers.

## Architecture

```
Cron Watchdog (schedule monitoring)        Cron Guardian (model monitoring)
         │                                          │
         │ detect missed jobs                       │ check model health every 15m
         │ re-fire if gap > 1.5x                    │ auto-pause jobs if model down
         │ report action taken                      │ auto-resume + gap report on recovery
         ▼                                          ▼
    Both work with: jobs.json (persistent state) ←─── Gateway (in-memory scheduler)
```

## Two-Tier Health Check

| Tier | Endpoint | Auth | Purpose |
|------|----------|------|---------|
| 1 | `GET /v1/models` | None (public) | Is the API reachable? |
| 2 | `POST /v1/chat/completions` | Bearer token | Does the key have credits? |

**Key insight:** The models endpoint returns 403 if you send an expired key. Omit auth
for Tier 1 (it's a public endpoint). Only send auth for Tier 2.

```python
# Tier 1 — no auth
req = urllib.request.Request(f"{API_BASE_URL}/models")
with urllib.request.urlopen(req, timeout=15) as resp:
    # If we get here, the API is alive

# Tier 2 — with auth
req = urllib.request.Request(f"{API_BASE_URL}/chat/completions", data=payload)
req.add_header("Authorization", f"Bearer {api_key}")
req.add_header("User-Agent", "curl/7.68.0")  # REQUIRED — avoids 403
```

## NEVER_PAUSE Blacklist

Infrastructure jobs must NEVER be paused or the system deadlocks:

- Cron Guardian itself (would stop monitoring)
- Guardian Angel (process watchdog)
- Cron Watchdog (schedule watchdog)
- Hermes System Backup
- PIM Ingestion (non-LLM data pipeline)
- tor-circuit-rotation (Tor circuit maintenance)

```python
NEVER_PAUSE = [
    "Cron Guardian", "Guardian Angel", "Cron Watchdog",
    "tor-circuit-rotation", "Hermes System Backup",
    "PIM Ingestion",
]
```

## Gap Bridge Report

On model recovery, generate a structured report of what was missed:

| Section | Content |
|---------|---------|
| Outage summary | Duration, cause, resolution |
| By category | Daily Ops, Intelligence, Real Estate, Legal, Finance, Cyber, etc. |
| Job counts | Total errored, by error type (429, connection, script timeout) |
| Corrective actions | What was done (repair, restore, pause/resume) |

## Implementation

The Cron Guardian is implemented as a `--no-agent` script that:
1. Uses Python stdlib only (urllib, subprocess, json, os, sys, time)
2. Runs on a 15-minute cron schedule
3. Maintains persistent state in `~/.hermes/cron/guardian_state.json`
4. Calls `hermes cron pause/resume` via subprocess
5. Generates gap reports to `~/.hermes/cron/gap-reports/`

## Relation to Other Watchdogs

| Tool | Scope | Technique | Model Needed? |
|------|-------|-----------|---------------|
| **Cron Watchdog** | Schedule compliance | Check last_run vs expected | No |
| **Guardian Angel** | Process health | Monitor PID, restart on crash | No |
| **Cron Guardian** | Model availability | Check API, pause/resume jobs | No |
| **Nightly Watchdog** | Overnight batch | Run updates, scan, report | Yes |

The Cron Guardian and Cron Watchdog are complementary: Guardian prevents error spam
during outages (by pausing BEFORE jobs run), and Watchdog catches genuine missed runs
after recovery (by checking last_run vs schedule).
