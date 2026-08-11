# Profile Sync Cron Job — Main → Automation Profile

**Cron job ID:** `28d080a625fd`  
**Script:** `scripts/profile-sync.py` (at `~/AppData/Local/hermes/scripts/profile-sync.py`)  
**Schedule:** Every 120m (2 hours)  
**Delivery:** `local` (no user notification)  
**Created:** 2026-05-30

## Purpose

Keeps the headless automation profile (`firefox-profile`) in sync with the operator's main browsing profile (`<profile-id>.default-release-1`) by periodically copying user data files when Firefox is not running.

## What It Copies

| File | Purpose | Critical? |
|------|---------|-----------|
| `cookies.sqlite` | Session tokens (ChatGPT, Grok, YouTube) | ✅ Yes |
| `logins.json` | Saved usernames/passwords | No |
| `key4.db` | Encryption keys for saved passwords | No |
| `places.sqlite` | Bookmarks + browsing history | No |
| `favicons.sqlite` | Site favicons | No |
| `signedInUser.json` | Firefox Account / Sync session | No |
| `containers.json` | Multi-account container config | No |

## Safety

The sync script **only runs when Firefox is NOT running**. It checks with `tasklist /FI "IMAGENAME eq firefox.exe"` and skips if any Firefox process is active. This prevents corruption of `cookies.sqlite` from concurrent writes.

If Firefox is running, the script logs `SKIP: Firefox is running — delaying sync` and exits cleanly (exit code 0).

## Integration Points

| Trigger | When | Method |
|---------|------|--------|
| Cron job | Every 2h | `scripts/profile-sync.py` (no_agent=true, deliver=local) |
| PIM pre-ingestion | Every 3h (before headless launch) | Inline in `ingest-chatgpt-grok.sh` |

The PIM script syncs BEFORE launching the headless Firefox because once headless Firefox starts on port 9239, the sync script sees it and skips (headless Firefox shows as `firefox.exe` in tasklist).

## Setup

```bash
cronjob action=create \
  name="Profile Sync — main→auto (every 2h)" \
  schedule="every 120m" \
  script="scripts/profile-sync.py" \
  no_agent=true \
  deliver=local
```

## Log

Log file at `~/AppData/Local/hermes/profile-sync.log`:
```
2026-05-30 17:20:53 [INFO] ==================================================
2026-05-30 17:20:53 [INFO] Profile Sync: MAIN -> AUTO
2026-05-30 17:20:53 [INFO] ==================================================
2026-05-30 17:20:53 [INFO] SKIP: Firefox is running — delaying sync
```
