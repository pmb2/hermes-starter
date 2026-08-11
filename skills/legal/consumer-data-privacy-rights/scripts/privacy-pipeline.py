#!/usr/bin/env python3
"""
Privacy Pipeline — CCPA/CPRA Data Rights Automation Engine

Commands:
  python3 privacy_pipeline.py status              # Current stats
  python3 privacy_pipeline.py search <query>       # Search brokers
  python3 privacy_pipeline.py generate --service N  # Generate DSAR letter
  python3 privacy_pipeline.py send --service N      # Mark as sent
  python3 privacy_pipeline.py receive --service N   # Mark data received
  python3 privacy_pipeline.py delete --service N    # Mark deletion confirmed
  python3 privacy_pipeline.py next-batch [N]        # Next N to process
  python3 privacy_pipeline.py report                # Full status report
  python3 privacy_pipeline.py help                  # This help
"""

import csv, json, os, sys, datetime, re
from pathlib import Path

BASE_DIR = Path(__file__).parent
SERVICES_DIR = BASE_DIR / "services"
LOG_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"
BROKERS_CSV = BASE_DIR / "merged_brokers.csv"

TIMESTAMP = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
DATE_STAMP = datetime.datetime.now().strftime("%Y-%m-%d")

for d in [SERVICES_DIR, LOG_DIR, REPORTS_DIR]:
    d.mkdir(exist_ok=True)

def log_action(action, service, details=""):
    log_file = LOG_DIR / f"action-log-{DATE_STAMP}.csv"
    exists = log_file.exists()
    with open(log_file, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["Timestamp", "Action", "Service", "Details"])
        w.writerow([TIMESTAMP, action, service, details])

def load_brokers():
    if not BROKERS_CSV.exists():
        print(f"ERROR: merged_brokers.csv not found. Run the data broker merge script first.")
        sys.exit(1)
    with open(BROKERS_CSV, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def cmd_status():
    brokers = load_brokers()
    tracker_files = sorted(LOG_DIR.glob("action-log-*.csv"))
    sent = set(); received = set(); deleted = set()
    for lf in tracker_files:
        with open(lf, "r") as f:
            for row in csv.reader(f):
                if len(row) >= 3:
                    if row[1] == "DSAR_SENT": sent.add(row[2].lower())
                    elif row[1] == "DATA_RECEIVED": received.add(row[2].lower())
                    elif row[1] == "DELETION_CONFIRMED": deleted.add(row[2].lower())
    
    print("=" * 60)
    print(f"DATA PRIVACY PIPELINE — {DATE_STAMP}")
    print("=" * 60)
    print(f"\n  Brokers catalogued:     {len(brokers)}")
    print(f"  DSARs sent:            {len(sent)}")
    print(f"  Data received:         {len(received)}")
    print(f"  Deletions confirmed:   {len(deleted)}")
    print(f"  Not started:           {len(brokers) - len(sent)}")
    
    type_counts = {}
    for b in brokers:
        t = b.get("Type", "Unknown") or "Unknown"
        type_counts[t] = type_counts.get(t, 0) + 1
    print(f"\n  Top categories:")
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1])[:5]:
        print(f"    {t}: {c}")

def cmd_search(query):
    brokers = load_brokers()
    matches = [b for b in brokers if query.lower() in b["Name"].lower()]
    print(f"\nFound {len(matches)} matches:\n")
    for b in matches[:20]:
        print(f"  • {b['Name']}")
        print(f"    Type: {b['Type']}  |  {b['Website']}")
        if b.get('OptOut URL'): print(f"    Opt-out: {b['OptOut URL']}")
        if b.get('Privacy Email'): print(f"    Email: {b['Privacy Email']}")
        print()
    if len(matches) > 20:
        print(f"  ... and {len(matches) - 20} more")

def cmd_generate(idx_str):
    brokers = load_brokers()
    try:
        idx = int(idx_str) - 1
        broker = brokers[idx]
    except (ValueError, IndexError):
        print(f"ERROR: invalid index '{idx_str}'. Use 'next-batch' to find valid indices.")
        return
    
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', broker['Name'].lower())[:50]
    svc_dir = SERVICES_DIR / safe_name
    svc_dir.mkdir(exist_ok=True)
    
    email = broker.get('Privacy Email', '') or "privacy@" + (re.sub(r'https?://(?:www\.)?([^/]+).*', r'\1', broker.get('Website', 'example.com')) if broker.get('Website') else 'example.com')
    
    letter = f"""=== COMBINED CCPA/CPRA DATA RIGHTS REQUEST ===
Generated: {TIMESTAMP}
Target: {broker['Name']} (Index {idx+1} of {len(brokers)})
Website: {broker.get('Website', '')}
Contact: {email}
Opt-Out URL: {broker.get('OptOut URL', '')}

=== LETTER ===

{DATE_STAMP}

VIA EMAIL: {email}

{broker['Name']}
Attn: Privacy Officer / Legal Department

RE: COMBINED DATA SUBJECT ACCESS REQUEST AND DELETION REQUEST
    UNDER THE CALIFORNIA CONSUMER PRIVACY ACT (CCPA/CPRA)

To the Privacy Officer:

I am a California resident exercising my rights under the California Consumer Privacy
Act of 2018 (Cal. Civ. Code § 1798.100 et seq.), as amended by the California Privacy
Rights Act (CPRA).

PART I — RIGHT TO KNOW (§ 1798.110)
I request disclosure of: (1) categories of personal info collected, (2) sources,
(3) business purpose, (4) third parties shared with, (5) specific pieces of personal
info (complete data export in portable format), (6) categories disclosed for business
purpose, (7) categories sold or shared.

PART II — RIGHT TO DELETE (§ 1798.105)
Upon receipt and review of the above data, I request immediate deletion of all
personal info you hold about me, including notification to all service providers,
contractors, and third parties.

IDENTIFICATION:
- Full Name: [FILL IN]
- Email: [FILL IN]
- Phone: [FILL IN]

Please confirm receipt within 10 days. Respond within 45 days.

Sincerely,

[FILL IN YOUR NAME]
[FILL IN YOUR EMAIL]
"""
    letter_path = svc_dir / f"{DATE_STAMP}-combined-request.txt"
    with open(letter_path, "w") as f:
        f.write(letter)
    print(f"\n✓ Letter generated for: {broker['Name']}")
    print(f"  Saved: {letter_path}")
    print(f"\n  Send via: {email}")
    print(f"  Then run: python3 privacy_pipeline.py send --service {idx+1}")

