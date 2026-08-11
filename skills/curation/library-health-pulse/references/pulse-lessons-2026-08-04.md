# Pulse Lessons — 2026-08-04/05 (Skillmate cycle)

Three lessons from the Aug 4 2026 pulse that future cycles should carry. The first two are
candidates to fold into Sweep I / Sweep E / Pitfalls text the next time `library-health-pulse`
SKILL.md is edited by a session whose loader isn't dedup-caching it.

## 1. Size watch must prioritize LOCAL (non-bundled) skills — and scan with pathlib

The Sweep I watch had tracked only gstack (bundled, unmodifiable) for multiple cycles. Result:
two **local-tree** skills crossed 90KB unnoticed:

- `market-lead/land-wholesaling` — 91.6KB
- `productivity/intelligence-pulse` — 91.4KB

Both are trimmable (extract market-priority tables / deal-log detail into `references/`). gstack
growth is only worth an upstream note; local crossers are the actionable ones. When the 95KB+
list is all bundled, look at the 86-95KB zone for local skills.

Also: the size scan must use Python `pathlib.rglob` — shell `find` on MSYS silently skips some
directories (same failure class as the Aug-3 431-vs-462 count undercount). A watch that uses
`find` can miss the exact crossers it exists to catch.

Reference one-liner:

```python
import os
from pathlib import Path
root = Path.home() / "AppData/Local/hermes/skills"
for s in sorted(root.rglob("SKILL.md")):
    if ".archive" in s.parts: continue
    sz = s.stat().st_size
    if sz > 86000:
        print(f"{sz:>8,}  {s.parent.parent.name}/{s.parent.name}")
```

## 2. append-digest.py's quiet-hours echo is NOT a delivery instruction

The daily-digest script prints its own gate notice:

```
[Digest] Quiet hours (00:00-06:59 EST) — saved to digest only.
[SILENT]
```

On Aug 4 2026 the job's own TZ check (`TZ='EST5EDT,M3.2.0/2,M11.1.0/2' date +%H` → 22:14 ET,
deliver hour) disagreed with the script's echo. The script's clock basis can differ from the
job's TZ instruction — the echo is informational about the *digest*, not a directive about the
*report*. Rules:

- Delivery decision follows the job's TZ check only. A `[SILENT]` printed by the digest script
  must NOT suppress the report when the job TZ says it's a report hour.
- Confirm the append actually landed: look for `[Digest] Appended to ...` in the script output.
  "Quiet hours" echo plus a successful `Appended to` line means the finding WAS saved — deliver
  the normal report.
- The `python /e/...` MSYS-path failure is a separate gotcha (native python needs `E:/...`),
  already documented in the skill's Pitfalls — but it also silently prevents the digest append,
  so check for `[Digest] Appended` as the success signal, not the exit code alone.

## 3. Gap-check before promoting a draft: grep the overlapping skill

`create-market-lead-wholesaling-skill-wit` (Real Estate Tier 1) sat next to the existing
`market-lead/land-wholesaling` for 5 days, looking redundant on its face. The promote-vs-
redundant decision was settled by grepping the existing skill for the draft's core concepts:

```bash
grep -io "max allowable offer\|MAO\|ARV\|after repair value\|offer calculat\|comps" \
  market-lead/land-wholesaling/SKILL.md | sort | uniq -c
```

Result: `land-wholesaling` had 9×"comps", 1×"ARV", zero MAO/offer-calc math — it covers vacant
land (Find Builder → Buy Box → Find Lot → Assign) with no house-level offer math. The draft was
a genuine gap, not a duplicate → promoted as `market-lead/house-wholesaling` v1.0.0 (9.8KB,
17 triggers, cross-refs land-wholesaling/county-property-database/public-property-records/
buy-box-match-engine).

Generalize: before authoring any draft whose domain overlaps an existing skill, quantify the
overlap. Near-zero grep hits on the draft's defining terms = genuine gap (promote). Dense
coverage = mark REDUNDANT/absorbed instead (saves a full authoring pass). This converts the
promote-vs-redundant call from a guess into a decision.
