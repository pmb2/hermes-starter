# Watchdog Daemon Pattern — Continuous Process Monitoring

**Relationship to the Self-Healing Pulse:** The pulse is an *intermittent diagnostic cron job* (runs every 4h). The watchdog is a *continuous daemon* that monitors processes every 15-30s. They are complementary:
- **Pulse** detects topology changes, infrastructure drift, and deep state (disk, DB, containers)
- **Watchdog** provides sub-minute crash recovery for the agent and gateways — the pulse's speed is insufficient for this

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  3-Layer Redundancy                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Watchdog Daemon (continuous)                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  pythonw hermes-watchdog.py --daemon                   │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │  │
│  │  │ hermes-agent │  │gateway-svc   │  │10 profile  │  │  │
│  │  │ (core AI)    │  │(Discord/etc) │  │gateways    │  │  │
│  │  └──────────────┘  └──────────────┘  └────────────┘  │  │
│  │  ┌──────────────┐                                     │  │
│  │  │discord-      │                                     │  │
│  │  │spacebar-bridge│                                     │  │
│  │  └──────────────┘                                     │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  Layer 2: Scheduled Task (every 5 min)                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  HermesWatchdogCheck → checks watchdog.lock → restart │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  Layer 3: VPS External Health (passive)                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  VPS probes gc.your-domain.example gateway health endpoint  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## When to Deploy the Watchdog (vs. the Pulse)

| Factor | Pulse (4h cron) | Watchdog (continuous) |
|--------|----------------|----------------------|
| Response time | Up to 4 hours | Under 30 seconds |
| Best for | Topology changes, DB health, disk, containers | Process crash recovery |
| Resource cost | ~60s per cycle | ~300MB RAM per monitored gateway |
| Escape valve | Cron re-triggers | Exponential backoff (60s max) |

**Deploy the watchdog when:**
- You have critical processes that must stay up (gateways, agent, bridge)
- Manual restart after crash causes unacceptable downtime ("lost you for hours")
- You have the RAM budget (in this environment, ~315MB per gateway is normal)

**Do NOT deploy the watchdog when:**
- The monitored processes are themselves cron jobs (use the pulse)
- RAM is constrained below 1GB free

## Windows-Specific Implementation Notes

- **PID checking requires `tasklist`, not `ps`** — msys bash's `ps` can't see Windows processes that weren't spawned from msys. Always use `tasklist //FI "PID eq N" //NH` to check process liveness.
- **`pythonw.exe` for daemon mode** — `python.exe` would keep a console window open. Use `pythonw.exe` (from the Hermes venv) when daemonizing.
- **Startup via VBS** — Windows Startup folder items that need to run hidden use a VBS launcher calling `pythonw.exe`.
- **`CREATE_NO_WINDOW` flag** — On Windows, use `creationflags=subprocess.CREATE_NO_WINDOW` when spawning monitored child processes to avoid console popups during auto-restart.
- **Lock file on Windows** — Use a simple PID file with `tasklist` check rather than `fcntl`/`flock` which doesn't exist on Windows.

## Restart Backoff Strategy

```
attempt 0 → 2s delay
attempt 1 → 4s
attempt 2 → 8s
attempt 3 → 16s
attempt 4 → 32s
attempt 5+ → 60s (cap)
```

If a process runs for >10 seconds before crashing, decrement the attempt counter (it was a real run, not a crash-loop). This prevents permanent backoff from isolated failures.

## Integration with Self-Healing Pulse

The pulse can query the watchdog's log to determine if there have been recent crashes:

```bash
grep -c "exited" ~/AppData/Local/hermes/logs/watchdog.log 2>/dev/null || echo 0
```

If crashes are detected in the last 4 hours, the pulse should investigate the root cause (MCP server failures, config corruption, resource exhaustion) rather than letting the watchdog paper over it.
