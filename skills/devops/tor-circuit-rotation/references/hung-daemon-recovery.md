# Hung Tor Daemon Recovery — Session Capture (2026-06-22)

## Scenario — Session 1 (PROTOCOLINFO timeout variant)
Cron job triggered with `mcp_tor_camoufox_bridge_*` tools available (not `mcp_tor_browser_mcp_*`).
Tor daemon was LISTENING on ports 9250/9251 but completely unresponsive.

Full Session 1 details are documented in the main SKILL.md **Hung Daemon Detection and Recovery**
pitfall section (diagnostic signs, recovery procedure, timings, and commands reference).

---

## Scenario — Session 2 (Connection Refused variant)

A second hung-daemon recovery on the same date (different cron cycle) revealed a
DIFFERENT flavor of hang: the control port actively refused new TCP connections
rather than accepting and then timing out on PROTOCOLINFO.

### Diagnostic Signs Observed
1. `curl --socks5-hostname 127.0.0.1:9250 -s https://check.torproject.org/api/ip` timed out
2. `curl --socks5-hostname 127.0.0.1:9250 -s https://api.ipify.org` also timed out
3. Non-Tor `curl -s https://api.ipify.org` succeeded (74.76.35.96) → problem was tor-specific
4. `netstat -ano | grep -E "9250|9251"` showed LISTENING on PID 2796, plus
   CLOSE_WAIT sockets and an ESTABLISHED connection from PID 80088 (the bridge MCP server)
5. **Key difference**: Raw socket `s.connect(('127.0.0.1', 9251))` RAISED `WinError 10061:
   No connection could be made because the target machine actively refused it` — NOT a
   timeout on PROTOCOLINFO as in Session 1. The control port socket was in a zombie state.
6. `msys kill -0 2796` said "No such process" (FALSE NEGATIVE — see MSYS PID trap below)
7. `powershell Get-Process -Id 2796` confirmed tor.exe was alive (started 06:27:56)

### Root Cause
The tor daemon (PID 2796) was still alive but its control port had a single established
connection from the bridge MCP server (PID 80088). The daemon refused to accept any
ADDITIONAL control connections — unlike Session 1 where the daemon accepted connections
but dropped protocol commands. This appears to happen when tor's control connection
accept queue fills up or the daemon enters a resource-starved state.

### Recovery Steps Executed

#### Step 1: Confirm alive via PowerShell (bypass MSYS PID lie)
```
powershell.exe -Command "Get-Process -Id 2796 | Select-Object Id, ProcessName, StartTime"
```
Confirmed tor.exe alive since 06:27:56. Also found secondary tor.exe (PID 14340, 06:15:04).

#### Step 2: Kill the hung tor daemon
```
MSYS_NO_PATHCONV=1 taskkill.exe /F /PID 2796
```
Result: SUCCESS.

#### Step 3: Wait for bridge auto-recovery
After killing tor, the bridge MCP server (Python PID 80088) detected the broken control
connection and spawned a fresh tor daemon. Checked every 10 seconds:
```
$ for i in 1..6; do sleep 10; netstat -ano | grep -E "925[0-1]"; done
```
**Fresh daemon appeared within 10 seconds** (faster than Session 1's ~20s):
- PID 51736 (WINPID from `ps -W` = 51736)
- Started 12:12:42 (immediately after kill)
- Both ports 9250/9251 LISTENING, zero CLOSE_WAIT sockets

#### Step 4: Authenticate with fresh cookie
6 stale cookie dirs existed. The newest cookie dir (37s old, `torbrowser-driver-2g1hcjfb`)
matched the fresh daemon:
```
Found 6 cookie dirs
  torbrowser-driver-2g1hcjfb (37s old) ← correct
  torbrowser-driver-cvxqt9ds (20723s old) ← stale
  ...
```
Authentication succeeded immediately (Tor 0.4.9.9, uptime 36s).

#### Step 5: Circuit state at 36s uptime
14 BUILT circuits:
- 2 internal (ONEHOP_TUNNEL)
- 12 general-purpose 3-hop circuits
- Entries: `uglygod`, `mullbinde7`
- Exits: `breitwegerich`, `NTH59R8`, `ForPrivacyNET`
- Also 1 HS_VANGUARDS circuit

Exit IP: **185.220.100.252** (confirmed via `check.torproject.org/api/ip`).

#### Step 6: Strong rotation
Closed 18 multi-hop circuits + NEWNYM + 30s wait:
- Before: 15 multi-hop circuits
- After: 12 multi-hop circuits
- Exit IP: 185.220.100.252 → **192.42.116.64** ✅
- Tor routing confirmed: IsTor=true on both

#### Step 7: Orphan cleanup with WINPID awareness
Discovered that `ps -W` output has 5+ columns; the WINPID (4th column) is what netstat
and taskkill use, NOT the MSYS PID (1st column). Killed 18 orphan Tor Browser
firefox.exe processes and 1 geckodriver.exe. Left user's regular Firefox and
firefox-portable untouched.

Stale session dirs: 5 of 9 removed successfully via `rm -rf`; 4 resisted deletion
(git-bash permission errors). The built-in 24h reaper handles the rest.

### Key Timings
- tor kill → fresh daemon listening: **~10s** (vs ~20s in Session 1)
- fresh daemon → exit IP verifiable: **~36s** (first circuit check)
- Strong rotation (close + NEWNYM + verify): **~60s** total
- Total recovery + rotation: **~90s**

### Unique To This Variant
- **Connection Refused** (WinError 10061) is the diagnostic sign, not PROTOCOLINFO timeout.
- The hung daemon was PARTIALLY alive (SOCKS and control sockets exist, but only the
  already-established MCP connection works; new connections are refused).
- `kill -0` gives FALSE "No such process" for WINPIDs in MSYS — always use
  `powershell Get-Process` for reliable Windows PID checking.
- The bridge MCP server respawned tor faster (~10s vs ~20s) in this cycle.
- The fresh daemon had already built exit-capable 3-hop circuits within 36s of startup,
  even before a NEWNYM — tor maintained some circuit state across the restart.
