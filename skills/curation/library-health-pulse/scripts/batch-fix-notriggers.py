#!/usr/bin/env python
"""Batch-fix NO_TRIGGERS skills: add a full metadata.hermes block.

CRLF-safe (handles \r\n, \r\r\n doubled-CRLF, and LF). Per the skill-authoring
Pitfall #7 family, skill_manage(action='patch') and the standalone patch()
tool silently fail or misbehave on CRLF files, so batch frontmatter fixes
must go through byte-level Python like this.

VERIFIED Aug 2026 — 10/10 skills fixed in one pass (emilkowalski-* family
x8 + impeccable + taste-skill), YAML validated after, zero regressions.

USAGE:
1. Find the regressions (usually an ENTIRE hub-imported family arrives
   bare-frontmatter at once — e.g. the apple/ family on Jul 29, the
   emilkowalski-* family on Aug 2):
     find <HERMES_HOME>/skills/ -name SKILL.md -not -path '*/.archive/*' \
       -exec sh -c 'grep -q "triggers:" "$1" || echo "$1"' _ {} \;
2. For each flagged file, read its frontmatter `name:` field. CRITICAL:
   the directory name and the YAML name often DIFFER for imported families
   (dir `taste-skill` -> name `design-taste-frontend`; dir
   `emilkowalski-motion` -> name `improve-animations`). The FIXES dict keys
   by DIRECTORY name; the frontmatter `name:` stays as-is.
3. Fill FIXES with {tags, triggers (4-5 phrases), related (peer names)}.
   Verify each related_skills target actually exists in a tree first —
   a dead related_skills ref is a worse defect than missing triggers.
4. Run:  python batch-fix-notriggers.py
5. Verify:
     find ... -exec sh -c 'grep -q "triggers:" "$1" || echo "$1"' _ {} \; | wc -l   # -> 0
     python -c "import yaml,pathlib; print(yaml.safe_load(pathlib.Path('<fixed file>').read_text().split('---',2)[1]))"
"""
import pathlib

SKILLS_ROOT = pathlib.Path(r"${USER_HOME}/AppData/Local/hermes/skills")

# directory-name -> metadata to inject. Edit per batch. Example shape:
# FIXES = {
#     "emilkowalski-motion": {
#         "tags": ["animation", "motion", "audit"],
#         "triggers": ["improve animations", "audit motion", "animation roadmap"],
#         "related": ["find-animation-opportunities", "review-animations"],
#     },
# }
FIXES = {}

DEFAULT_VERSION = "1.0.0"
DEFAULT_AUTHOR = "Hermes Agent"
DEFAULT_LICENSE = "MIT"


def insert_metadata(path: pathlib.Path, cfg: dict) -> bool:
    data = path.read_bytes()
    has_crlf = b"\r\n" in data
    doubled = b"\r\r\n" in data
    if doubled:
        text = data.decode("utf-8").replace("\r\r\n", "\n")
    elif has_crlf:
        text = data.decode("utf-8").replace("\r\n", "\n")
    else:
        text = data.decode("utf-8")

    # Insert before the closing --- of the frontmatter (first close after open)
    close_idx = text.find("\n---", 3)
    if close_idx == -1:
        print(f"SKIP (no frontmatter close): {path.name}")
        return False

    block = (
        f"\nversion: {DEFAULT_VERSION}\n"
        f"author: {DEFAULT_AUTHOR}\n"
        f"license: {DEFAULT_LICENSE}\n"
        "metadata:\n"
        "  hermes:\n"
        f"    tags: [{', '.join(cfg['tags'])}]\n"
        f"    triggers: [{', '.join(cfg['triggers'])}]\n"
        f"    related_skills: [{', '.join(cfg['related'])}]\n"
    )
    new_text = text[:close_idx] + block + text[close_idx:]

    if doubled:
        out = new_text.replace("\n", "\r\r\n")
    elif has_crlf:
        out = new_text.replace("\n", "\r\n")
    else:
        out = new_text
    path.write_bytes(out.encode("utf-8"))
    return True


def main() -> None:
    if not FIXES:
        print("FIXES dict is empty — populate it first (see docstring).")
        return
    fixed = 0
    for folder, cfg in FIXES.items():
        p = SKILLS_ROOT / folder / "SKILL.md"
        if not p.exists():
            print(f"MISSING: {folder}")
            continue
        if insert_metadata(p, cfg):
            fixed += 1
            print(f"FIXED: {folder}")
    print(f"\nTotal fixed: {fixed}/{len(FIXES)}")


if __name__ == "__main__":
    main()
