# Tor Daemon Binary Missing — 2026-07-24 Cron Cycle

## Summary

The tor_camoufox_bridge MCP server reported `tor_browser: {status: "configured"}`
but `tor.exe` was completely absent from disk. The `TorBrowser\Tor\` directory
(containing `tor.exe`, `tor-gencert.exe`, `geoip`, `geoip6`) had been deleted,
while `TorBrowser\Browser\` (with `xul.dll`, `firefox.exe`) remained intact.

This is a **stale MCP "configured" state** — the bridge's parent Python process
was alive, but the managed subprocess it reported existed had no binary to launch.

## Full Diagnostic Record

| Check | Finding |
|---|---|
| `bridge_status()` | `tor_browser: {status: "configured"}` |
| `netstat -ano \| grep -E "9250\|9251"` | Empty (exit 1) |
| `tasklist.exe /FI "IMAGENAME eq tor.exe"` | "No tasks running" |
| `${USER_HOME}\TorBrowser\Tor\` | **Directory does not exist** |
| `${USER_HOME}\TorBrowser\Browser\xul.dll` | ✅ Exists (162MB, Jun 21, patched) |
| xul.dll binary check | `PATCHED=True (webdriver:0, WEBDRIVER_BIDI:0)` |
| `Tor Browser.lnk` target | `${USER_HOME}\TorBrowser\Browser\firefox.exe` |
| curl SOCKS5 (:9250) | `curl: (7) Failed to connect` |
| Non-Tor reference IP | `74.76.35.96` |
| Firefox orphans | 0 |
| Geckodriver orphans | 0 |
| Stale temp session dirs | 1 (lock-only) |

## Recovery Attempts Made (all failed)

1. `browser_navigate(about:blank)` — dispatched but no tor spawned. Bridge's
   `last_tor_result` showed `{status: "dispatched"}`.
2. `browser_new_identity()` — returned "NEWNYM requested" but no tor.exe appeared.
3. Wait 20s+ — bridge never auto-recovered.

**Why auto-recovery didn't fire:** The bridge's broken-control-connection detection
listens for a socket disconnection from the tor daemon's control port. When no
tor.exe exists, no connection was ever established (or the socket was never opened
in the current session), so the detection never triggers. The bridge sits in a
permanent stale "configured" state.

## OS-Level Process Probe Commands Used

```bash
netstat -ano | grep -E "9250|9251"
MSYS_NO_PATHCONV=1 tasklist.exe /FI "IMAGENAME eq tor.exe" /NH /FO CSV
MSYS_NO_PATHCONV=1 tasklist.exe /FI "IMAGENAME eq python.exe" /FO CSV
ls -la ${USER_HOME}/TorBrowser/Tor/  # directory missing entirely
```

## Root Cause Identification

The `TorBrowser\Tor\` directory deletion removed the daemon binary. The portable
Tor Browser layout requires:

```
${USER_HOME}\TorBrowser\
  ├── Browser\           # firefox.exe, xul.dll, omni.ja, etc.
  │   └── firefox.exe
  └── Tor\               # tor.exe, tor-gencert.exe, geoip*, torrc
      └── tor.exe
```

The `Tor Browser.lnk` shortcut only references `Browser\firefox.exe`, so it
opened correctly. But the MCP server resolves `Tor\tor.exe` relative to the
browser directory and found nothing. No alternative tor.exe existed anywhere
on the system (searched C:\, D:\, E:\).

## Required Recovery

Reinstall Tor Browser or restore `${USER_HOME}\TorBrowser\Tor\` including:
- `tor.exe`
- `tor-gencert.exe`
- `geoip` and `geoip6`
- Default `torrc`

After restoration, verify:
- Ports 9250/9251 LISTENING
- `tasklist` shows tor.exe running
- xul.dll patch still intact (`PATCHED=True`)
- Bridge MCP auto-recovery triggers on next Hermes restart
