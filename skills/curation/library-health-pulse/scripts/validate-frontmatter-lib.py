#!/usr/bin/env python3
"""Full-library frontmatter validation for Hermes skill trees.

Definitive replacement for grep/head-based scans, which have line-truncation
blind spots (triggers can legitimately sit past line 25 in verbose
frontmatter) and miss YAML parse errors entirely. Run against any skills root:

    python validate-frontmatter-lib.py [SKILLS_ROOT]   # default: .

Reports per-file defects and exits 1 if any live skill is defective.
Live = any SKILL.md not under a .archive/ path.

Checks (all at once, one yaml.safe_load per file):
  - missing leading/closing --- fence
  - YAML parse errors (silently-skips-skill class)
  - duplicate root-level YAML keys (last-one-wins data loss)
  - root-level tags/triggers/related_skills (ignored by inference engine)
  - missing metadata.hermes.triggers (NO_TRIGGERS class)
  - missing root name/description (metadata-only frontmatter class — all fields
    nested under metadata.hermes, loader falls back to dir-name description)
  - size over 95KB (MAX_SKILL_CONTENT_CHARS watch threshold)
"""
import pathlib
import sys

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

WATCH_KB = 95000


def check_file(p: pathlib.Path):
    """Return list of (KIND, detail) defect tuples for one SKILL.md."""
    problems = []
    c = p.read_text(encoding="utf-8", errors="replace")
    if not c.startswith("---"):
        return [("NO_OPEN_FENCE", "missing leading ---")]
    rest = c[3:]
    close = rest.find("\n---")
    if close < 0:
        return [("NO_CLOSE_FENCE", "missing closing ---")]
    fm_block = rest[:close]
    try:
        fm = yaml.safe_load(fm_block)
    except Exception as e:
        return [("YAML_PARSE", str(e)[:80])]
    if not isinstance(fm, dict):
        return [("FM_NOT_DICT", type(fm).__name__)]

    # duplicate root-level keys (naive line scan — YAML last-one-wins)
    seen = {}
    for line in fm_block.splitlines():
        if line and not line[0].isspace() and ":" in line:
            key = line.split(":", 1)[0].strip()
            seen[key] = seen.get(key, 0) + 1
    for k, n in seen.items():
        if n > 1:
            problems.append(("DUP_KEY", f"{k} x{n}"))

    # root-level tags/triggers/related_skills
    for k in ("tags", "triggers", "related_skills"):
        if k in fm:
            problems.append(("ROOT_LEVEL", k))

    # missing triggers under metadata.hermes
    h = fm.get("metadata", {}).get("hermes", {}) if isinstance(fm.get("metadata"), dict) else {}
    if not h.get("triggers"):
        problems.append(("NO_TRIGGERS", ""))

    # missing root name/description — metadata-only frontmatter class (Aug 2 2026:
    # 4 skills had ALL fields nested under metadata.hermes, zero root keys; loader
    # silently fell back to dir-name descriptions, breaking discoverability)
    if not fm.get("name"):
        problems.append(("NO_NAME", "missing root name"))
    if not fm.get("description"):
        problems.append(("NO_DESCRIPTION", "missing root description"))

    if len(c) > WATCH_KB:
        problems.append(("OVER_95KB", f"{len(c)} bytes"))

    return problems


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    live = [p for p in root.rglob("SKILL.md") if ".archive" not in p.parts]
    bad = 0
    for p in sorted(live):
        for kind, detail in check_file(p):
            bad += 1
            print(f"{kind}: {p} {detail}".rstrip())
    total = len(live)
    print(f"\nScanned {total} live SKILL.md files: {total - bad} clean, {bad} with defects")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
