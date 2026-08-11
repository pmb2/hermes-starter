#!/usr/bin/env python3
"""
Sync REGISTRY.md — Add broker targets from action log as new category.
Reconciles the registry with actual sent letters, updates quick stats.

Usage:
  python3 sync_registry.py
"""

import csv, datetime, re
from pathlib import Path

BASE = Path(__file__).parent.resolve()
REGISTRY = BASE / "REGISTRY.md"
LOGS = BASE / "logs"
DATE = datetime.date.today().isoformat()

# Read action log to get all sent services
services = set()
for lf in sorted(LOGS.glob("action-log-*.csv")):
    with open(lf, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("Action") == "DSAR_SENT":
                services.add(row["Service"])

if not services:
    print("No sent services found in action logs.")
    return

# Categorize
cats = {
    "Credit Bureaus & Financial": [], "People Search Sites": [],
    "Marketing & Advertising": [], "B2B Sales Intelligence": [],
    "Employment & Background": [], "Insurance & Medical": [], "Other": [],
}
kw = {
    "Credit Bureaus & Financial": ["equifax","experian","transunion","lexisnexis",
        "chexsystems","innovis","clarity","datax","sagestream","early warning",
        "telecheck","certegy","corelogic","choicepoint"],
    "People Search Sites": ["spokeo","whitepages","411.com","beenverified",
        "truthfinder","intelius","radaris","mylife","peoplefinders","checkpeople",
        "peoplelooker","nuwber","fastpeoplesearch","truepeoplesearch","thatsthem",
        "peekyou","familytreenow","cocofinder","zabasearch","us search"],
    "Marketing & Advertising": ["acxiom","epsilon","oracle","liveramp","trade desk",
        "criteo","tapad","lotame","zeta","merkle","infutor","quantcast","comscore",
        "nielsen","exelate","adstra","6sense","demandbase","bombora"],
    "B2B Sales Intelligence": ["zoominfo","apollo","seamless","lusha","hunter",
        "clearbit","rocketreach","signalhire","crunchbase","pitchbook"],
    "Employment & Background": ["first advantage","hireright","checkr"],
    "Insurance & Medical": ["mib","milliman","verisk","iso"],
}
for s in services:
    assigned = False
    for cat, kws in kw.items():
        if any(k in s.lower() for k in kws):
            cats[cat].append(s); assigned = True; break
    if not assigned: cats["Other"].append(s)

# Build broker section
idx = 0
section = f"\n## Data Brokers\n\n>DSAR+Deletion sent {DATE}.\n\n| # | Broker | Category | Status | Sent | Received | Deleted |\n"
section += "|---|--------|----------|--------|------|----------|---------|\n"
for cat, entries in cats.items():
    for s in entries:
        idx += 1
        section += f"| {idx} | {s} | {cat} | 🟡 DSAR Sent | {DATE} | — | — |\n"

# Read existing registry, insert broker section before Quick Stats
content = REGISTRY.read_text(encoding="utf-8")
qs = content.find("## Quick Stats")
if qs > 0:
    content = content[:qs] + section + "\n" + content[qs:]
else:
    content += section

# Update quick stats
total_services = len(re.findall(r"^\| \d+ \|", content, re.MULTILINE))
content = re.sub(r'\*\*Total services tracked:\*\* \d+', f'**Total services tracked:** {total_services}', content)
content = re.sub(r'\*\*DSAR sent:\*\* \d+/\d+', f'**DSAR sent:** {len(services)}/{total_services}', content)

REGISTRY.write_text(content, encoding="utf-8")
print(f"Synced: +{len(services)} broker targets → REGISTRY.md")
print(f"Total tracked: {total_services}")