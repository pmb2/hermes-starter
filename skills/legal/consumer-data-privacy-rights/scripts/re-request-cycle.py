#!/usr/bin/env python3
"""90-Day re-request cycle for previously-deleted services."""
import csv, datetime, sys
from pathlib import Path

BASE = Path(__file__).parent
SVC = BASE / "services"
LOG = BASE / "logs"
RPT = BASE / "reports"
for d in (SVC, LOG, RPT): d.mkdir(exist_ok=True)
DS = datetime.datetime.now().strftime("%Y-%m-%d")
CYCLE = (datetime.datetime.now() - datetime.datetime(2026, 7, 29)).days // 90 + 1

deleted = set()
for lf in sorted(LOG.glob("action-log-*.csv")):
    with open(lf) as f:
        for row in csv.reader(f):
            if len(row) >= 3 and row[1] == "DELETION_CONFIRMED":
                deleted.add(row[2].lower())

dry = "--dry-run" in sys.argv
if dry:
    print(f"DRY RUN Cycle {CYCLE} — {len(deleted)} services")

for svc_dir in sorted(SVC.iterdir()):
    if not svc_dir.is_dir() or svc_dir.name not in deleted: continue
    if dry:
        print(f"  [dry] {svc_dir.name}"); continue
    (svc_dir / f"{DS}-re-request-cycle-{CYCLE}.txt").write_text(
        f"90-day re-request cycle {CYCLE} for {svc_dir.name}: please confirm "
        f"data remains deleted. Generated {DS}.\n")

(RPT / f"cycle-{CYCLE}-{DS}.md").write_text(
    f"Cycle {CYCLE}: {len(deleted)} services\n")
if not dry:
    print(f"Cycle {CYCLE}: {len(deleted)} re-requested")
