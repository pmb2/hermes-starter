# Usage Registry Ghost Cleanup

## Detection

Cross-reference `.usage.json` entries against on-disk directories:

```python
import json, os

with open('.usage.json') as f:
    d = json.load(f)

ghosts = [name for name, meta in d.items()
          if meta.get('state') == 'active' and not os.path.isdir(name)]
```

Key signals: `state == 'active'`, `use_count == 0`, `patch_count == 0`, `archived_at is None`.

## Cross-Reference Safety Check

Before marking stale, verify no active skill's `related_skills` references a ghost:

```python
for root, dirs, files in os.walk('.'):
    if '.archive' in root or '.curator_backups' in root: continue
    if 'SKILL.md' in files:
        with open(os.path.join(root, 'SKILL.md')) as f:
            content = f.read()
        if content.startswith('---'):
            fm_end = content.index('---', 3)
            fm = content[3:fm_end]
            if 'related_skills' in fm:
                for g in ghosts:
                    if g in fm: print(f"REFERENCED: {root} -> {g}")
```

## Remediation

Mark ghosts as `state: stale` (preserves audit trail):

```python
import json
from datetime import datetime, timezone
now = datetime.now(timezone.utc).isoformat()
for name in ghosts:
    d[name]['state'] = 'stale'
    d[name]['archived_at'] = now
with open('.usage.json', 'w') as f:
    json.dump(d, f, indent=2)
```

## Verification

```python
active = sum(1 for v in d.values() if v.get('state') == 'active')
stale = sum(1 for v in d.values() if v.get('state') == 'stale')
print(f"Active: {active} | Stale: {stale} | Total: {len(d)}")
```

See also `scripts/ghost-detect.py` — standalone, re-runnable script with `--fix` and `--dry-run` flags.
