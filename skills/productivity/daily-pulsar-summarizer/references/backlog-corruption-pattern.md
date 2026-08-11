# Backlog Corruption Pattern

## Observed: July 19, 2026

The `unseen-backlog.json` contained 156 items, all structurally corrupted — every entry had:
- `header: "?"`
- `source_ref: "?"` (or absent)
- No meaningful content

Despite a `stats` count of 156 total / 156 unseen / 0 seen, the effective signal was zero.

## Detection Commands

```bash
# Count structurally empty entries
python -c "
import json
with open('${MY_REPOS}/_project/daily-digest/unseen-backlog.json') as f:
    d = json.load(f)
items = d.get('items', d.get('backlog', []))
bad = [i for i in items if i.get('header','?') == '?' or not i.get('source_ref','')]
print(f'{len(bad)}/{len(items)} entries have empty headers or sources')
"

# Show worst offenders by category
python -c "
import json
with open('${MY_REPOS}/_project/daily-digest/unseen-backlog.json') as f:
    d = json.load(f)
items = d.get('items', d.get('backlog', []))
bad = [i for i in items if i.get('header','?') == '?']
by_prio = {}
for i in bad:
    p = i.get('priority','?')
    by_prio[p] = by_prio.get(p, 0) + 1
for p, c in sorted(by_prio.items()):
    print(f'  {p}: {c} corrupted entries')
"
```

## Root Cause

The `unseen-backlog.py add` command was called with missing or truncated parameters. Most likely: a Pulsar script invocation where argument parsing dropped the header string (e.g., MSYS path issue, pipe buffering, or shell quoting edge case).

## Cleanup Strategy

1. **Do NOT add items to a corrupted backlog** — each add compounds the problem
2. **Flag the corruption** in the PULSAR delivery as a system health issue
3. **Next steps for the operator:**
   - Option A: `rm unseen-backlog.json` and restart fresh (cleanest)
   - Option B: Write a dedup script that discards entries where `header == "?"` or `source_ref == "?"`
   - Option C: Acknowledge all corrupted entries in bulk, then rebuild from recent digest entries

## Prevention

- Always pass a real header string (20-80 chars) when calling `add`
- Never call `add` in a loop where the header string comes from a potentially-empty variable
- After every batch of `add` calls, run `stats` and spot-check 1-2 entries via `list`
- If `stats` reports unseen count growing faster than expected, stop and investigate before adding more
