# Cookie-Missing Deadlock: Tor Daemon Alive but Uncontrollable

## Scenario

The tor daemon is healthy (SOCKS5 routes traffic, control port responds to
PROTOCOLINFO) but the auth cookie file has been cleaned from disk. With no
MCP server loaded (cron session), control port authentication is impossible.
In some cases the cron session cannot kill the tor daemon either (ACCESS_DENIED
— the MCP server started it with higher privileges).

## History

- **2026-07-09 12:20 UTC** — Initial discovery during cron rotation cycle.
  Daemon running as SYSTEM (Services session), all kill attempts denied.
- **2026-07-13 06:12 UTC** — Daemon running as Console (user-level session,
  PID 47912, uptime 6 days). Kill succeeded via `cmd /c taskkill /F /PID <pid>`,
  triggering MCP auto-recovery with fresh cookie. Proved the deadlock has an
  escape hatch when the daemon runs as the current user.

## Diagnostic Signs

| Signal | What you see |
|--------|-------------|
| `netstat -ano` | Ports 9250/9251 LISTENING, tor PID visible |
| `curl --socks5-hostname :9250` | ✅ Returns Tor-routed IP (api.ipify.org works; check.torproject.org/api/ip may return `IsTor:true`) |
| PROTOCOLINFO on :9251 | ✅ Responds with version, cookie path, auth methods |
| Cookie file at reported path | ❌ File not found (reported path exists, cookie cleaned) |
| Cookie dir contents | ❌ Only a `lock` file (0 bytes) — no cookie at all. Lock date reveals when daemon _started_ (contrast with current date to estimate uptime) |
| AUTHENTICATE with cookie | ❌ "UnreadableCookieFile" / file not found |
| AUTHENTICATE with empty hex | ❌ `515 Authentication failed: Wrong length on authentication cookie` |
| AUTHCHALLENGE SAFECOOKIE | ❌ Two observed failure modes:<br>1. `512 Wrong number of arguments` (common — needs cookie to hash)<br>2. `ConnectionAbortedError: [WinError 10053]` (less common — connection aborted mid-handshake when the daemon rejects the challenge) |
| stem Controller.authenticate() | ❌ "file doesn't exist" |
| `taskkill /F /PID <pid>` | ⚠️ Daemon-dependent: Console user ✅ may succeed; Services/SYSTEM ❌ ACCESS_DENIED |
| MCP tools in session | ❌ Neither tor-browser-mcp nor tor_camoufox_bridge loaded |

## The Deadlock

1. Can't authenticate → can't send explicit NEWNYM or inspect circuits
2. Can't kill daemon (if SYSTEM/Services) → can't start a fresh controllable instance
3. No MCP tools → can't use bridge's persistent auth connection
4. SOCKS5 still works → daemon is healthy, just not controllable from cron

## What Works

- **Exit IP check**: `curl --socks5-hostname 127.0.0.1:9250 -s https://api.ipify.org`
- **Non-Tor IP check**: `curl -s https://api.ipify.org`
- **xul.dll patch check**: Binary read (no browser or auth needed)
- **Orphan check**: PowerShell for accuracy (MSYS reports phantoms)
- **Exit IPs may still rotate naturally** — In a Jul 2026 deadlock session, the
  exit IP changed multiple times without any explicit NEWNYM:
  - **Jul 9 session**: 185.220.101.35 → 109.70.100.2 → 203.55.81.2 over ~15 min
  - **Jul 10 session**: 203.55.81.1 → 171.25.193.82 between two sequential checks
    (~2 min apart, different SOCKS5 connections took different circuits)
  The MCP server's persistent authenticated control connection was independently
  rotating circuits even though the cron session couldn't authenticate. The
  deadlocked daemon is not frozen — circuits refresh as tor's internal guard
  rotation algorithms run and new SOCKS5 connections may be routed through
  different exits.

## Resolution Path (in priority order)

### Option 1: Daemon Kill + MCP Auto-Recovery (if daemon runs as Console user)

**Check daemon session type first:**
```
tasklist.exe /FI "IMAGENAME eq tor.exe" /NH /FO LIST
```
If the daemon's session shows "Console" (not "Services"), kill will likely
succeed. If "Services" (SYSTEM), skip to Option 2.

**How to kill reliably from cron (Python subprocess):**
```python
import subprocess
kill = subprocess.run(
    ['cmd', '/c', 'taskkill /F /PID <pid>'],
    capture_output=True, text=True, timeout=15
)
```

**The `cmd /c` bypass is essential** — `MSYS_NO_PATHCONV=1 taskkill.exe` does
NOT work from Python `subprocess.run` because the environment variable prefix
gets passed as a single argument to the executable name, not as an env var.
`cmd /c` avoids MSYS path translation entirely and is the most reliable way
to call taskkill from Python on git-bash.

**After kill succeeds:**
1. MCP auto-recovery spawns a fresh tor daemon within 5-15s
2. The new daemon creates a fresh auth cookie — it WILL be on disk
3. Authenticate via raw socket or stem, then send NEWNYM
4. Clean stale session dirs (all but newest active one)
5. Verify exit IP changed

**2026-07-13 confirmation:** Daemon PID 47912 (Console, running 6 days, 54 stale
dirs accumulated) killed successfully. MCP auto-recovery spawned PID 17444 within
seconds. Fresh cookie created. Exit IP changed from 171.25.193.235 →
107.189.6.124 (fresh daemon) → 45.9.168.106 (after NEWNYM). 0 orphan processes.
53/54 stale dirs cleaned. Full recovery in under 60s.

### Option 2: Wait for next interactive session (when ACCESS_DENIED)

If `taskkill` returns "Access is denied" (daemon running as SYSTEM/Services),
the cron session cannot kill it. The MCP server (when loaded in an interactive
session) holds a persistent authenticated control connection. It can rotate
circuits and verify stealth even without the on-disk cookie. The cron session
should report the state and defer rotation.

**Which session type to check first:** Console (user-level) is increasingly
common since Hermes MCP servers run under the user's profile. Always try the
kill first (with `cmd /c`) before assuming ACCESS_DENIED.

### Option 3: Restart Hermes profile

Triggers MCP server restart, which kills the old tor daemon and starts a
fresh one with a new cookie. Heavy-handed but guaranteed to work.

### Option 4: Manual kill from elevated shell

If an Admin PowerShell/cmd is available, `taskkill /F /PID <pid>` works.
The cron session's user account may simply lack the right privilege.

## Prevention

- The cookie is cleaned by Windows temp file reaper when the temp dir's
  `torbrowser-driver-*` directory is scanned. The reaper targets files older
  than a threshold (typically 24h for Windows temp cleanup). The session dir
  itself persists but the cookie inside gets cleaned.
- Not directly preventable — this is a Windows temp management behavior.
- The MCP server's persistent connection survives this because it authenticates
  once at startup and never re-reads the cookie file.
- Mitigation: clean stale session dirs aggressively (every cron cycle). Fewer
  stale dirs = reaper has less surface area to scan.
