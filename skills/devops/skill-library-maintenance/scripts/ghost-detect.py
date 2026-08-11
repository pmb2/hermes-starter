#!/usr/bin/env python3
"""
ghost-detect.py — Detect ghost entries in .usage.json

Ghost entries are skills tracked as `state: active` in .usage.json
whose on-disk directories have been removed. Cross-reference checks
ensure no active skill points to a ghost via related_skills.

Usage:
    cd ~/AppData/Local/hermes/skills
    python scripts/ghost-detect.py [--fix] [--dry-run]

Options:
    --fix       Mark ghosts as stale in .usage.json
    --dry-run   Show what would be done without writing
"""
import json
import os
import sys

SKILLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USAGE_JSON = os.path.join(SKILLS_DIR, '.usage.json')


def main():
    dry_run = '--dry-run' in sys.argv
    do_fix = '--fix' in sys.argv

    with open(USAGE_JSON) as f:
        registry = json.load(f)

    # Detect ghosts
    ghosts = []
    for name, meta in registry.items():
        if meta.get('state') == 'active':
            skill_dir = os.path.join(SKILLS_DIR, name)
            if not os.path.isdir(skill_dir):
                ghosts.append(name)

    if not ghosts:
        print("No ghost entries found. Registry is clean.")
        return

    print(f"Ghost entries: {len(ghosts)}")
    for g in ghosts:
        meta = registry[g]
        print(f"  {g} | created {meta.get('created_at','?')[:10]} | "
              f"{meta.get('use_count',0)} uses, {meta.get('patch_count',0)} patches")

    # Cross-reference check
    print("\nCross-referencing against active skill related_skills...")
    refs = []
    for root, dirs, files in os.walk(SKILLS_DIR):
        if '.archive' in root or '.curator_backups' in root:
            continue
        if 'SKILL.md' in files:
            path = os.path.join(root, 'SKILL.md')
            with open(path) as f:
                content = f.read()
            if content.startswith('---'):
                fm_end = content.index('---', 3)
                fm = content[3:fm_end]
                if 'related_skills' in fm:
                    for g in ghosts:
                        if g in fm:
                            refs.append((os.path.relpath(root, SKILLS_DIR), g))

    if refs:
        print(f"WARNING: {len(refs)} active skills reference ghost entries:")
        for skill, ghost in refs:
            print(f"  {skill} -> {ghost}")
        print("Fix consumer related_skills before marking ghosts stale.")
        if not do_fix:
            print("Run with --fix to force remediation anyway.")
            return
    else:
        print("No active skill references any ghost entry. Safe to remediate.")

    if not do_fix or dry_run:
        print(f"\n{'[DRY RUN] Would mark' if dry_run else 'Run with --fix to mark'} "
              f"{len(ghosts)} entries as stale.")
        return

    # Remediate
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    updated = 0
    for name in ghosts:
        if name in registry:
            registry[name]['state'] = 'stale'
            registry[name]['archived_at'] = now
            updated += 1

    with open(USAGE_JSON, 'w') as f:
        json.dump(registry, f, indent=2)

    print(f"Marked {updated} ghost entries as stale in {USAGE_JSON}")

    # Final health
    active = sum(1 for v in registry.values() if v.get('state') == 'active')
    stale = sum(1 for v in registry.values() if v.get('state') == 'stale')
    print(f"Active: {active} | Stale: {stale} | Total: {len(registry)}")


if __name__ == '__main__':
    main()
