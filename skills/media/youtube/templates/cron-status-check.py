#!/usr/bin/env python3
"""
Cron Job Status Check — Quick health read for any cron job that writes a status JSON.
Usage: python cron_status_check.py
Reads: ../cron_last_status.json (or first arg)
"""
import json, sys
from pathlib import Path

status_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / ".." / "cron_last_status.json"
log_file = status_file.with_name(status_file.stem.replace("_last_status", "")).with_suffix(".log")
if not log_file.exists():
    log_file = status_file.parent / status_file.name.replace("_last_status", "").replace(".json", ".log")

print("=" * 55)
print("  Cron Job — Status Check")
print("=" * 55)

if not status_file.exists():
    print(f"  STATUS: ⚫ Never run")
    print(f"  Expected: {status_file}")
    sys.exit(0)

with open(str(status_file)) as f:
    status = json.load(f)

last_run = status.get("last_run_iso", "unknown")
errors = status.get("errors", [])
total = status.get("total_videos_found") or status.get("total_items", 0)
new = status.get("new_items_inserted", 0)

print(f"  Last run: {last_run}")
print(f"  Items found: {total}")
print(f"  New items: {new}")
print(f"  Errors: {len(errors)}")

if errors:
    print("\n  ❌ ISSUES:")
    for e in errors:
        print(f"     • {e}")

# Last 5 log lines
if log_file.exists():
    with open(str(log_file)) as f:
        lines = f.readlines()
    if lines:
        print("\n  Last log entries:")
        for line in lines[-5:]:
            print(f"    {line.strip()}")
