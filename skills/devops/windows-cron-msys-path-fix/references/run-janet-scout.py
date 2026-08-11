#!/usr/bin/env python3
"""Run admin portfolio scout from the insider-trading project.

This wrapper handles the relative-import issue that prevents
insider-trading's scripts/run_scout.py from running as a standalone
script. It adds the project to sys.path, chdirs to project root,
then imports and calls the project's own functions directly.

Deployment location: ~/.hermes/scripts/run-admin-scout.py
Cron job: hermes cron create "0 8 * * 1" --name "admin Scout" \
            --script run-admin-scout.py --no-agent --deliver origin
"""

import sys
import os

PROJECT_DIR = r"${MY_REPOS}\Documents\github\finance-team\insider-trading"
sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, os.path.join(PROJECT_DIR, "src"))
os.chdir(PROJECT_DIR)

from src.main import init_system, run_scout

init_system()
signals = run_scout("admin")

print(f"admin Scout — {len(signals)} signal(s)\n")
for s in signals:
    print(f"  {s.ticker}: {s.action} ({s.confidence:.0f}%) | {s.reasoning[:120]}")
print()

if not signals:
    print("No signals generated.")
    sys.exit(0)
