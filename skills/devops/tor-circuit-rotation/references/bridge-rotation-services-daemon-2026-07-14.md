# Clean Bridge Rotation — Services Daemon, Cookie-Missing — 2026-07-14

## Scenario

Cookie-missing deadlock with a Services-session (SYSTEM) tor daemon — **not killable
from cron**. The bridge's persistent control connection handled the rotation in a
single `browser_new_identity()` call with no escalation needed. This is the
**preferred outcome** for this deadlock variant: the bridge bypasses the missing
cookie entirely.

Key differences from prior cycles:
- **`sleep 25` was NOT interrupted** (first cycle where this didn't happen)
- **Only 2 stale dirs** (lowest count observed — system has stabilized)
- **`check.torproject.org/api/ip` worked for both pre and post checks** (intermittent reliability confirmed)

## Initial State

| Metric | Value |
|--------|-------|
| Tor Daemon PID | 25976 (Services — not killable) |
| SOCKS5 | ✅ :9250, routing traffic |
| Control Port | ✅ :9251, PROTOCOLINFO responds |
| Auth Cookie | ❌ 0 files on disk (deadlock — COOKIEFILE path from PROTOCOLINFO doesn't exist) |
| Stale Session Dirs | **2** (lowest observed — built-in reaper keeping up) |
| Pre-rotation Exit IP | **204.8.96.105** |
| Non-Tor Reference IP | 74.76.35.96 |
| xul.dll patch | ✅ PATCHED (webdriver:0, WEBDRIVER_BIDI:0) |
| MCP tools available | `mcp_tor_camoufox_bridge_*` (bridge tools) |
| Bridge state | `tor_browser: {status: "configured"}`, `camoufox: {status: "running"}` |
| Tor version | 0.4.9.9 |

## Rotation

| Step | Detail | Result |
|------|--------|--------|
| `bridge_status()` | Active engine: tor | ✅ |
| Pre-IP via SOCKS5 | `check.torproject.org/api/ip` → `204.8.96.105` | ✅ |
| `browser_new_identity()` | NEWNYM dispatched | `"NEWNYM requested for Tor circuit rotation"` |
| Wait | `sleep 25` — **completed normally** (exit 0, no interruption) | ✅ First cycle where sleep worked |
| Post-IP via SOCKS5 | `check.torproject.org/api/ip` → `171.25.193.82` | ✅ |
| IP changed? | **204.8.96.105 → 171.25.193.82** | ✅ Single NEWNYM sufficed |
| Waterfall escalation | None needed — first-try success | ✅ |

**Notable:** Unlike the Jul 12 normal-rotation reference where `check.torproject.org/api/ip`
timed out on post-rotation, this cycle had it working for both checks. The intermittent
reliability pattern persists but the service was available here.

## Post-Rotation Checks

### xul.dll Stealth Patch
```
PATCHED=True (webdriver:0, WEBDRIVER_BIDI:0) ✅
```
All 4 binary patches intact after weeks of continuous operation.

### Cookie & Circuit Inspection
- **0 cookie files found** on disk (confirmed deadlock)
- PROTOCOLINFO reports COOKIEFILE at `torbrowser-driver-6p_kf0ti\tor-data\control_auth_cookie`
  — but file does not exist (32 bytes expected, 0 found)
- Null auth attempt returns: `515 Authentication failed: Wrong length on authentication cookie`
- Cannot inspect circuits via raw socket (no cookie) — but bridge rotation succeeded.
- **Service-specific note:** Many IP-check services block Tor exits:
  - `check.torproject.org/api/ip` — ✅ Works
  - `ipinfo.io/ip` — ❌ 403 (blocks Tor)

### Orphan Processes
| Process | Count | Method |
|---------|-------|--------|
| `firefox.exe` | **0** | `check-ff-windows.ps1` |
| `geckodriver.exe` | **0** | `tasklist /FI` |
| `tor.exe` | **1** (Services, PID 25976) | `tasklist /FI "PID eq 25976"` |

**Consecutive cycle with 0 orphans:** The system has remained stable since the GFX
auto-recovery patches took effect. The 25-83 orphan pattern from earlier cycles has
not recurred for multiple consecutive rotations.

### Daemon Session Type
```
tor.exe,25976,Services,0,"51,636 K"
```
Services session (3rd field). Confirmed **not killable from cron** — consistent
with the cookie-missing deadlock.

### Stale Session Directory Cleanup
| Metric | Value |
|--------|-------|
| **Pre-cleanup count** | 2 `torbrowser-driver-*` directories |
| **Cleaned** | 1 (`torbrowser-driver-kbv6kia3`) |
| **Preserved** | 1 (`torbrowser-driver-6p_kf0ti` — active session) |
| **Cleanup method** | `rm -rf` via bash (targeted) |

**Accumulation trend:** 41 (Jul 12) → 46 (Jul 13) → **2 (Jul 14)**. The steep drop
from 46 to 2 suggests the built-in 24h reaper triggered a bulk cleanup between Jul 13
and Jul 14. Prior high-water marks of 54+ are not recurring. At this rate, stale-dir
accumulation is no longer a concern.

### Sleep Reliability
`sleep 25` completed normally (exit 0) for the first recorded cycle. Prior cycles
(Jul 12, Jul 13) both showed exit code 15 (interrupted sleep). This confirms the
cron sleep interruption is **environment-dependent and intermittent**, not a hard
guarantee. The pitfall's workaround (NEWNYM is fire-and-forget; proceed to verification
even after interrupted sleep) remains valid for both cases.

## Health Summary

```
Bridge Status     → tor: configured, camoufox: running
Circuit Rotation  → 204.8.96.105 → 171.25.193.82 ✅ (single NEWNYM)
Stealth Patch     → webdriver:0, WEBDRIVER_BIDI:0 ✅
SOCKS5            → reachable on :9250 ✅
Orphans           → 0 firefox, 0 geckodriver ✅
Stale Dirs        → 2 → 1 (1 cleaned) ✅
Recovery Actions  → none needed
Cookie State      → missing (Services daemon — not killable, bridge bypass works)
```

## Key Takeaways

1. **Bridge rotation works reliably even in cookie-missing deadlock** — the persistent
   control connection bypasses the missing cookie. Single NEWNYM suffices.
2. **Sleep interruption is intermittent** — this cycle worked normally. Always verify
   exit IP regardless of sleep exit code (the pitfall's guidance is correct: NEWNYM
   is fire-and-forget).
3. **System has stabilized** — 0 orphans, 2 stale dirs, no escalation needed. The
   GFX auto-recovery patches are holding.
4. **`check.torproject.org/api/ip` reliability is intermittent** — worked this cycle
   for both pre and post checks. `api.ipify.org` remains the reliable fallback.
5. **Services daemon = not killable** — but rotation via bridge works without killing.
   The daemon will be replaced naturally on the next clean MCP server restart.
