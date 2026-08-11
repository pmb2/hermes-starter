# Builder Email Watchdog v4 — Working Example

Full working script from the session. Path in backup: `hermes-system-backup/scripts/watch_builder_emails.py`
Live path: `~/AppData/Local/hermes/scripts/watch_builder_emails.py`

## What This Watchdog Does

1. Connects to Gmail via IMAP (App Password auth)
2. Finds builder emails (Lennar, DR Horton, Pulte, etc.) from the last 7 days
3. Checks Sent folder to see if we replied already
4. For new unanswered emails: extracts body, generates contextual draft, saves to [Gmail]/Drafts
5. Reports new emails + draft previews to Discord
6. Exits silently if nothing new

## Key Design Decisions

- **UID tracking**: Stores last-processed UID, never re-processes old emails
- **Message-ID dedup**: Stores reported Message-IDs, won't re-report across restarts
- **Sent folder check**: Three search strategies (thread ref, recipient email) to confirm if replied
- **Contextual drafts**: Keyword-matched response templates based on email content (lots, pricing, documents)
- **Performance**: 7-day window, 30-email cap, 90s wall-clock timeout, header-first fetch
- **Format**: Zero blank lines between items, Unicode emoji, compact layout per discord-report-format skill

## State File

Stored at `.builder_watchdog_state.json` alongside the script. Contains:
```json
{
  "last_uid": 15432,
  "reported_ids": ["msgid1@mail.gmail.com", "msgid2@mail.gmail.com"]
}
```

## Cron Configuration

```yaml
job_id: 651d353fb925
name: Builder Email Watchdog
script: watch_builder_emails.py
no_agent: true
schedule: every 30m
deliver: origin
```

## Output Format

```
❗ **Builder Email Watchdog | 2 new, 1 drafts, 0 already replied**
━━━━━━━━━━━━━━━━━━━━━━
**Lennar**
📥 `Re: Land inquiry`
⏰ Thu, 18 Jun 2026 09:23:45 -0400
> Thanks for reaching out. We are interested...

━━━━━━━━━━━━━━━━━━━━━━
📝 **Drafts Created**
**Lennar** — Re: `Land inquiry`
> Hi there, Thank you for your inquiry...

━━━━━━━━━━━━━━━━━━━━━━
🔍 Checked Jun 18, 12:34 PM ET
```
