#!/usr/bin/env python3
"""
CCPA Correspondence Listener
=============================
Monitors Gmail inbox for data broker responses to DSAR/deletion requests.
Auto-classifies, logs, and triggers follow-ups when deadlines approach.

Usage:
  python3 listener.py --once       # Single scan
  python3 listener.py --daemon     # Continuous polling (every 30min)

Setup:
  1. Enable 2FA on Google account
  2. Generate App Password at https://myaccount.google.com/apppasswords
  3. Copy .env.template to .env and fill in EMAIL_PASSWORD
"""

import csv, datetime, email, imaplib, os, re, sys, time, ssl
from email.mime.text import MIMEText
from pathlib import Path

BASE = Path(__file__).parent.resolve()
LOGS = BASE / "logs"
EMAIL_ADDR = os.environ.get("EMAIL_ADDRESS", "<your-email>@gmail.com")
EMAIL_PASS = os.environ.get("EMAIL_PASSWORD", "")
IMAP_SERVER = "imap.gmail.com"
POLL_INTERVAL = 1800  # 30 min

# Known broker domains for sender classification
MANUAL_DOMAINS = {
    "experian.com": "Experian", "equifax.com": "Equifax", "transunion.com": "TransUnion",
    "lexisnexis.com": "LexisNexis", "chexsystems.com": "ChexSystems",
    "earlywarning.com": "Early Warning", "innovis.com": "Innovis",
    "acxiom.com": "Acxiom", "epsilon.com": "Epsilon", "oracle.com": "Oracle Data Cloud",
    "liveramp.com": "LiveRamp", "zoominfo.com": "ZoomInfo", "spokeo.com": "Spokeo",
    "whitepages.com": "Whitepages", "beenverified.com": "BeenVerified",
    "truthfinder.com": "TruthFinder", "intelius.com": "Intelius",
    "radaris.com": "Radaris", "mylife.com": "MyLife",
}

def clean(text):
    parts = []
    for chunk, enc in email.header.decode_header(text):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            parts.append(str(chunk))
    return "".join(parts)

def classify(subject, body):
    text = (subject + " " + body[:2000]).lower()
    if any(w in text for w in ["bounce", "delivery failed", "undeliverable", "550"]):
        return "BOUNCE"
    if any(w in text for w in ["ccpa request", "privacy request", "acknowledge",
                                "identity verification", "case number"]):
        return "ACKNOWLEDGMENT"
    if any(w in text for w in ["your data", "data package", "data export",
                                "download your data", "data attached"]):
        return "DATA_RECEIVED"
    if any(w in text for w in ["deletion complete", "deleted your data", "data removed",
                                "confirmed deletion", "has been deleted"]):
        return "DELETION_CONFIRMED"
    if any(w in text for w in ["unable to verify", "cannot process", "denied",
                                "additional information needed", "rejected"]):
        return "NEEDS_ATTENTION"
    if any(w in text for w in ["follow-up", "second notice", "response required",
                                "action needed", "respond by"]):
        return "FOLLOWUP_NEEDED"
    return "UNKNOWN"

def scan():
    if not EMAIL_PASS:
        return [], "NO_PASSWORD"
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993)
        mail.login(EMAIL_ADDR, EMAIL_PASS)
        mail.select("INBOX")
    except Exception as e:
        return [], f"FAILED: {e}"

    since = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%d-%b-%Y")
    _, data = mail.search(None, f'(SINCE {since})')
    if _ != "OK":
        mail.logout(); return [], "SEARCH_FAILED"

    matches = []
    for mid in data[0].split()[-50:]:
        _, msg_data = mail.fetch(mid, "(RFC822)")
        if _ != "OK": continue
        msg = email.message_from_bytes(msg_data[0][1])
        sender = clean(msg.get("From", ""))
        subject = clean(msg.get("Subject", "")[:120])
        date = clean(msg.get("Date", ""))
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try: body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    except: pass
                    break
        else:
            try: body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
            except: pass

        dm = re.search(r"@([\w.-]+)", sender)
        domain = dm.group(1).lower() if dm else ""
        broker = "UNKNOWN"
        if domain in MANUAL_DOMAINS:
            broker = MANUAL_DOMAINS[domain]
        # Also load from merged_brokers.csv if available
        csv_path = BASE / "merged_brokers.csv"
        if csv_path.exists() and broker == "UNKNOWN":
            with open(csv_path, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    site = row.get("Website", "")
                    if domain in site.lower():
                        broker = row["Name"]
                        break

        is_ccpa = any(w in subject.lower() for w in
            ["ccpa","cpra","privacy","dsar","deletion","opt-out","opt out",
             "your data","data subject","consumer request"])
        if not is_ccpa and broker == "UNKNOWN": continue

        cl = classify(subject, body)
        matches.append({
            "date": date, "sender": sender, "broker": broker,
            "subject": subject, "classification": cl,
            "body_snippet": body[:400].replace("\n", " ").strip(),
        })

    mail.logout()
    return matches, "OK"

def log_matches(matches):
    if not matches: return
    log = LOGS / f"listener-{datetime.date.today().isoformat()}.csv"
    exists = log.exists()
    with open(log, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["Timestamp","Date","Sender","Broker","Subject","Classification"])
        for m in matches:
            w.writerow([datetime.datetime.now().isoformat(), m["date"],
                        m["sender"], m["broker"], m["subject"], m["classification"]])
    return log

def run_once():
    matches, status = scan()
    if status == "NO_PASSWORD":
        print("⚠ No EMAIL_PASSWORD in .env. Set up: cp .env.template .env && edit .env")
        return
    if status.startswith("FAILED"):
        print(f"✗ {status}"); return
    print(f"Found {len(matches)} CCPA-related emails")
    if matches:
        log = log_matches(matches)
        urgent = [m for m in matches if m["classification"] in ("NEEDS_ATTENTION","BOUNCE","FOLLOWUP_NEEDED")]
        if urgent:
            print(f"\n⚠ URGENT — {len(urgent)} items need attention:")
            for m in urgent:
                print(f"   {m['broker']}: {m['subject']}")
        if log: print(f"Logged: {log}")

def run_daemon():
    print(f"Listener starting — polling every {POLL_INTERVAL}s")
    while True:
        try:
            matches, _ = scan()
            if matches: log_matches(matches)
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt: break
        except: time.sleep(60)

if __name__ == "__main__":
    if "--daemon" in sys.argv: run_daemon()
    else: run_once()