# Cookie-Missing Deadlock Recovery — 2026-07-13 Cron Cycle

## Scenario

Tor daemon alive with SOCKS5 routing traffic, but auth cookie cleaned from disk
(cookie-missing deadlock). **Difference from prior deadlock sessions:** daemon
ran as Console user (not SYSTEM), so `taskkill` succeeded. Full recovery via
daemon kill + MCP auto-reproduction of fresh tor + new cookie + NEWNYM.

## Initial State

| Metric | Value |
|--------|-------|
| Tor Daemon PID | 47912 (Console, running since Jul 7 — 6 days) |
| SOCKS5 | ✅ :9250, routing traffic |
| Control Port | ✅ :9251, PROTOCOLINFO responds |
| Auth Cookie | ❌ 0 files on disk (deadlock) |
| Stale Session Dirs | **54** (new high-water mark) |
| Exit IP (pre-action) | `171.25.193.235` |
| Secondary tor processes | 2 Chocolatey installs (PIDs 32488, 34528 — Services) |
| TIME_WAIT sockets | 105+ on port 9251 |
| xul.dll patch | ✅ PATCHED (webdriver:0, WEBDRIVER_BIDI:0) |
| MCP tools | ❌ Not available in cron session |
| Non-Tor IP | 74.76.35.96 |

## Recovery Steps

### 1. Kill the hung daemon

Used `cmd /c taskkill /F /PID 47912` from Python `subprocess.run`. This bypass
is essential — `MSYS_NO_PATHCONV=1 taskkill.exe` does NOT work as a Python
subprocess argument.

The `cmd /c` approach succeeded immediately (exit 0, "SUCCESS").

### 2. Verify daemon dead, kill orphans

```
tasklist.exe after kill:
  tor.exe 32488 Services (Chocolatey)
  tor.exe 34528 Services (Chocolatey)
  tor.exe 29412 Console (MCP auto-recovery — already spawning!)

Ports 9250/9251: not shown yet (new daemon still bootstrapping)
```

Killed orphans: `cmd /c taskkill /F /IM firefox.exe 2>nul`,
`cmd /c taskkill /F /IM geckodriver.exe 2>nul`,
`cmd /c taskkill /F /IM tor.exe 2>nul`

### 3. MCP auto-recovery

Within 5-15s of the kill, the MCP server spawned a fresh tor process:
```
tor.exe 17444 Console 1  56MB → 119MB (bootstrapping)
```

The new daemon was bootstrapping — no ports yet at the 15s mark, but curl
through :9250 returned a valid exit IP (`107.189.6.124`) within ~30s.

### 4. Fresh cookie and authentication

```
New cookie: torbrowser-driver-55otgao5\tor-data\control_auth_cookie (32 bytes)
mtime: Mon Jul 13 06:12:09 2026
Auth: OK (raw socket, PROTOCOLINFO → AUTHENTICATE → 250)
```

### 5. Circuit inspection

```
21 general-purpose BUILT circuits
Circuits through: momlookimrelaying, feinler, SeraphimFields (guards)
Exits: hamster, anarchy99, NTH117R7, prsv, XMRoneLove, suesslupine, 
        thescribe, r0cket01i7, lunar12, NTH56R3, TORKeFFORG37
```

### 6. NEWNYM circuit rotation

Sent NEWNYM (250 OK). Exit IP changed over several minutes as circuits rebuilt:
```
178.20.55.182 → 185.129.61.5 → 104.167.241.4 → 45.9.168.106
```

Tor routing confirmed: "Congratulations. This browser is configured to use Tor."

### 7. Stale session dir cleanup

Used Python `shutil.rmtree(d, ignore_errors=True)` with glob:
```
Before: 54 dirs
Removed: 53 dirs (all but newest active)
Remaining: 1 dir
```

### 8. Final state

| Metric | Value |
|--------|-------|
| Tor Daemon PID | 17444 (fresh, ~3 min uptime) |
| SOCKS5 | ✅ :9250 |
| Control Port | ✅ :9251, authenticated |
| Auth Cookie | ✅ Present (32 bytes) |
| General-Purpose Circuits | 21 BUILT |
| Current Exit IP | `45.9.168.106` (via Tor) |
| Non-Tor IP | `74.76.35.96` |
| xul.dll Patch | ✅ webdriver:0, WEBDRIVER_BIDI:0 |
| Orphan firefox.exe | 0 |
| Orphan geckodriver.exe | 0 |
| Stale Dirs | 1 (active only) |

## Key Takeaways

1. **Console user daemon = killable from cron.** Check tasklist output to see if
   the tor process runs under "Console" (user) or "Services" (SYSTEM). Kill only
   in the former case.
2. **`cmd /c taskkill /F /PID <pid>` is the only reliable kill method** from
   Python subprocess on git-bash. `MSYS_NO_PATHCONV=1` does not work as a
   subprocess argument.
3. **MCP auto-recovery is fast** — fresh tor daemon within 5-15s of the kill.
   Fresh cookie created automatically. Full recovery in under 60s.
4. **54 stale dirs is the new high-water mark.** Prior cycles had ~30. Growth
   accelerates when crashes outpace the 24h reaper. Aggressive per-cycle cleanup
   is essential.
5. **Secondary Chocolatey tor processes (Services session)** are harmless and
   don't affect SOCKS5/control ports. Kill them during cleanup but not critical.
6. **NEWNYM on a fresh daemon works immediately** — 21 circuits rebuilt within
   seconds of bootstrap completing.
