#!/usr/bin/env python3
"""One-shot consolidated pulse audit (pathlib ground truth).

Runs the full frontmatter regression battery + collision + size watch in a
single pass — the default audit for a pulse cycle:
  - active SKILL.md count (pathlib rglob; MSYS `find` silently skips dirs)
  - YAML parse errors, missing version, missing triggers
  - root-level keys (tags/triggers/related_skills outside metadata.hermes)
  - duplicate frontmatter keys
  - within-tree name collisions grouped by frontmatter `name:` (dir name !=
    frontmatter name in import families, e.g. dir lm-evaluation-harness ->
    name evaluating-llms-harness)
  - size watch (>88KB, non-archived)
  - _drafts stub count

Usage: python pulse-audit.py [root]   (default: ~/AppData/Local/hermes/skills)
Exit 0 always; inspect output. Verified Aug 8 2026: 465 skills scanned, caught
the market-signal-scanner bare-frontmatter regression (no version, no
triggers), confirmed only the exempt gstack trio collisions.
"""
import pathlib, sys
import yaml

ROOT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else (
    pathlib.Path.home() / "AppData/Local/hermes/skills")
ARCHIVE_MARKERS = (".archive", ".hub")

skills = [p for p in ROOT.rglob("SKILL.md")
          if not any(m in p.parts for m in ARCHIVE_MARKERS)]
print(f"TOTAL SKILL.md (pathlib, excl .archive): {len(skills)}")

parse_errs, no_version, no_triggers, root_keys, dup_keys = [], [], [], [], []
by_name = {}
sizes = []

for p in skills:
    raw = p.read_bytes()
    sizes.append((len(raw), p))
    c = raw.decode("utf-8", errors="replace")
    if not c.startswith("---"):
        parse_errs.append((str(p), "no leading ---")); continue
    rest = c[3:]
    close = rest.find("\n---")
    if close < 0:
        parse_errs.append((str(p), "no closing ---")); continue
    fm_text = rest[:close]
    try:
        fm = yaml.safe_load(fm_text)
    except Exception as e:
        parse_errs.append((str(p), f"yaml: {e}")); continue
    if not isinstance(fm, dict):
        parse_errs.append((str(p), "fm not dict")); continue
    name = fm.get("name")
    if name:
        by_name.setdefault(name, []).append(str(p))
    if "version" not in fm:
        no_version.append(str(p))
    hermes = (fm.get("metadata") or {}).get("hermes") or {}
    if not isinstance(hermes, dict) or "triggers" not in hermes:
        no_triggers.append(str(p))
    for k in ("tags", "triggers", "related_skills"):
        if k in fm:
            root_keys.append((str(p), k))
    seen = set()
    for line in fm_text.splitlines():
        s = line.strip()
        if s.endswith(":") and not s.startswith("-") and not s.startswith("#"):
            key = s[:-1].strip()
            if key in seen:
                dup_keys.append((str(p), key))
            seen.add(key)


def show(label, items, limit=10):
    print(f"{label}: {len(items)}")
    for it in items[:limit]:
        print("  ", it)


show("YAML parse errors", parse_errs)
show("Missing version", no_version)
show("Missing triggers (metadata.hermes)", no_triggers)
show("Root-level keys", root_keys)
show("Duplicate keys", dup_keys)

print("=== WITHIN-TREE NAME COLLISIONS (frontmatter name grouped) ===")
collisions = {n: ps for n, ps in by_name.items() if len(ps) > 1}
print(f"Collision names: {len(collisions)}")
for n, ps in sorted(collisions.items()):
    print(f"  {n}:")
    for path in ps:
        print(f"    - {path}")

print("=== SIZE WATCH (>88KB) ===")
big = sorted((s for s in sizes if s[0] > 88000), reverse=True)
print(f"Skills >88KB: {len(big)}")
for size, p in big:
    print(f"  {size:>8,}B  {p}")

drafts = ROOT / "_drafts"
if drafts.exists():
    files = sorted(drafts.rglob("*.md"))
    print(f"Draft stubs (incl README): {len(files)}")
else:
    print("No _drafts dir")
