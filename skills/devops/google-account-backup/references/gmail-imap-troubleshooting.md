# Gmail IMAP Troubleshooting

## IMAP Connection Errors

### "[ALERT] Application-specific password required"
**Cause:** 2-Step Verification is enabled on the account. Regular passwords
are rejected for IMAP.

**Fix:** Generate an App Password at
`https://myaccount.google.com/apppasswords`.
- Requires 2FA to be enabled
- App Password is 16 characters, displayed with spaces (remove them)
- One App Password per device/application (name them descriptively)

### "BAD Could not parse command" on mail.select()
**Cause:** The mailbox name `[Gmail]/All Mail` contains brackets that need
quoting in the IMAP SELECT command.

**Fix:** Use double quotes around the name, wrapped in Python single quotes:
```python
mail.select('"[Gmail]/All Mail"', readonly=True)
```

### Connection timeout / too many connections
Gmail limits concurrent IMAP connections. If a previous script crashed,
its connection may still be open for ~10 minutes.

**Fix:** Close all connections and retry:
```python
mail.logout()
time.sleep(5)
```

## Performance

### Batch Size
- Batch of 50 per IMAP fetch call: ~16,000 emails/hour
- Increase batch_size to 100 for slightly better throughput
- Don't exceed 200 — Gmail may throttle

### Progress Tracking
Always save progress after every 10-100 messages:
```json
{"last_uid": 136811, "total_downloaded": 8995}
```
On restart, only fetch UIDs greater than `last_uid`.

## Gmail Mailbox Names

| Mailbox | IMAP Name | Purpose |
|---------|-----------|---------|
| Inbox | `INBOX` | Received messages |
| All Mail | `"[Gmail]/All Mail"` | Everything (include sent) |
| Sent | `"[Gmail]/Sent Mail"` | Sent messages |
| Drafts | `"[Gmail]/Drafts"` | Drafts |
| Spam | `"[Gmail]/Spam"` | Junk |
| Trash | `"[Gmail]/Trash"` | Deleted |
| Starred | `"[Gmail]/Starred"` | Starred |
| Important | `"[Gmail]/Important"` | Auto-flagged |

Use All Mail for full backup — it contains every message including sent.

## Gmail IMAP Limits

- Max simultaneous connections per user: 15
- Max connections per IP: 10
- Rate limit: ~2500 messages per day per user (soft)
- Max UID: variable (increments with each message received)
- Read-only mode (`readonly=True`) does NOT count toward some limits
