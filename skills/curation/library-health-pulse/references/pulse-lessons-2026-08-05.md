# Pulse Lessons — 2026-08-05 (dream-cycle skill count)

## Depth-capped scans undercount: a second failure class alongside `find` silent-skip

The Hermes dream-cycle inventory script counted skills with a 2-level scan
(`for cat in skills/*: for skill in cat/*: check SKILL.md`) and reported **323**.
Fully recursive `pathlib.rglob("SKILL.md")` (excluding `.archive`) found **460** —
a 137-skill undercount. Same conversation: shell `find . -name SKILL.md -not -path
'*/.archive/*'` reported 429 while Python rglob found 460 (consistent with the
Aug-3 431-vs-462 incident already documented in SKILL.md).

Two DISTINCT undercount causes on this host:
1. `find` on MSYS silently skips some directories (no error).
2. Depth-capped scans miss nested-category skills that sit 3+ levels deep:
   - `mlops/evaluation/weights-and-biases/SKILL.md`
   - `gstack/browse/SKILL.md`, `gstack/qa/SKILL.md`, `gstack/review/SKILL.md`

## Nested skills are legitimately separate — dedup by parent dir, not category

`gstack/` has its own SKILL.md AND sub-directory skills (`gstack/browse`, etc.).
A category dir with its own SKILL.md plus sub-skill dirs yields multiple skills;
deduping by category would drop the sub-skills. Correct dedup: skip a SKILL.md
only if its parent dir already yielded one (first-encounter per parent wins),
i.e. `seen_dirs.add(skill_md.parent)`.

## Verified recursive count recipe

```python
from pathlib import Path
root = Path.home() / "AppData/Local/hermes/skills"
seen = set()
count = 0
for md in sorted(root.rglob("SKILL.md")):
    if ".archive" in md.parts or md.parent in seen:
        continue
    seen.add(md.parent)
    count += 1
print("active skills:", count)   # 460 on 2026-08-05 (64 archived)
```

Use this for any count that drives a decision (Sweep K census, Sweep L diffs,
trend numbers) — never a depth-capped loop, and cross-check `find`-based counts
against it.
