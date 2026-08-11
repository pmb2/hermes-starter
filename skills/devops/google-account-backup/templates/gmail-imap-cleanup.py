#!/usr/bin/env python3
"""
Gmail IMAP cleanup script — bulk-deletes ALL emails after backup confirmation.

🚨 CRITICAL: Gmail IMAP deletion is NON-STANDARD.
Standard STORE +FLAGS \\Deleted + EXPUNGE does NOT work in Gmail
(messages stay in All Mail and still count against quota).
This script uses the correct X-GM-LABELS approach (Gmail IMAP extension)
to move messages to Trash before permanent deletion.

Prerequisites:
  - Local backup confirmed complete (download all emails via gmail-imap-backup.py first)
  - App Password from myaccount.google.com/apppasswords
  - Mailbox name quoting: select('"[Gmail]/All Mail"', readonly=False)
  - This is SLOW (~100 UIDs/min). For 50k+ messages, use the web UI instead.

Usage:
  python gmail-imap-cleanup.py                    # Delete all from All Mail
  python gmail-imap-cleanup.py --dry-run           # Count only, no deletion
  python gmail-imap-cleanup.py --older-than 365    # Delete emails older than N days
"""

import imaplib, time, json, os, sys

# ── CONFIG ──────────────────────────────────────────────────────────────────
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
USERNAME = "your-email@gmail.com"
PASSWORD = "your-app-password"          # Generate at myaccount.google.com/apppasswords

# List of mailboxes to clean (in order)
MAILBOXES = [
    '"[Gmail]/All Mail"',
    '"[Gmail]/Trash"',
    '"[Gmail]/Spam"',
]
# ────────────────────────────────────────────────────────────────────────────


def delete_from_mailbox(mail, mailbox_name, dry_run=False, older_than=None):
    """Delete all (or filtered) messages from a mailbox. Returns count."""
    try:
        status, msgs = mail.select(mailbox_name, readonly=False)
        if status != "OK":
            print(f"  SKIP {mailbox_name}: cannot select")
            return 0
        
        total = int(msgs[0])
        if total == 0:
            print(f"  {mailbox_name}: 0 messages (nothing to do)")
            return 0
        
        if older_than:
            # Search for messages before a date (format: "DD-Mon-YYYY" e.g. "1-Jan-2024")
            import datetime
            cutoff = older_than if isinstance(older_than, str) else (
                datetime.date.today() - datetime.timedelta(days=older_than)
            ).strftime("%d-%b-%Y")
            status, data = mail.uid('search', None, f'BEFORE {cutoff}')
            if status != "OK" or not data[0]:
                print(f"  {mailbox_name}: 0 old messages to delete")
                return 0
            uids = data[0].split()
        else:
            status, data = mail.uid('search', None, 'ALL')
            if status != "OK" or not data[0]:
                print(f"  {mailbox_name}: search failed")
                return 0
            uids = data[0].split()
        
        count = len(uids)
        print(f"  {mailbox_name}: {count} messages to delete")
        
        if dry_run:
            print(f"    (dry-run, skipping)")
            return count
        
        # Gmail IMAP requires X-GM-LABELS to actually delete
        # Standard STORE +FLAGS \Deleted + EXPUNGE does NOT work in Gmail
        GMAIL_BATCH = 100
        deleted = 0
        
        if mailbox_name == '"[Gmail]/All Mail"':
            # All Mail: use X-GM-LABELS to add Trash + Deleted labels
            print(f"    Moving to Trash via X-GM-LABELS (slow ~100/min)...")
            for i in range(0, count, GMAIL_BATCH):
                batch = uids[i:i+GMAIL_BATCH]
                for uid_bytes in batch:
                    uid = uid_bytes.decode()
                    try:
                        mail.uid('STORE', uid, '+X-GM-LABELS', '(\Trash \Deleted)')
                        deleted += 1
                    except Exception as e:
                        print(f"    Error UID {uid}: {e}")
                pct = deleted / count * 100
                print(f"    Trashed {deleted}/{count} ({pct:.0f}%)", end='\r')
            print()
            
            # Empty Trash
            print(f"    Emptying Trash...")
            try:
                mail.select('"[Gmail]/Trash"', readonly=False)
                mail.uid('STORE', '1:*', '+FLAGS', '\Deleted')
                mail.expunge()
                print(f"    ✓ Trash emptied")
            except Exception as e:
                print(f"    Error emptying Trash: {e}")
        else:
            # Trash/Spam/Drafts: standard \Deleted + EXPUNGE works fine
            for i in range(0, count, GMAIL_BATCH):
                batch = uids[i:i+GMAIL_BATCH]
                batch_str = ','.join(uid.decode() for uid in batch)
                mail.uid('store', batch_str, '+FLAGS', '\Deleted')
                deleted += len(batch)
            mail.expunge()
            print(f"    ✓ Purged {deleted} messages")
        
        return deleted
    
    except Exception as e:
        print(f"  ERROR on {mailbox_name}: {e}")
        return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Gmail IMAP cleanup")
    parser.add_argument("--dry-run", action="store_true", help="Count only, don't delete")
    parser.add_argument("--older-than", type=int, default=0,
                       help="Delete emails older than N days (0 = all)")
    args = parser.parse_args()
    
    if args.dry_run:
        print("DRY RUN — no deletions will be performed")
    
    print(f"Connecting to {IMAP_SERVER}:{IMAP_PORT}...")
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    try:
        mail.login(USERNAME, PASSWORD)
    except imaplib.IMAP4.error as e:
        print(f"Login failed: {e}")
        print("Use an App Password from myaccount.google.com/apppasswords")
        sys.exit(1)
    print("Connected.\n")
    
    total_deleted = 0
    for mb in MAILBOXES:
        n = delete_from_mailbox(mail, mb, dry_run=args.dry_run,
                                older_than=args.older_than if args.older_than else None)
        total_deleted += n
        
        # Re-select the mailbox (expunge affects selection state)
        try:
            mail.select(mb, readonly=False)
        except:
            pass
    
    mode = "DRY RUN" if args.dry_run else "CLEANUP"
    print(f"\n{'='*50}")
    print(f"{mode} COMPLETE")
    print(f"  Total messages processed: {total_deleted}")
    print(f"{'='*50}")
    
    mail.logout()


if __name__ == "__main__":
    main()