def cmd_mark(action, idx_str):
    brokers = load_brokers()
    try:
        idx = int(idx_str) - 1
        name = brokers[idx]['Name']
    except (ValueError, IndexError):
        print(f"ERROR: invalid index '{idx_str}'")
        return
    log_action(action, name)
    print(f"✓ {action}: {name}")

def cmd_next_batch(n=10):
    brokers = load_brokers()
    tracker_files = sorted(LOG_DIR.glob("action-log-*.csv"))
    sent = set()
    for lf in tracker_files:
        with open(lf, "r") as f:
            for row in csv.reader(f):
                if len(row) >= 3 and row[1] == "DSAR_SENT":
                    sent.add(row[2].lower())
    
    remaining = [(i, b) for i, b in enumerate(brokers, 1)
                 if b['Name'].strip().lower() not in sent]
    
    print(f"\nNext {min(n, len(remaining))} of {len(remaining)} remaining:\n")
    for i, (idx, b) in enumerate(remaining[:n]):
        print(f"  [{idx}] {b['Name']}")
        print(f"       Type: {b['Type']}  |  {b['Website']}")
        if b.get('OptOut URL'): print(f"       Opt-out: {b['OptOut URL']}")
        if b.get('Privacy Email'): print(f"       Email: {b['Privacy Email']}")
        print()

def cmd_report():
    brokers = load_brokers()
    tracker_files = sorted(LOG_DIR.glob("action-log-*.csv"))
    sent = set(); received = set(); deleted = set()
    for lf in tracker_files:
        with open(lf, "r") as f:
            for row in csv.reader(f):
                if len(row) >= 3:
                    if row[1] == "DSAR_SENT": sent.add(row[2].lower())
                    elif row[1] == "DATA_RECEIVED": received.add(row[2].lower())
                    elif row[1] == "DELETION_CONFIRMED": deleted.add(row[2].lower())
    
    report = f"""# Data Privacy Pipeline — Status Report
**Date:** {DATE_STAMP}

## Overview
| Metric | Count |
|--------|-------|
| Brokers catalogued | {len(brokers)} |
| DSARs sent | {len(sent)} |
| Data packages received | {len(received)} |
| Deletions confirmed | {len(deleted)} |
| Not started | {len(brokers) - len(sent)} |

## Type Distribution
"""
    type_counts = {}
    for b in brokers:
        t = b.get("Type", "Unknown") or "Unknown"
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        report += f"- **{t}:** {c}\n"
    report += f"\n*Next 90-day re-request cycle: {(datetime.datetime.now() + datetime.timedelta(days=90)).strftime('%Y-%m-%d')}*\n"
    
    report_path = REPORTS_DIR / f"status-{DATE_STAMP}.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\n✓ Report: {report_path}")

HELP = """
Commands:
  status                     Pipeline statistics
  search <query>             Search brokers by name
  generate --service N       Generate DSAR letter (N = index from next-batch)
  send --service N           Mark DSAR as sent
  receive --service N        Mark data received
  delete --service N         Mark deletion confirmed
  next-batch [N]             Show next N brokers to process
  report                     Generate status report
  help                       This message
"""

def main():
    if len(sys.argv) < 2:
        print(HELP); return
    
    cmd = sys.argv[1].lower()
    if cmd == "status": cmd_status()
    elif cmd == "search":
        if len(sys.argv) < 3: print("Usage: privacy_pipeline.py search <query>")
        else: cmd_search(sys.argv[2])
    elif cmd == "generate":
        if "--service" in sys.argv:
            idx = sys.argv.index("--service") + 1
            if idx < len(sys.argv): cmd_generate(sys.argv[idx])
            else: print("Usage: privacy_pipeline.py generate --service N")
        else: print("Usage: privacy_pipeline.py generate --service N")
    elif cmd in ("send", "receive", "delete"):
        action_map = {"send": "DSAR_SENT", "receive": "DATA_RECEIVED", "delete": "DELETION_CONFIRMED"}
        if "--service" in sys.argv:
            idx = sys.argv.index("--service") + 1
            if idx < len(sys.argv): cmd_mark(action_map[cmd], sys.argv[idx])
            else: print(f"Usage: privacy_pipeline.py {cmd} --service N")
        else: print(f"Usage: privacy_pipeline.py {cmd} --service N")
    elif cmd == "next-batch":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        cmd_next_batch(n)
    elif cmd == "report": cmd_report()
    else: print(HELP)

if __name__ == "__main__":
    main()
