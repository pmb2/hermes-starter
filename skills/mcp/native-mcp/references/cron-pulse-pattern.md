# Cron-Based MCP Pulse Check Pattern

A reusable pattern for periodic MCP fleet health checks run as Hermes cron jobs.
Suitable for daily or twice-daily automation that validates server health, DB
freshness, and version drift across a multi-server MCP installation.

## Pulse Check Template Structure

Every pulse follows this sequence:

```
1. Quiet-hours gate: Check TZ='America/New_York' date +%H
   → 00-06: output [SILENT] and exit
   → 07+: proceed with full audit
2. Fleet health sweep: All servers, all layers (see mcp-fleet-health-audit.md)
3. Data freshness sweep: DB files, modification times, size trends
4. Version bump detection: Compare against last-known versions from memory
5. One meaningful investigation: A specific probe, test, or repair action
6. Append findings to PULSE.md or equivalent tracking file
7. Append digest to daily log (if configured)
8. Deliver formatted report (discord-report-format)
```

## Key Techniques

### Two-Phase Health Check

Phase 1 (fast, parallel batch): Check all servers at once for basic liveness.

```bash
# Docker containers — single command covers many servers
docker ps --format '{{.Names}}\t{{.Status}}'

# Process-based servers (bare binaries)
ps aux | grep -i brainmd

# HTTP servers — quick port check
curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 http://localhost:3000/
```

Phase 2 (targeted): For each server flagged in Phase 1, run detailed diagnostics.
Typically only 1-2 servers need deep inspection per pulse.

### Cross-Pulse Trend Tracking

Track metrics that change slowly across pulses:

- **DB file sizes** — growth (or lack) indicates ingestion activity
- **Modification timestamps** — active vs stale (24h+ without change = investigate)
- **PID continuity** — same PID across pulses = server survived; new PID = crash/restart
- **Version strings** — unexpected bumps may indicate auto-updates or config drift

### The "Locked DB" Positive Signal

When `sqlite3 /path/to/db` fails with "unable to open database file", the MCP
server process likely holds an exclusive lock. This confirms the server is
**alive and serving** — paradoxical but useful.

Verify with process check:
```bash
# Find the process holding the lock
# On Linux: lsof /path/to/db
# On Windows/MSYS: handle.exe or check running MCP servers via tasklist
```

### Wearable Investigation (The "One Thing" Rule)

Each pulse should do ONE non-trivial thing beyond passive health checks:
- Restart a crashed server
- Test a tool chain end-to-end
- Verify data persistence after crash recovery
- Investigate a stale data source
- Research a pending upgrade or Dockerization
- Track a crash pattern across multiple pulses
- **Verify previous pulse's action items** — re-run a pipeline that was fixed last cycle to confirm the fix is durable and didn't degrade after a restart/cron cycle

This prevents the pulse from becoming a passive dashboard read.

### Cross-Pulse Fix Verification

When a previous pulse applied a fix (dependency install, config change, binary restart), the next pulse should **re-run the affected component** to confirm the fix survived the inter-pulse interval. This catches:

- **Partial fixes** — The fix worked once but doesn't survive a process restart or cron cycle
- **Hidden side effects** — The fix resolved symptom A but broke dependency B that only manifests on the second invocation
- **Scheduler gaps** — The fix was applied to the one-shot code path but no daemon/cron was set up to keep it running, so data will go stale again

**Pattern:**
```
Pulse N:   Identify root cause of stale data (missing dep) → Apply fix → Run pipeline → 5 signals produced ✅
Pulse N+1: Re-run pipeline from scratch → Still works → Fix is durable ✅
Pulse N+2: Check data freshness → Fresh data present (DB mod time advanced) → Scheduler gap still unaddressed ⏳
```

**Key signals in the second pulse:**
- Same pipeline command produces output again → fix is durable
- Pipeline fails with a different error → root cause was broader than diagnosed
- Pipeline succeeds but DB modification date hasn't advanced → output may not be writing to the expected DB path
- No scheduler/cron exists for the pipeline → without one, the fix is ephemeral; data will go stale again after a few days

**When to escalate:** If the fix fails at pulse N+1 with the same error it had at pulse N, the root cause analysis was incomplete — escalate to deeper investigation (dependency chain audit, config drift check, or source repo diff).

### Cron Persistence Verification

After creating a Hermes cron job from within an agent session, **verify it still exists on the next pulse.** Hermes cron jobs (created via `hermes cron create`) may be session-scoped or cleared on config reload — they do NOT reliably persist across agent sessions.

**Detection pattern:**
```bash
hermes cron list 2>&1 | grep -i "job-name"
```
If the job is missing after the inter-pulse interval, the scheduled automation is dead and needs recreation via a more durable mechanism (OS crontab, Windows Task Scheduler, or a self-registering startup script).

**Durable alternatives for Windows environments:**
- **Windows Task Scheduler** — Survives reboots and agent restarts. Create via `schtasks /create ...` with XML task definition or inline flags.
- **Hermes profile startup hook** — Add a `~/.hermes/profiles/<name>/cron/` entry that gets re-registered every time the profile starts.
- **Hybrid approach** — The pulse check cron itself can recreate the job if it detects it's missing, as part of the "one meaningful investigation" step:
  ```
  if ! hermes cron list | grep -q "admin-scout"; then
    hermes cron create ... "weekly mon 8am"
  fi
  ```

**Known cause:** Hermes cron registrations are stored in the session-scoped runtime state and may be cleared when the agent process restarts or the session is garbage-collected. Jobs created via the `hermes cron create` CLI command during one agent session may not survive to the next session. Always check `hermes cron list` at the start of a pulse or deploy critical jobs through the host OS scheduler instead.

## Pulse Frequency Recommendations

| Fleet Size | Recommended Cadence | Focus per Pulse |
|-----------|---------------------|-----------------|
| 1-5 servers | Weekly | 5min check, no deep dive needed |
| 5-15 servers | Twice weekly | Check + one investigation |
| 15-30+ servers | Daily | Quick pass + rotating deep dive per server |

## Common Pulse Pitfalls

- **Checking at wrong layer** — port check alone misses a server that's running
  but not serving MCP tools properly. Always verify with `tools/list` when possible.
- **Compound command failures** — `for d in a b c; do ls $d; done` exits at first
  missing directory. Use `[ -d "$d" ] && echo OK || echo MISSING` per-directory checks.
- **SSE timeout misinterpretation** — A curl POST that hangs on `/mcp` is normal
  for SSE servers. Check root `/` endpoint or Docker status instead.
- **Silent process death** — A process may exit without logging or error between
  pulses. Always re-check PID and port liveness each pulse.
- **Persistence confirmation** — After restarting a server with writable storage,
  write a test note and read it back before declaring the server fully recovered.
