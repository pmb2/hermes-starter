#!/usr/bin/env python3
"""
version-field-audit.py — Scan and optionally fix missing `version:` fields
in Hermes skill frontmatter.

Usage:
    python scripts/version-field-audit.py              # scan only
    python scripts/version-field-audit.py --fix         # scan + patch missing to 1.0.0
    python scripts/version-field-audit.py --fix --dry-run  # show what would change
    python scripts/version-field-audit.py --path ~/AppData/Local/hermes/skills

Prints a summary:
    Scanned: 321 | Missing version: 12 (3.7%) | Fixed: 12
"""

import argparse
import os
import re
import sys
from pathlib import Path


def get_skills_dir() -> Path:
    """Resolve the skills directory."""
    candidates = [
        Path.home() / "AppData/Local/hermes/skills",
        Path.home() / ".hermes/skills",
        Path.home() / ".local/share/hermes/skills",
    ]
    for p in candidates:
        if p.is_dir():
            return p
    # Fallback: relative to this script's location
    script_dir = Path(__file__).resolve().parent.parent
    if (script_dir / "SKILL.md").exists():
        return script_dir.parent
    sys.exit("ERROR: Cannot find skills directory. Pass --path explicitly.")


def find_active_skills(base: Path) -> list[Path]:
    """Return paths to every SKILL.md not under .archive or .curator_backups."""
    results = []
    for root, dirs, files in os.walk(str(base)):
        # Prune excluded dirs
        rel = os.path.relpath(root, str(base))
        parts = rel.replace("\\", "/").split("/")
        if any(p in (".archive", ".curator_backups", "_drafts", ".hub", ".git") for p in parts):
            continue
        if "SKILL.md" in files:
            results.append(Path(root) / "SKILL.md")
    return results


def version_line(skill_path: Path) -> str | None:
    """Return the raw version: line (including leading spaces) or None."""
    with open(skill_path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    # Extract YAML frontmatter (between --- markers)
    m = re.match(r"^---\s*\n(.*?\n)---", text, re.DOTALL)
    if not m:
        return None
    fm = m.group(1)
    for line in fm.splitlines():
        if re.match(r"^version\s*:", line):
            return line
    return None


def patch_version(skill_path: Path, value: str = "1.0.0", dry_run: bool = False) -> bool:
    """Insert a version line into the YAML frontmatter after the name line."""
    with open(skill_path, encoding="utf-8") as f:
        text = f.read()

    m = re.match(r"^(---\s*\n)(.*?\n)(---)", text, re.DOTALL)
    if not m:
        return False  # malformed frontmatter

    header, fm, footer = m.group(1), m.group(2), m.group(3)

    # Find insertion point: right after `name:` line
    lines = fm.splitlines()
    insert_idx = None
    for i, line in enumerate(lines):
        if re.match(r"^name\s*:", line):
            insert_idx = i + 1
            break
    if insert_idx is None:
        return False  # no name: field to anchor on

    indent = " " * (len(lines[insert_idx - 1]) - len(lines[insert_idx - 1].lstrip()))
    new_line = f"{indent}version: {value}\r\n" if text.find("\r\n") >= 0 else f"{indent}version: {value}\n"
    lines.insert(insert_idx, new_line)
    new_fm = "\n".join(lines)
    # Restore trailing newline if present
    if fm.endswith("\n"):
        new_fm += "\n"

    new_text = header + new_fm + footer

    if dry_run:
        print(f"  WOULD FIX: {skill_path.name}")
        return True

    with open(skill_path, "w", encoding="utf-8") as f:
        f.write(new_text)
    return True


def main():
    parser = argparse.ArgumentParser(description="Audit and fix missing version fields in skill frontmatter")
    parser.add_argument("--path", type=str, default=None, help="Path to skills directory")
    parser.add_argument("--fix", action="store_true", help="Patch missing version fields to 1.0.0")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be fixed without modifying")
    args = parser.parse_args()

    base = Path(args.path).expanduser().resolve() if args.path else get_skills_dir()
    if not base.is_dir():
        sys.exit(f"ERROR: {base} is not a directory.")

    skills = find_active_skills(base)
    missing = []

    for sp in skills:
        vl = version_line(sp)
        if vl is None:
            missing.append(sp)

    # Report
    total = len(skills)
    count = len(missing)
    pct = count * 100 / total if total else 0

    print(f"Skills directory: {base}")
    print(f"Scanned: {total} | Missing version: {count} ({pct:.1f}%)")

    if not missing:
        print("✅ All skills have version fields.")
        return

    print()
    for sp in sorted(missing, key=lambda p: p.parent.name):
        print(f"  MISSING: {sp.parent.name:45s} ({sp})")

    if args.fix or args.dry_run:
        fixed = 0
        for sp in sorted(missing, key=lambda p: p.parent.name):
            if patch_version(sp, dry_run=args.dry_run):
                fixed += 1
        mode = "WOULD FIX" if args.dry_run else "FIXED"
        print(f"\n{mode}: {fixed}/{count}")


if __name__ == "__main__":
    main()
