# Unseen Backlog Script API

## Script Location

```
${MY_REPOS}\Documents\github\_project\scripts\unseen-backlog.py
```

## Commands

### add

Add an item to the backlog.

```bash
python ${MY_REPOS}/_project/scripts/unseen-backlog.py add \
  "<source_pulse>" <priority> <category> "<summary>" "<citation>"
```

| Field | Values |
|-------|--------|
| `source_pulse` | Name of the pulse that produced this item (e.g. "Self-Healing Pulse", "Daily Pulsar") |
| `priority` | `critical`, `high`, `medium`, `low`, `fyi` |
| `category` | `action`, `important`, `improvement`, `infra`, `bizdev`, `intel`, `project` |
| `summary` | Brief one-line description |
| `citation` | Reference to the source (e.g. `daily-digest/2026-06-04.md`) |

**Output format:**
```
[Backlog] Saved — N total items
[Backlog] Added item <8ch_id>: [PRIORITY] Summary text
```

The `<8ch_id>` is the item UUID — capture it if you need to `mark-seen` later.

### list

List backlog items with optional filters.

```bash
python ${MY_REPOS}/_project/scripts/unseen-backlog.py list
python ${MY_REPOS}/_project/scripts/unseen-backlog.py list --unseen-only
python ${MY_REPOS}/_project/scripts/unseen-backlog.py list --unseen-only --priority=critical
python ${MY_REPOS}/_project/scripts/unseen-backlog.py list --category=bizdev
```

**Output format (NOT JSON — line-based text):**
```
○ abc12345 [CRITICAL] Summary of the item
       Source: Pulse Name — daily-digest/2026-06-04.md#citation
○ def67890 [HIGH] Another item
       Source: Pulse Name — daily-digest/2026-06-04.md#citation
```

**Parsing tips:**
- Count by priority: `grep -c "\[CRITICAL\]"` or `grep -c "\[HIGH\]"`
- Extract item IDs: `grep "^○" | sed 's/^○ //' | awk '{print $1}'`
- This is NOT JSON — do not attempt `json.loads()` on the output
- The `○` is Unicode U+25CB (WHITE CIRCLE); unseen items use this, seen items use `●` (U+25CF, BLACK CIRCLE)

### mark-seen

Mark an item as acknowledged by the operator.

```bash
python ${MY_REPOS}/_project/scripts/unseen-backlog.py mark-seen <item_id>
```

### stats

Show aggregated counts by priority, category, and source.

```bash
python ${MY_REPOS}/_project/scripts/unseen-backlog.py stats
```

### digest-summary

Analyze a daily digest file and produce structured JSON of all pulse entries classified by priority and actionability.

```bash
python ${MY_REPOS}/_project/scripts/unseen-backlog.py digest-summary \
  ${MY_REPOS}/_project/daily-digest/2026-06-04.md
```

**Returns:** JSON with shape:
```json
{
  "sections": 37,
  "items": [
    {
      "header": "[05:35 EST] Forge Pulse",
      "priority": "critical",
      "category": "project",
      "type": "important",
      "summary": "First 150 characters of...",
      "full_body": "Complete raw pulse body..."
    }
  ]
}
```

**Usage notes:**
- `summary` is auto-truncated to ~150 characters — use this for lightweight categorization
- `full_body` is the COMPLETE raw pulse text (can be 500+ chars per item, especially for multi-line pulses)
- For analysis scripts, prefer `summary` unless you need the full detail
- Pipe into `python -c "import sys,json; d=json.load(sys.stdin); ..."` for programmatic grouping

## Pipeline: End-to-End Workflow

```python
# 1. Analyze the digest
import subprocess, json
result = subprocess.run([
    "python",
    "${MY_REPOS}/_project/scripts/unseen-backlog.py",
    "digest-summary",
    "${MY_REPOS}/_project/daily-digest/2026-06-05.md"
], capture_output=True, text=True, timeout=10)
data = json.loads(result.stdout)

# 2. Group by priority
from collections import Counter
by_p = Counter(i['priority'] for i in data['items'])

# 3. Add critical/high items to backlog
for item in [i for i in data['items'] if i['priority'] in ('critical','high')]:
    subprocess.run([
        "python",
        "${MY_REPOS}/_project/scripts/unseen-backlog.py",
        "add",
        "Daily Pulsar",
        item['priority'],
        item['category'],
        item['summary'][:120],
        f"daily-digest/2026-06-05.md"
    ], timeout=10)

# 4. Count unseen backlog items (list is text — use grep-style parsing)
result = subprocess.run([
    "python",
    "${MY_REPOS}/_project/scripts/unseen-backlog.py",
    "list", "--unseen-only", "--priority=critical"
], capture_output=True, text=True, timeout=10)
critical_count = result.stdout.count("[CRITICAL]")
```

## Priority Classification Rules

Priority is auto-detected by regex patterns:
- **critical** (`🔴`): `CRITICAL`, `BLOCKED`, `FAILED`, `DOWN`, `stale.*\d+ days`, `cold.*\d+ days`, `divergence`, `0 outreach`, `0 won`
- **high** (`🟡`): `WARNING`, `stalled`, `needs.*attention`, `should`, `need to`, `must`, `recommend`, `opportunity`
- **fyi**: Everything else

## Category Classification Rules

- `bizdev`: matches `business`, `bizdev`, `contract`, `outreach`, `pipeline`, `target`
- `infra`: matches `infra`, `docker`, `gpu`, `server`, `container`, `health`
- `intel`: matches `intel`, `intelligence`, `pim`, `bookmark`, `star`, `youtube`, `blogwatcher`
- `project`: matches `project`, `repo`, `commit`, `code`, `feature`, `pr`
- `improvement`: matches `action`, `improve`, `optimize`, `could`, `better`, `upgrade`
