#!/usr/bin/env python3
"""Scan a Hermes skill library for duplicate `name:` frontmatter values.

Frontmatter-exact: reads only the YAML head of each SKILL.md, so `name:`
lines in body text, examples, and code blocks do NOT produce false positives
(a naive `grep -rh '^name:' | sort | uniq -d` does — it flagged 22 "duplicates"
in the 2026-07-31 audit when the true count was 5).

Usage:
    python scan-name-collisions.py [skills_root]

Default root: ~/AppData/Local/hermes/skills (or %LOCALAPPDATA%/hermes/skills).
Skips: .archive, _drafts, .hub, .curator_backups.
Exit code 1 if any duplicates found, 0 otherwise.

After finding collisions, classify before remediating:
  - Near-identical byte sizes (<=2KB diff)  -> redundant duplicate; keep the
    larger/newer copy, delete the other.
  - Large size divergence                   -> different content sharing a name;
    rename one side or merge, never blind-delete.
"""
import collections
import os
import re
import sys

SKIP_DIRS = {".archive", "_drafts", ".hub", ".curator_backups"}


def main() -> int:
    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        root = os.path.expandvars(r"%LOCALAPPDATA%\hermes\skills")
        if not os.path.isdir(root):
            root = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes", "skills")

    name_map = collections.defaultdict(list)
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.lower() != "skill.md":
                continue
            total += 1
            p = os.path.join(dirpath, fn)
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    head = f.read(2000)  # frontmatter head only
            except OSError:
                continue
            m = re.search(r'^name:\s*["\']?([^"\'\n]+)', head, re.M)
            if m:
                name_map[m.group(1).strip()].append(os.path.relpath(p, root).replace("\\", "/"))

    print(f"total SKILL.md scanned: {total}")
    dups = {k: v for k, v in name_map.items() if len(v) > 1}
    print(f"duplicate names: {len(dups)}")
    for name, paths in sorted(dups.items()):
        print(f"\n== {name} ({len(paths)}x) ==")
        for rel in paths:
            print("  " + rel)
            full = os.path.join(root, rel.replace("/", os.sep))
            try:
                print(f"    {os.path.getsize(full)} bytes")
            except OSError:
                pass
    return 1 if dups else 0


if __name__ == "__main__":
    sys.exit(main())
