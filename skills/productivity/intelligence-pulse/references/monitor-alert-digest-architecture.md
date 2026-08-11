# Alert Bridge + Daily Digest Architecture

## Purpose

Convert raw findings from a file-based monitoring pipeline into delivered intelligence. Two complementary patterns:

- **Alert Bridge**: Fires immediately when a high-relevance finding appears (every 4h)
- **Daily Digest**: Consolidated brief of everything notable in the last 24h (daily 6am)

Both are no_agent=True cron scripts — pure data transformation with zero LLM cost.

## Alert Bridge Pattern

### Script Structure

```python
#!/usr/bin/env python3
"""
Reads latest.json + history.jsonl for business-category findings above threshold.
Only prints output (triggering cron delivery) when there's genuinely new signal.
"""
# Config
BUSINESS_CATS = {"fl_land_intel", "govcon_c2c_intel", "opportunity_signals"}
ALERT_THRESHOLD = 0.40  # lower for non-Trump categories

# Load state (dedup fingerprints)
state = load_state("findings/alert_state.json")
last_fp = state.get("last_alerted_fp", "")

# Load findings from latest.json + history.jsonl (last 48h)
findings = load_latest_with_history_fallback("findings/")

# Filter to high-relevance business signals
hits = [f for f in findings 
        if f["category"] in BUSINESS_CATS 
        and f["relevance_score"] >= ALERT_THRESHOLD]

if not hits:
    return  # silent — nothing to alert

# Skip if it's the same item we already alerted
top = sorted(hits, key=lambda x: x["relevance_score"], reverse=True)[0]
if top["fingerprint"] == last_fp:
    return  # silent — already alerted this

# Format and deliver
print(format_alert(top, hits[1:4]))
save_state({"last_alerted_fp": top["fingerprint"], ...})
```

### State Management

```json
// findings/alert_state.json
{
  "last_alerted_fp": "a1b2c3d4e5f6g7h8",
  "last_alerted_at": "2026-06-22T10:03:06+00:00",
  "last_headline": "Table of effective dates for MPT and SAT"
}
```

Single-fingerprint state is sufficient because the bridge alerts on the highest-relevance item each cycle. The fingerprint prevents re-alerting the same article. When a genuinely new higher-relevance item appears, its different fingerprint triggers delivery.

## Daily Digest Pattern

### Script Structure

```python
#!/usr/bin/env python3
"""
Reads all monitoring categories, dedups against previously-reported items,
groups by category, and produces a scannable morning brief.
"""
BUSINESS_CATS = {"fl_land_intel", "govcon_c2c_intel", "opportunity_signals"}
TRUMP_CATS = {"nyag_civil", "criminal", ..., "regulatory"}
CAT_LABELS = {"fl_land_intel": "FL Land Intel", ...}

# Load dedup state
state = load_state("findings/daily_brief_state.json")
seen_fps = set(state.get("reported_fingerprints", []))

# Load + dedup
findings = load_latest_with_history_fallback("findings/", hours=48)
fresh = [f for f in findings if f["fingerprint"] not in seen_fps]

# Split business vs high-signal Trump
biz = [f for f in fresh if f["category"] in BUSINESS_CATS]
trump = [f for f in fresh if f["category"] in TRUMP_CATS and f["relevance_score"] >= 0.6]

if not biz and not trump:
    return  # silent

# Format per-category sections
output = []
output.append(f"Business Intel Digest - {date}")
for cat in ["fl_land_intel", "govcon_c2c_intel", "opportunity_signals"]:
    items = [f for f in biz if f["category"] == cat]
    if items:
        output.append(f">> {label} ({len(items)} items)")
        for item in sorted(items, key=lambda x: x["relevance_score"], reverse=True)[:5]:
            output.append(f"  [{item['relevance_score']:.2f}] {item['headline'][:120]}")
            if item.get('url'):
                output.append(f"     {item['url']}")

# Update state
state["reported_fingerprints"] = list(seen_fps | new_fps)
print("\n".join(output))
```

### Dedup Strategy

Use SHA-256 fingerprint (truncated to 16 chars) of `url|title` as the dedup key. Store reported fingerprints in a state JSON. On each run:
1. Load all findings from latest 48h
2. Skip anything whose fingerprint is already in state
3. Report only the fresh items
4. Append new fingerprints to state

This prevents the same article from appearing in consecutive digests. State grows monotonically but typical findings volume (50-150 items/day) means <55K fingerprints/year — negligible storage.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **no_agent=True** | Pure data transformation — no LLM needed. Cheaper, faster, deterministic |
| **Fingerprint dedup** | URL+title hash is simple and effective. Content changes produce new fingerprints |
| **history.jsonl fallback** | latest.json gets overwritten on sequential category runs; history is append-only |
| **Category-specific thresholds** | Scoring algorithm biases toward name-bonus terms; non-Trump categories score lower |
| **Silent when nothing new** | Follows the "watchdog pattern" — don't deliver empty reports |

## Example Implementations

- `daily_business_intel.py` — Daily digest at `~/AppData/Local/hermes/scripts/daily_business_intel.py` (6am daily)
- `business_alert_bridge.py` — Alert bridge at `~/AppData/Local/hermes/scripts/business_alert_bridge.py` (every 4h)

Both monitor findings in `${USER_HOME}/trumpian-accounting-kb/monitoring/findings/`.
