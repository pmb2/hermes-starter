# Firefox Cookie Import — Technical Reference

## Why Cookie Import Is Needed

Camoufox (the stealth browser engine) is a Firefox fork with its own
profile directory at `~/.camofox/profiles/`. It starts fresh with no
logged-in sessions. Importing Firefox cookies gives the stealth browser
all the same accounts without logging in again.

## Cookie Storage

Firefox stores cookies in SQLite at:
```
~/AppData/Roaming/Mozilla/Firefox/Profiles/<profile>/cookies.sqlite
```

Cookies are stored in **plain text** (not encrypted). Only saved passwords
(logins.json) and credit cards are encrypted.

## Cookie Format

| Column | Type | Notes |
|--------|------|-------|
| name | TEXT | Cookie name |
| value | TEXT | Cookie value (unencrypted) |
| host | TEXT | Domain, may be prefixed with `.` |
| path | TEXT | URL path |
| expiry | INTEGER | **Milliseconds** since epoch |
| isSecure | INTEGER | 0/1 |
| isHttpOnly | INTEGER | 0/1 |
| sameSite | INTEGER | 0=Strict, 1=Lax, 2=None |

**IMPORTANT**: Firefox stores expiry in **milliseconds**, but Camofox
expects **seconds** (Unix timestamp). Divide by 1000 when importing.

## Camofox Cookie Import Endpoint

```
POST /sessions/{userId}/cookies
Content-Type: application/json

{
  "cookies": [
    {
      "name": "...",
      "value": "...",
      "domain": "example.com",
      "path": "/",
      "expires": 1814631932,     # Unix timestamp in SECONDS
      "httpOnly": true,
      "secure": true,
      "sameSite": "Lax"
    }
  ]
}
```

Limits:
- Max 100 cookies per request (413 if more)
- Expiry must be -1 (session) or positive Unix timestamp (seconds)
- Session cookies (Firefox expiry=0) → convert to -1

## Auto-Refresh Cron

```
cronjob action=create name=refresh-firefox-cookies schedule="every 6h" \
  script=import-firefox-cookies.py no_agent=true deliver=local
```

Runs every 6 hours to re-import cookies from Firefox into Camoufox.
This keeps sessions fresh as cookies expire.

## Verification

```python
# Create tab to Google.com - if "Sign out" or profile pic visible, 
# cookies are working
POST /tabs {"userId": "the operator", "url": "https://google.com"}
GET /tabs/{tabId}/snapshot?userId=the operator
# Look for "sign out" or account indicators in snapshot text
```
