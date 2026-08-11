#!/usr/bin/env python3
"""
CCPA Auto-Responder — Deadline Enforcement Engine
====================================================
Reads the action log and checks for overdue statutory deadlines.
Sends automated follow-up emails when companies miss:

- Day 10: Must acknowledge receipt
- Day 45: Must provide data or confirm deletion
- Day 60: Demand letter for noncompliant companies
- Day 90: CPPA complaint escalation

Usage:
  python3 auto_responder.py --check       # Check overdue deadlines
  python3 auto_responder.py --send        # Send pending follow-ups
  python3 auto_responder.py --report      # Generate escalation report
"""

import csv, datetime, os, re, smtplib, ssl
from email.mime.text import MIMEText
from pathlib import Path

BASE = Path(__file__).parent.resolve()
LOGS = BASE / "logs"
SERVICES = BASE / "services"
RPT = BASE / "reports"

EMAIL_ADDR = os.environ.get("EMAIL_ADDRESS", "<your-email>@gmail.com")
EMAIL_PASS = os.environ.get("EMAIL_PASSWORD", "")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

PI_NAME = "the operator M Backus"

def load_timeline():
    timeline = {}
    for lf in sorted(LOGS.glob("action-log-*.csv")):
        with open(lf, encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) < 3: continue
                ts, action, service = row[0], row[1], row[2]
                try: dt = datetime.datetime.fromisoformat(ts.split(" UTC")[0].split(".")[0])
                except: dt = datetime.datetime.now()
                if service not in timeline: timeline[service] = []
                timeline[service].append({"date": dt, "action": action})
    return timeline

def check_overdue():
    tl = load_timeline()
    now = datetime.datetime.now()
    overdue = {"ack": [], "data": [], "demand": [], "cppla": []}
    for svc, events in tl.items():
        dsar = None
        for e in sorted(events, key=lambda x: x["date"]):
            if "DSAR_SENT" in e["action"] or "SENT" in e["action"]:
                dsar = e["date"]
        if not dsar: continue
        days = (now - dsar).days
        actions = {e["action"] for e in events}
        if days > 10 and not any("ACK" in a or "RECEIPT" in a for a in actions):
            overdue["ack"].append((svc, days))
        if days > 45 and not any("DATA_RECEIVED" in a for a in actions):
            overdue["data"].append((svc, days))
        if days > 60 and not any("DEMAND" in a for a in actions):
            overdue["demand"].append((svc, days))
        if days > 90 and not any("CPPA" in a for a in actions):
            overdue["cppla"].append((svc, days))
    return overdue

def find_email(service):
    safe = re.sub(r'[^a-z0-9_-]', '_', service.lower())[:50]
    d = SERVICES / safe
    if d.exists():
        for lf in d.glob("*.txt"):
            txt = lf.read_text(encoding="utf-8")
            m = re.search(r"VIA EMAIL: ([\w.@+-]+)", txt)
            if m: return m.group(1)
    return None

def send_email(to, subject, body):
    if not EMAIL_PASS: return False
    msg = MIMEText(body, "plain")
    msg["From"] = EMAIL_ADDR
    msg["To"] = to
    msg["Subject"] = subject
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=ctx) as s:
            s.login(EMAIL_ADDR, EMAIL_PASS)
            s.sendmail(EMAIL_ADDR, [to], msg.as_string())
        return True
    except: return False

def log_action(action, service, details=""):
    log = LOGS / f"action-log-{datetime.date.today().isoformat()}.csv"
    exists = log.exists()
    with open(log, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists: w.writerow(["Timestamp","Action","Service","Details"])
        w.writerow([datetime.datetime.now().isoformat(), action, service, details])

def cmd_check():
    overdue = check_overdue()
    total = sum(len(v) for v in overdue.values())
    if total == 0:
        print("✓ All services within compliance deadlines.")
        return
    for label, items in [("No acknowledgment (>10d)", "ack"),
                          ("No data received (>45d)", "data"),
                          ("Demand needed (>60d)", "demand"),
                          ("CPPA candidate (>90d)", "cppla")]:
        for svc, days in overdue[items]:
            print(f"  ⚠ {label}: {svc} ({days} days)")
    print(f"\nTotal: {total} overdue")

def cmd_send():
    overdue = check_overdue()
    sent = 0
    for svc, days in overdue["ack"]:
        email = find_email(svc)
        if not email:
            log_action("FOLLOWUP_PENDING", svc, "No email on file")
            continue
        subj = f"SECOND REQUEST: CCPA Data Rights Request — {svc}"
        body = f"""To Whom It May Concern,

On {datetime.datetime.now() - datetime.timedelta(days=days):%Y-%m-%d}, I submitted a CCPA/CPRA request to {svc}. I have not received an acknowledgment.

Under Cal. Civ. Code § 1798.110(d), acknowledgment was due within 10 days. This deadline has passed.

Please acknowledge receipt immediately. If I do not receive a response within 10 days, I will file a complaint with the California Privacy Protection Agency.

Sincerely,
{PI_NAME}"""
        if send_email(email, subj, body):
            log_action("FOLLOWUP_SENT", svc, "Ack follow-up sent")
            sent += 1
        else:
            log_action("FOLLOWUP_FAILED", svc, f"Send to {email} failed")
    for svc, days in overdue["data"]:
        log_action("DEMAND_PENDING", svc, f"Data overdue {days}d")
        sent += 1
    for svc, days in overdue["demand"]:
        log_action("CPPA_CANDIDATE", svc, f"Overdue {days}d")
        sent += 1
    print(f"Processed: {sent} actions")

def cmd_report():
    overdue = check_overdue()
    now = datetime.datetime.now()
    rpt = f"""# CCPA Auto-Responder Report
**{now:%Y-%m-%d %H:%M}**

## Overdue
- Ack (>10d): {len(overdue["ack"])}
- Data (>45d): {len(overdue["data"])}
- Demand (>60d): {len(overdue["demand"])}
- CPPA (>90d): {len(overdue["cppla"])}
"""
    rpt_path = RPT / f"auto-responder-{now:%Y-%m-%d}.md"
    rpt_path.write_text(rpt)
    print(f"Report: {rpt_path}")

if __name__ == "__main__":
    if "--check" in sys.argv: cmd_check()
    elif "--send" in sys.argv: cmd_send()
    elif "--report" in sys.argv: cmd_report()
    else: print(__doc__)