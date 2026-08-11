# Multi-Profile Strategy for the operator's Firefox

## Profile Inventory

All profiles from `${USER_HOME}/AppData/Roaming/Mozilla/Firefox/profiles.ini`:

| # | Name | Path | Type | Default? | Notes |
|---|------|------|------|----------|-------|
| 1 | `default-release-1` | `Profiles/<profile-id>.default-release-1` | **NORMAL** | No (StoreID=14699cee) | the operator's MAIN profile. Saved passwords, bookmarks, ChatGPT/Grok sessions. |
| 2 | `default` | `Profiles/bljvedlk.default` | Legacy | **YES** (Default=1) | Old Firefox install default. Clean user.js (performance tweaks only). |
| 3 | `default-release` | `Profiles/5knm22qr.default-release-1744298751041` | NEW install default | YES for InstallE7CF176E110C211B | Newer Firefox install. Performance tweaks only. |
| 4 | `cdp-automation` | `Profiles/74g0w42k.cdp-automation` | AUTOMATION | No | Created for CDP-based automation experiments. No user.js. |
| 5 | `DebugProfile` | `Profiles/cyesaul1.DebugProfile` | DEBUG | No | Firefox debug tests. |
| 6 | `hermes-mcp` | `${USER_HOME}\AppData\Local\hermes\firefox-profile` | **AUTOMATION** | No (IsRelative=0) | The MCP automation profile. Has full stealth + remote debugging prefs in user.js. |

## Which Profile Firefox Uses on Launch

Firefox determines the active profile via:

```
profiles.ini:
  [General]
  StartWithLastProfile=1
```

With `StartWithLastProfile=1`, Firefox opens the LAST profile that was used in that session, NOT the one marked `Default=1`.

- If the operator last used `<profile-id>.default-release-1`, that's what opens next
- The `Default=1` flag on `bljvedlk.default` only matters if `StartWithLastProfile=0` or the last profile was deleted

## Automation Strategy

### Two-profile separation

| Profile | User behavior | Has remote debugging? | Prefs |
|---------|---------------|----------------------|-------|
| `<profile-id>.default-release-1` | the operator's normal browsing | NO | stealth-only (marionette, webdriver overrides, signon forced) |
| `hermes-mcp` | MCP server connects here | YES | full automation (remote.active-protocols=1, devtools.debugger.*) |

### Automation firefox must stay running

The `hermes-mcp` profile has remote debugging enabled. It's launched by the ultimate-firefox-mcp server. This Firefox should:

1. Be started at boot (via Task Scheduler or startup script)
2. Have ChatGPT and Grok logged in ONCE
3. Stay running in the background (minimized to tray)
4. The PIM cron job connects to it periodically to scrape new conversations

### Profile contamination risk

If a normal-browsing profile (like `<profile-id>`) is EVER started with `--remote-debugging-port`, Firefox writes automation prefs into its `prefs.js`:
- `remote.active-protocols = 1` (or appropriate value)
- `devtools.debugger.remote-enabled = true`
- `devtools.debugger.remote-port = 922X`

These persist across restarts and cause robot detection + password manager failure even when Firefox is opened normally.

**Fix**: Edit `prefs.js` directly, or use the stealth patcher:
```bash
python firefox-stealth-patcher.py --profile "C:\Path\To\Profile"
```
