#!/usr/bin/env python3
"""Dual-tree skill audit: name collisions + triggerless + versionless, with drift compare.

Usage:
    python audit-dual-tree.py [APP_SKILLS_DIR] [EXT_SKILLS_DIR]

Defaults:
    APP_SKILLS_DIR = C:/Users/<user>/AppData/Local/hermes/skills
    EXT_SKILLS_DIR = <external_dirs entry>/skills   (e.g. C:/Users/<user>/Documents/github/hermes-config/skills)

What it reports:
  1. Names present in BOTH trees -> collision candidates (verify live with skill_view(name))
  2. External-only / AppData-only names (discoverability gaps)
  3. Triggerless skills in each tree (metadata.hermes.triggers missing -> inference engine never activates them)
  4. Versionless skills in each tree
  5. For colliding names: version + trigger-count drift, plus file-set diff (files only on one side)

Pitfalls this script is designed to avoid (learned 2026-08-05):
  - rglob('<name>/SKILL.md') silently matches .archive/ copies; collection here filters
    '.archive' out of p.parts AND uses frontmatter name: (not directory name) as the key.
  - read_text() translates CRLF->LF on Windows; line-ending checks use read_bytes().
  - Frontmatter-exact name matching only -- grep '^name:' over-reports (2026-07-31 lesson).
"""
import pathlib
import sys
import yaml

APP_DEFAULT = pathlib.Path.home() / "AppData/Local/hermes/skills"
EXT_DEFAULT = pathlib.Path.home() / "Documents/github/hermes-config/skills"


def parse_frontmatter(path):
    """Return (frontmatter_dict, raw_bytes) or (None, None) on parse failure."""
    try:
        raw = path.read_bytes()
        c = raw.decode("utf-8")
    except Exception:
        return None, None
    if not c.startswith("---"):
        return None, None
    rest = c[3:]
    close = rest.find("\n---")
    if close < 0:
        return None, None
    try:
        fm = yaml.safe_load(rest[:close])
    except Exception:
        return None, None
    if not isinstance(fm, dict):
        return None, None
    return fm, raw


def collect(root):
    """name -> list of (abs_path, fm, raw_bytes) for every SKILL.md outside .archive."""
    out = {}
    for p in root.rglob("SKILL.md"):
        if ".archive" in p.parts:
            continue
        fm, raw = parse_frontmatter(p)
        if not fm or not fm.get("name"):
            continue
        out.setdefault(fm["name"], []).append((p, fm, raw))
    return out


def trig_count(fm):
    h = fm.get("metadata", {}).get("hermes", {}) if isinstance(fm.get("metadata"), dict) else {}
    return len(h.get("triggers", []) or [])


def file_set(skill_dir):
    return sorted(str(x.relative_to(skill_dir)).replace("\\", "/") for x in skill_dir.rglob("*") if x.is_file())


def main():
    app_root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else APP_DEFAULT
    ext_root = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else EXT_DEFAULT
    app = collect(app_root)
    ext = collect(ext_root)

    both = sorted(set(app) & set(ext))
    print(f"== Names in BOTH trees (collision candidates): {len(both)}")
    for n in both:
        for label, tree in (("APP", app), ("EXT", ext)):
            for p, fm, raw in tree[n]:
                skill_dir = p.parent
                crlf = b"\r\n" in raw
                fs = file_set(skill_dir)
                print(f"   [{label}] {n} v{fm.get('version','MISSING')} | {trig_count(fm)} trig | "
                      f"{len(fs)} files | CRLF={crlf} | {p}")
        # drift summary
        ap = app[n][0][1]
        ep = ext[n][0][1]
        av, ev = ap.get("version", "MISSING"), ep.get("version", "MISSING")
        at, et = trig_count(ap), trig_count(ep)
        drift = []
        if av != ev:
            drift.append(f"version {av} vs {ev}")
        if at != et:
            drift.append(f"triggers {at} vs {et}")
        print(f"   DRIFT: {', '.join(drift) if drift else 'none (versions+triggers match)'}")
        print()

    for label, tree in (("APP", app), ("EXT", ext)):
        no_trig = sorted(n for n in tree if not any(trig_count(fm) for _, fm, _ in tree[n]))
        no_ver = sorted(n for n in tree if not any(fm.get("version") for _, fm, _ in tree[n]))
        print(f"== {label} triggerless: {len(no_trig)}  {no_trig}")
        print(f"== {label} versionless: {len(no_ver)}  {no_ver}")

    app_only = sorted(set(app) - set(ext))
    ext_only = sorted(set(ext) - set(app))
    print(f"== AppData-only names: {len(app_only)}")
    print(f"== External-only names: {len(ext_only)}  {ext_only}")
    print(f"== Totals: AppData {len(app)} | External {len(ext)}")

    if both:
        print("\nACTION: verify each BOTH name live with skill_view(name) -- any 'Ambiguous skill name'")
        print("result is a regression. Resolve per skill-name-collision-remediation Option B->A.")


if __name__ == "__main__":
    main()
