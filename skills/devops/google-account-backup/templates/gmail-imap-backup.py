#!/usr/bin/env python3
"""
Gmail IMAP backup script — downloads all emails + attachments via IMAP.
Saves to local folders, tracks progress for resumability.

Usage:
  python gmail-imap-backup.py --mode check-storage   # Analyze mailbox
  python gmail-imap-backup.py --mode backup           # Full download
  python gmail-imap-backup.py --mode backup --max-emails 100  # Dry run
"""

import imaplib
import email
import os
import sys
import time
import json
import argparse
from email.header import decode_header
from email.utils import parsedate_to_datetime

# ── CONFIG ──────────────────────────────────────────────────────────────────
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
USERNAME = "your-email@gmail.com"
PASSWORD = "your-app-password"          # Generate at myaccount.google.com/apppasswords

BACKUP_DIR = os.path.dirname(os.path.abspath(__file__))
EMAIL_DIR = os.path.join(BACKUP_DIR, "emails")
ATTACHMENT_DIR = os.path.join(BACKUP_DIR, "attachments")
PROGRESS_FILE = os.path.join(BACKUP_DIR, "progress.json")
# ────────────────────────────────────────────────────────────────────────────


def decode_mime_header(header_value):
    if not header_value:
        return "no_subject"
    parts = decode_header(header_value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(charset or "utf-8", errors="replace"))
            except Exception:
                result.append(part.decode("utf-8", errors="replace"))
        else:
            result.append(str(part))
    return "".join(result).strip() or "no_subject"


def safe_filename(name, max_len=120):
    name = "".join(c if c.isalnum() or c in "._- " else "_" for c in name)
    return name[:max_len].strip()


def download_attachments(msg, email_id, email_subject):
    saved = []
    if msg.is_multipart():
        for part in msg.walk():
            cd = str(part.get("Content-Disposition", ""))
            if "attachment" not in cd.lower():
                continue
            filename = part.get_filename()
            if not filename:
                continue
            filename = decode_mime_header(filename)
            safe_name = safe_filename(filename)
            ct = part.get_content_type()
            tf = "video" if "video" in ct else "image" if "image" in ct else "other"
            subj_dir = safe_filename(email_subject, 60)
            save_dir = os.path.join(ATTACHMENT_DIR, tf, subj_dir)
            os.makedirs(save_dir, exist_ok=True)
            fp = os.path.join(save_dir, safe_name)
            c = 1
            base, ext = os.path.splitext(fp)
            while os.path.exists(fp):
                fp = f"{base}_{c}{ext}"
                c += 1
            try:
                with open(fp, "wb") as f:
                    f.write(part.get_payload(decode=True))
                saved.append(fp)
            except Exception as e:
                print(f"    ERROR attachment {filename}: {e}")
    return saved


def save_email(msg, email_id):
    subject = decode_mime_header(msg.get("Subject", ""))
    date = msg.get("Date", "")
    from_addr = msg.get("From", "")
    try:
        dt = parsedate_to_datetime(date)
        date_folder = dt.strftime("%Y-%m")
    except Exception:
        date_folder = "unknown-date"
    save_dir = os.path.join(EMAIL_DIR, date_folder)
    os.makedirs(save_dir, exist_ok=True)
    safe_subj = safe_filename(subject, 80)
    fpath = os.path.join(save_dir, f"{email_id}_{safe_subj}.eml")
    with open(fpath, "wb") as f:
        f.write(msg.as_bytes())
    return fpath, subject, from_addr, date


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"last_uid": 0, "total_downloaded": 0, "run_count": 0}


def save_progress(prog):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(prog, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Gmail IMAP backup")
    parser.add_argument("--mode", choices=["backup", "check-storage"], default="backup")
    parser.add_argument("--max-emails", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    progress = load_progress()
    if progress["run_count"] == 0:
        print(f"Emails   -> {EMAIL_DIR}")
        print(f"Attachments -> {ATTACHMENT_DIR}")

    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    try:
        mail.login(USERNAME, PASSWORD)
    except imaplib.IMAP4.error as e:
        print(f"Login failed: {e}")
        print("Use an App Password from myaccount.google.com/apppasswords")
        sys.exit(1)
    print("Connected.")

    # List mailboxes for debugging
    status, mailboxes = mail.list()
    if status == "OK":
        print("Mailboxes found:")
        for mb in mailboxes:
            name = mb.decode("utf-8", errors="replace")
            if "All Mail" in name or "INBOX" in name:
                print(f"  {name}")

    # Select All Mail (must quote due to brackets)
    mailbox_names = ['"[Gmail]/All Mail"', "INBOX"]
    selected = False
    total_msgs = 0
    for mb in mailbox_names:
        status, messages = mail.select(mb, readonly=True)
        if status == "OK":
            selected = True
            total_msgs = int(messages[0])
            print(f"Selected: {mb} ({total_msgs} messages)")
            break
    if not selected:
        print("Could not select any mailbox.")
        return

    if args.mode == "check-storage":
        for sf, label in [("5000000", ">5MB"), ("1000000", "1-5MB"),
                          ("500000", "500K-1MB"), ("100000", "100K-500K")]:
            st, dt = mail.uid("search", None, f"LARGER {sf}")
            n = len(dt[0].split()) if dt[0] else 0
            print(f"  {label}: {n}")
        mail.logout()
        return

    # Backup mode
    st, dt = mail.uid("search", None, "ALL")
    all_uids = dt[0].split()
    last_uid = progress["last_uid"]
    new_uids = [u for u in all_uids if int(u) > last_uid] if last_uid > 0 else all_uids
    print(f"New to download: {len(new_uids)}")

    if args.max_emails > 0:
        new_uids = new_uids[:args.max_emails]

    downloaded = progress["total_downloaded"]
    start = time.time()
    bs = args.batch_size

    for b_start in range(0, len(new_uids), bs):
        batch = new_uids[b_start:b_start + bs]
        for i, uid_b in enumerate(batch):
            uid = uid_b.decode()
            idx = b_start + i + 1
            try:
                st, md = mail.uid("fetch", uid, "(RFC822)")
                if st != "OK":
                    continue
                raw = md[0][1]
                msg = email.message_from_bytes(raw)
                fpath, subj, frm, date = save_email(msg, uid)
                atts = download_attachments(msg, uid, subj)
                sz = len(raw)
                if idx % 25 == 0 or sz > 1024 * 1024 or len(atts) > 0:
                    szs = f" ({sz/1024/1024:.1f}MB)" if sz > 1024*1024 else ""
                    ats = f" [{len(atts)} atts]" if atts else ""
                    print(f"  [{idx}/{len(new_uids)}] {subj[:55]}{szs}{ats}")
                downloaded += 1
                if idx % 25 == 0:
                    progress["last_uid"] = int(uid)
                    progress["total_downloaded"] = downloaded
                    save_progress(progress)
            except Exception as e:
                print(f"  ERROR UID {uid}: {e}")

        progress["last_uid"] = int(batch[-1].decode())
        progress["total_downloaded"] = downloaded
        save_progress(progress)
        elapsed = time.time() - start
        rate = downloaded / elapsed * 3600 if elapsed else 0
        print(f"\nBatch done: {downloaded} dl'd ({rate:.0f}/hr)\n")

    elapsed = time.time() - start
    print(f"\nDONE: {downloaded} emails in {elapsed/60:.1f} min")
    mail.logout()


if __name__ == "__main__":
    main()
