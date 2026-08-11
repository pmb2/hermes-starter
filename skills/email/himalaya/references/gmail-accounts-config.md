# Configured Gmail Accounts

Both accounts configured in `~/.config/himalaya/config.toml`.

## Account: youraccount (DEFAULT)

| Field | Value |
|-------|-------|
| Email | <your-email>@gmail.com |
| Display Name | the operator |
| Default | Yes |
| IMAP | imap.gmail.com:993 (TLS) |
| SMTP | smtp.gmail.com:587 (STARTTLS) |
| App password | `${GMAIL_APP_PASSWORD}` (via python -c inline cmd) |
| Quota | OK |

## Account: youraccount2

| Field | Value |
|-------|-------|
| Email | <your-email>@gmail.com |
| Display Name | the operator |
| Default | No |
| IMAP | imap.gmail.com:993 (TLS) |
| SMTP | smtp.gmail.com:587 (STARTTLS) |
| App password | `ufwdgehdyolxlbkm` (via python -c inline cmd) |
| Quota | OVER 15GB — IMAP reads still work, but send/receive impacted |

## Usage

Default account (backusagency) — just run himalaya commands directly:
```bash
himalaya envelope list
himalaya message read 42
```

Secondary account (youraccount2):
```bash
# Envelope list works with -a
himalaya envelope list -a youraccount2

# Message read does NOT work with -a on Windows (known bug)
# Workaround: use Python IMAP directly (see Windows-Specific Quirks in SKILL.md)
```

## App Password Notes

Both use Gmail App Passwords (generated at myaccount.google.com/security). The
app password is stored in the Himalaya config via `backend.auth.cmd` using a
`python -c` inline command so it never appears in plaintext in shell history.
