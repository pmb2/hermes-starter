# Fleet Manager Architecture — Bulletproof Multi-Bot Deployments

## Design Rationale

Running multiple Spacebar bot gateways manually (one `terminal(background=true)` per bot) is fragile:
- No auto-restart when a process crashes
- No health checking — bots can be "alive" but disconnected
- No centralized logging or alerts
- Manual restarts needed after system reboot

The Fleet Manager creates a **single supervisory process** that manages the full lifecycle.

## Architecture

```
Fleet Manager (spacebar-fleet-manager.py)
├── subprocess: <bot-1> spacebar-gateway.py
├── subprocess: <bot-2> spacebar-gateway.py
├── subprocess: <bot-3> spacebar-gateway.py
├── ... (up to N bots, staggered launch)
│
└── asyncio watchdog loop (every 15s)
     ├── 1. Poll each subprocess — is the PID alive?
     │    └── Dead? → Log → Exponential backoff (2s–60s) → Restart
     └── 2. Health check 1 bot (round-robin) via Spacebar REST API
          └── TIMEOUT? → Log as transient, skip restart (REST ≠ WSS)
```

## Components

### `spacebar-fleet-manager.py`
- Location: `agent-fleet/scripts/spacebar-fleet-manager.py`
- Single file, no dependencies beyond standard library + Hermes venv Python
- Reads bot tokens from profile `.env` files at `~/AppData/Local/hermes/profiles/<name>/.env`
- Creates rotating log at `~/.hermes/logs/fleet-manager.log` (10MB, 3 backups)
- Each subprocess writes its own gateway log to `~/.hermes/logs/spacebar-<name>.log`

### `start-spacebar-fleet.bat`
- Location: `agent-fleet/scripts/start-spacebar-fleet.bat`
- Double-click launcher for Windows
- Auto-restarts the fleet manager if it exits with error
- Shows ASCII banner in console

## Key Behaviors

### Subprocess Management
- Each gateway is spawned with `subprocess.Popen()` using `CREATENEWPROCESSGROUP` flag
- 1-second stagger between launches to prevent identify collisions on Spacebar
- Tokens passed via environment (not CLI args) to prevent shell history leaks
- Gateway logs captured to individual files (appended, not truncated)

### Exponential Backoff
- Starting delay: 2 seconds
- After each restart: multiply by 1.5
- Cap at 60 seconds
- Reset to 2 seconds on successful restart (process stays alive > check interval)

### Health Check
- One bot checked per 15s cycle (each bot checked every ~75s)
- HTTP GET to `/users/@me` with bot token
- Verifies returned `username` matches expected bot name
- Failure triggers restart

### Graceful Shutdown
- SIGINT (Ctrl+C) or SIGBREAK triggers shutdown
- Sends CTRL_BREAK_EVENT to subprocess group (Windows)
- 10-second wait for graceful exit, then `process.kill()`

## Windows Deployment

### Task Scheduler (Auto-Start on Boot)
1. Open Task Scheduler → Create Basic Task
2. Name: "Spacebar Fleet Manager"
3. Trigger: When the computer starts
4. Action: Start a program
   - Program: `${USER_HOME}\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`
   - Arguments: `${MY_REPOS}\Documents\github\agent-fleet\scripts\spacebar-fleet-manager.py`
   - Start in: `${MY_REPOS}\Documents\github\agent-fleet\scripts`
5. Check "Run whether user is logged on or not"

### Startup Validation
The fleet manager should have all bots connected within 30 seconds of launch. To verify:
```bash
# Check fleet manager log
tail -n 20 ~/.hermes/logs/fleet-manager.log
# Expected: All N "Started" entries + "Monitoring cycle started"

# Check gateway logs for connection
grep "✓ discord connected\|Registered /skill command" ~/.hermes/logs/spacebar-*.log
# Expected: N matches (one per bot)

# Check health check behavior — after 120s grace, expect transient errors (not restarts):
grep "transient error\|Health check" ~/.hermes/logs/fleet-manager.log | tail -5
# Expected: "[INFO] Health check transient error (skipping restart)" — NOT "FAILED — restarting"

## Failure Modes

| Failure | Detection | Recovery |
|---------|-----------|----------|
| Stale gateway.lock from killed process | Process dies on startup with lock error | Patched lock path (`gateway.lock.spacebar`) avoids the collision entirely |
| Gateway process exits silently | Watchdog detects PID gone | Auto-restart with backoff |
| Spacebar server down | All health checks fail | Fleet manager keeps retrying, backoff caps at 60s |
| Bot token expired | Health check returns 401 | Restart won't help — manual token refresh needed |
| Gateway connected but idle (no crash) | Health check passes, PIDs alive | This is normal — gateway daemons just wait for events |
| REST API times out (WSS stays healthy) | Health check read timeout on `/users/@me` | **Do NOT restart** — log as transient error and return healthy. The 120s startup grace period + timeout-skip in the exception handler prevents false-positive restarts. WSS connections are independent of REST. |
