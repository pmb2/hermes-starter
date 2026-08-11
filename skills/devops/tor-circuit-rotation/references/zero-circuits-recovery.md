# Zero Circuits + No Cookie on Disk — Recovery (2026-07-09)

## Scenario
Cron job triggered with `mcp_tor_camoufox_bridge_*` tools present (not `mcp_tor_browser_mcp_*`).
Tor daemon was LISTENING on ports 9250/9251 but had **0 general-purpose BUILT circuits** —
a degraded-but-alive state distinct from the hung daemon variants documented in
`hung-daemon-recovery.md`.

## Diagnostic Signs Observed
1. `bridge_status()` → tor status "configured" (daemon running, no browser launched)
2. `curl --socks5-hostname 127.0.0.1:9250` to `check.torproject.org/api/ip` timed out
3. Non-Tor `curl -s https://api.ipify.org` succeeded (74.76.35.96) → problem was tor-specific
4. `netstat -ano | grep -E "9250|9251"` showed both ports LISTENING on PID 47912, with
   **130+ TIME_WAIT sockets** on port 9251 (far more than the 10-20+ from the
   CLOSE_WAIT accumulation pitfall — this was the TIME_WAIT variant)
5. Raw socket `PROTOCOLINFO` on port 9251 succeeded immediately (250 response)
6. **Key finding**: PROTOCOLINFO returned `COOKIEFILE="C:\...\torbrowser-driver-ge5q_d86\tor-data\control_auth_cookie"`
   but the file did NOT exist on disk. The directory (`tor-data`) contained only a stale
   `lock` file from July 7. All other torbrowser-driver temp dirs also had no cookie files.

## Root Cause
The tor daemon (PID 47912) was using a stale session directory whose auth cookie had been
cleaned from disk. The daemon itself was alive and processing control commands, but had
**0 general-purpose BUILT circuits** (only ONEHOP_TUNNEL internal circuits would have
existed if any). The 130+ TIME_WAIT sockets accumulated from repeated failed stem/raw
socket connections in prior cron cycles.

This is **not a hung daemon** — the control port was responsive. It is a **degraded state**
where:
- The bridge MCP server holds a persistent control connection internally
- New control connections authenticate via cookie, but cookie file is gone
- SOCKS proxy accepts connections but has no exit circuits → curl timeouts
- The daemon is alive and can receive NEWNYM signals from the bridge's internal connection

## Key Difference From Hung Daemon Variants
| State | Control Port | Cookie File | Exit Circuits | Fix |
|-------|-------------|-------------|---------------|-----|
| Healthy | PROTOCOLINFO + AUTH succeed | On disk | 5+ BUILT | None needed |
| Degraded (this variant) | PROTOCOLINFO succeeds | 0 bytes / missing | 0 BUILT | NEWNYM via bridge → 25s wait |
| Hung (Session 1) | PROTOCOLINFO times out | Exists but stale | 0 | Kill daemon → auto-recovery |
| Hung (Session 2) | Connection refused | Stale | 0 | Kill daemon → auto-recovery |

## Recovery Steps Executed

### Step 1: Confirm control port is responsive (not hung)
```
PROTOCOLINFO → 250 response → Tor 0.4.9.9, AUTH METHODS=COOKIE
```
Run `PROTOCOLINFO` via raw socket. If it responds with a 250 line, the daemon is alive.
This is the **key diagnostic** that distinguishes degraded-from-hung.

### Step 2: Send NEWNYM via bridge (bypasses missing cookie)
The `browser_new_identity()` bridge tool works because the MCP server holds its own
persistent control connection. The missing cookie on disk is irrelevant to the bridge's
internal connection.

**Result:** `"NEWNYM requested for Tor circuit rotation"`

### Step 3: Wait 25s for circuit rebuild
Single NEWNYM with 25s wait was sufficient. No strong rotation (close circuits)
was needed — circuits rebuilt automatically from the NEWNYM signal.

### Step 4: Verify exit IP
```
curl --socks5-hostname 127.0.0.1:9250 -s https://check.torproject.org/api/ip
→ {"IsTor":true,"IP":"185.220.101.34"}
```
Tor routing confirmed. Exit IP changed from "unavailable" to 185.220.101.34.

### Step 5: Verify xul.dll patch (browser-independent)
```
xul.dll: PATCHED=True (webdriver:0, WEBDRIVER_BIDI:0) ✓
```

### Step 6: Clean orphans
25 orphan firefox.exe processes were killed (accumulated from prior GFX crash cycles).
No geckodriver.exe orphans found.

### Key Timings
- PROTOCOLINFO → bridge NEWNYM: **immediate** (< 1s)
- NEWNYM → exit IP verifiable: **25s**
- Total recovery + rotation: **~35s**
- No daemon kill needed — full recovery via single bridge NEWNYM

## What To Do When You See This Pattern

1. **Do NOT kill the tor daemon.** The control port is responsive; the daemon is alive.
2. **Skip raw socket circuit inspection** if no cookie file exists — you can't authenticate.
3. **Call `browser_new_identity()`** via the bridge. This works without the cookie file.
4. **Wait 25-30s**, then verify exit IP via `check.torproject.org/api/ip` through SOCKS5.
5. If the exit IP still doesn't respond after 30s, escalate to the **strong rotation**
   waterfall (close circuits + NEWNYM), or if the control port goes unresponsive,
   treat as hung daemon and kill+recover.
6. Clean orphans and verify xul.dll patch per the standard post-rotation checklist.
