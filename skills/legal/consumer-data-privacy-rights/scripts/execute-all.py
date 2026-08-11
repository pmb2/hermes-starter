#!/usr/bin/env python3
"""
Bulk Execution — Mark All Generated Letters as SENT
======================================================
Reads every service directory, logs each as SENT in the action log,
updates TRACKER.md with submission dates + 45-day deadlines,
and updates REGISTRY.md statuses.

Usage:
  python3 execute_all.py     # Normal mode
  python3 execute_all.py --dry-run  # Preview only
"""

import csv, datetime, os, re, sys
from pathlib import Path

BASE = Path(__file__).parent.resolve()
SERVICES = BASE / "services"
LOGS = BASE / "logs"
TRACKER = BASE / "TRACKER.md"
REGISTRY = BASE / "REGISTRY.md"

DATE = datetime.datetime.now().strftime("%Y-%m-%d")
TS = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
DEADLINE = (datetime.datetime.now() + datetime.timedelta(days=45)).strftime("%Y-%m-%d")
DRY = "--dry-run" in sys.argv

def find_letters():
    results = []
    for d in sorted(SERVICES.iterdir()):
        if not d.is_dir(): continue
        letter = d / "001-combined-request.txt"
        if not letter.exists(): continue
        txt = letter.read_text(encoding="utf-8")
        m = re.search(r"Target:\s*(.+)", txt)
        name = m.group(1).strip() if m else d.name.replace("_", " ").title()
        em = re.search(r"VIA EMAIL:\s*([\w.@+-]+)", txt)
        email = em.group(1) if em else "unknown"
        results.append({"name": name, "dir": d.name, "email": email, "path": str(letter)})
    return results

def log_actions(letters):
    log = LOGS / f"action-log-{datetime.date.today().isoformat()}.csv"
    exists = log.exists()
    with open(log, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists: w.writerow(["Timestamp","Action","Service","Email","Letter"])
        for s in letters:
            w.writerow([TS, "DSAR_SENT", s["name"], s["email"], s["path"]])
    return log

def update_tracker(letters):
    entry = f"\n## Batch Execution — {DATE}\n\n**{len(letters)} letters sent** on {TS}\n"
    entry += f"**45-day deadline:** {DEADLINE}\n\n| Service | Email | Sent | Deadline |\n"
    entry += "|---------|-------|------|----------|\n"
    for s in letters:
        entry += f"| {s['name']} | {s['email']} | {DATE} | {DEADLINE} |\n"

    content = TRACKER.read_text(encoding="utf-8") if TRACKER.exists() else ""
    # Replace existing batch section or append
    if "## Batch Execution" in content:
        content = re.sub(r"## Batch Execution.*?(?=\n## |\Z)", "", content, flags=re.DOTALL).strip()
    content += entry
    TRACKER.write_text(content, encoding="utf-8")
    return len(letters)

def update_registry(letters):
    if not REGISTRY.exists(): return 0
    content = REGISTRY.read_text(encoding="utf-8")
    # Update quick stats
    total = len(letters)
    for s in letters:
        name = s["name"]
        for line in content.split("\n"):
            m = re.search(r"^\|[^|]+\|([^|]+)\|", line)
            if m and name.lower() in m.group(1).strip().lower():
                content = content.replace(
                    line,
                    line.replace("🔴 Not Started", "🟡 DSAR Sent")
                        .replace("| — | — | — | — |", f"| {DATE} | — | — | — |")
                )
                break
    # Update quick stats counts
    content = re.sub(r'\*\*DSAR sent:\*\* \d+/\d+',
                     f'**DSAR sent:** {total}/{len(content.split(chr(10)))}',
                     content)
    REGISTRY.write_text(content, encoding="utf-8")
    return total

def main():
    letters = find_letters()
    if not letters:
        print("No letters found. Run batch_generate.py first.")
        return

    print(f"Letters found: {len(letters)}")
    if DRY:
        print("DRY RUN — no changes written")
        for s in letters[:5]:
            print(f"  [dry] {s['name']}")
        if len(letters) > 5: print(f"  ... and {len(letters)-5} more")
        return

    log = log_actions(letters)
    print(f"Action log: {log}")

    tracker_count = update_tracker(letters)
    print(f"TRACKER.md: {tracker_count} entries")

    registry_count = update_registry(letters)
    print(f"REGISTRY.md: {registry_count} services updated")

    # Categorize summary
    cats = {"Credit/Financial": 0, "People Search": 0, "Marketing/B2B": 0, "Other": 0}
    kw_map = {
        "Credit/Financial": ["equifax","experian","transunion","lexisnexis","chexsystems",
                             "innovis","first advantage","hireright","sagestream","clarity",
                             "datax","early warning","telecheck","certegy","mib","milliman","verisk"],
        "People Search": ["spokeo","whitepages","beenverified","truthfinder","intelius",
                          "radaris","mylife","peoplefinders","nuwber","fastpeoplesearch",
                          "truepeoplesearch","thatsthem","peekyou","familytreenow","zabasearch"],
        "Marketing/B2B": ["acxiom","epsilon","oracle","liveramp","zoominfo","apollo",
                          "seamless","lusha","clearbit","crunchbase","trade desk","criteo"]
    }
    for s in letters:
        sl = s["name"].lower()
        assigned = False
        for cat, kws in kw_map.items():
            if any(k in sl for k in kws):
                cats[cat] += 1; assigned = True; break
        if not assigned: cats["Other"] += 1

    print(f"\nBreakdown: {', '.join(f'{k}: {v}' for k,v in cats.items() if v)}")
    print(f"Total: {len(letters)}")
    print(f"Next 45-day deadline: {DEADLINE}")

if __name__ == "__main__":
    main()