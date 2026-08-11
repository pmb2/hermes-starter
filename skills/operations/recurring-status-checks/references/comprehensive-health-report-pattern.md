# Comprehensive Health Report Pattern (Dream Cycle)

A multi-layer system health aggregation that combines inventory, gbrain, guardian, gap reports, and cron output analysis into a single actionable report. Use for daily/weekly system health checks that span the full Hermes ecosystem.

## Data Sources (in order)

| Source | Tool | What It Provides |
|--------|------|------------------|
| Pre-run script | Terminal | Skills count, MCP server list, cron job count, gap summary |
| GBrain Health | `get_health` | Brain score, embed coverage, orphan count, stale pages |
| GBrain Doctor | `run_doctor` | Status checks, top issues, schema version, queue health, sync failures |
| GBrain Stats | `get_stats` | Pages by type, chunk count, link count |
| Guardian State | `guardian_state.json` | Last outage window, recovery count, current health status |
| Gap Reports | `gap-reports/` | Detailed outage logs, error counts, rate-limit analysis |
| Cron Output | `cron/output/` | Recent job activity, output files per job |
| GBrain Salience | `get_recent_salience` | Recently touched pages and emotional salience |

## Collection Steps

### Phase 1: Inventory (always first)
Collect from the pre-run script or direct terminal commands:
- Skills count + any notable new/removed skills
- MCP server count + list
- Cron job count (0 means paused/completed — check jobs.json for actual definition count)

### Phase 2: GBrain Health
```python
get_health()  # brain_score, embed_coverage, orphans, stale pages
run_doctor()  # structured issues, sync_failures, schema_version
get_stats()   # pages_by_type, chunk_count, link_count
```

Key thresholds to flag:
- **brain_score < 60** — unhealthy, likely needs enrichment
- **orphan_pages == page_count** — 100% orphan rate, no internal linking
- **sync_failures > 0** — stale sync state, needs `gbrain sync --skip-failed`
- **embed_coverage < 1.0** — missing embeddings

### Phase 3: Guardian & Outage History
Read guardian state from `guardian_state.json`:
```bash
cat ~/AppData/Local/hermes/cron/guardian_state.json
```

Key fields:
- `last_healthy_at` — when system was last fully healthy
- `last_down_at` — most recent outage start
- `recovery_count` — how many times the guardian has auto-recovered
- `was_paused` — whether jobs were auto-paused during outage

### Phase 4: Gap Report Analysis
Read the 1-2 most recent gap reports from `gap-reports/`:
```bash
ls -t ~/AppData/Local/hermes/cron/gap-reports/ | head -2
```

For each gap report, extract:
- **Outage duration** — start/end timestamps, total hours
- **Error counts** — HTTP 429 rate limits vs script failures vs timeouts
- **Consecutive pattern detection** — if the same error type (e.g., 429) appears across multiple reports, it's systemic, not transient
- **Model rate-limit clustering** — if multiple diverse job categories (ai-sharp, finance, data-scrub, bots) all hit 429 simultaneously, it's a provider-level quota issue

### Phase 5: Cron Output Activity
Count output files and assess recent activity:
```bash
ls ~/AppData/Local/hermes/cron/output/ 2>/dev/null | wc -l
```

Group by job ID to see which jobs are producing output and which are silent.

### Phase 6: GBrain Activity
```python
get_recent_salience(days=7, limit=10)  # what's been touched recently
list_pages(sort="updated_desc", limit=10)  # recent page updates
```

## Report Structure

```
## 🌙 [TITLE] — YYYY-MM-DD

### 📋 Inventory Snapshot
| Metric | Value |
|--------|-------|
| Skills installed | N |
| MCP servers configured | N |
| Active cron jobs | N |
| GBrain pages | N |
| GBrain health score | N/100 |

### 🔄 System Health
- Guardian status: health/state/recovery count
- Previous outages: each window with duration and error summary
- GBrain issues: brain_score, orphans, sync failures, staleness

### 🔍 Gap Analysis
**Critical:** None detected (or list critical issues)
**Moderate:** Issues with moderate impact
**Suggestions:** Recommended new MCP servers, integrations, config changes

### 🔧 Action Items
1. Concrete next step — why it matters
2. Another step — what to run and why
...
```

## Pitfalls

- **Don't skip Phase 1.** Always start with inventory — it sets the baseline and reveals if anything major changed since last run.
- **Don't rely on gbrain alone.** A healthy gbrain doesn't mean the guardian is OK, and vice versa. Cross-reference all layers.
- **Don't miss consecutive outage patterns.** When 14/24 errors are the same type (429) across different job categories, that's a systemic provider quota issue, not N unrelated failures. Flag it as such.
- **Don't report stale gap data.** Check file timestamps on gap reports — if the most recent report is from before the last guardian recovery, supplement with the guardian's current state.
- **Don't assume 0 cron jobs = nothing happening.** Check `jobs.json` size and output directories — jobs may be defined but paused, or run as no_agent scripts outside the LLM loop.
- **Don't re-report the same findings identically.** If the previous dream cycle had the same brain_score and issues, the delta is the action items — prioritize escalation if issues persist across consecutive cycles.
- **Report deltas, not full repeats.** When the system state hasn't changed materially, note it briefly and escalate any persistent issues. A carbon-copy report wastes attention.
