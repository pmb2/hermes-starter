# Tor Bridge Dead Daemon — Deceptive Acknowledgments (2026-07-25)

## Scenario

`tor_camoufox_bridge` MCP server was loaded and responding to tool calls,
reporting `tor_browser: {status: "configured"}`. However, `tor.exe` was
completely absent — no process, no ports 9250/9251, stale session dir from
3+ days prior. The daemon had died without the bridge detecting it.

## The Trap

Both `browser_navigate(about:blank)` and `browser_new_identity()` returned
success acknowledgments but were **completely non-functional**:

| Tool | Response | Reality |
|------|----------|---------|
| `browser_navigate(about:blank)` | `"Navigating Tor Browser to about:blank"` | Spawned 13 orphan Firefox processes, no tor started |
| `browser_new_identity()` | `"NEWNYM requested for Tor circuit rotation"` | No tor process to receive the signal |
| `bridge_status()` | `{"tor_browser": {"status": "configured"}}` | Stale state — daemon dead since Jul 22 |

## Triangulation (all three must agree)

```bash
MSYS_NO_PATHCONV=1 tasklist.exe /FI "IMAGENAME eq tor.exe" /NH
netstat -ano | grep -E "9250|9251"
powershell.exe -Command "Get-Process tor -ErrorAction SilentlyContinue | Select-Object Id"
```

## Recovery: Manual Tor Start

Killing the MCP server wasn't feasible (cron session). Instead, start tor
manually with the existing torrc:

```bash
terminal(background=true, command='tor -f "${USER_HOME}/AppData/Local/Temp/torbrowser-driver-torrun/torrc"')
```

Wait 12s for bootstrap. Existing auth cookie stays valid.

## Rotation Escalation

Bridge NEWNYM didn't change the exit IP (188.68.49.235). Strong rotation
(close 13 circuits + NEWNYM + 30s wait) via raw socket succeeded:
**188.68.49.235 → 45.84.107.182**. Tor routing confirmed (IsTor: true).

## Key Lesson

Bridge acknowledgment does NOT equal action. Always verify with an OS-level
probe after calling recovery tools. Strong rotation via raw socket is the
reliable escalation when bridge NEWNYM fails.
