# Guardian Angel Infinite Restart Loop — Case Notes

> Date: 2026-07-15
> Affected: Hermes Agent / Gateway on Windows
> Symptoms: Session killed every 5–10 minutes; cron reports "Gateway DOWN — restarting"; 551+ consecutive failures.

## What happened

Guardian Angel (`guardian-angel.py`) was configured as a cron job running every 5 minutes.
It read `gateway_state.json` from a hardcoded path (`~/.hermes/gateway_state.json`) instead of from `$HERMES_HOME`.

On this host:

```bash
HERMES_HOME=${USER_HOME}\AppData\Local\hermes
```

The gateway correctly wrote state to `${USER_HOME}\AppData\Local\hermes\gateway_state.json`.
Guardian Angel looked at the wrong (empty/missing) file, concluded the gateway was down,
incremented `consecutive_failures`, and issued `hermes gateway restart` after 3 failures.

Each restart:
- Killed the active Discord session
- Created a new gateway PID
- Still left the `~/.hermes` state file empty

Result: an infinite restart loop with 551+ consecutive failures and 4+ restarts per hour.

## Diagnosis commands

```bash
# Check environment
python -c "import os; print(os.environ.get('HERMES_HOME'))"

# Check the path the watchdog reads vs. the path the gateway writes
ls -la "$HERMES_HOME/gateway_state.json"
ls -la ~/.hermes/gateway_state.json

# Check failure counter
python -c "import json, pathlib; print(json.loads(pathlib.Path('$HERMES_HOME/guardian-angel-state.json').read_text())['gateway']['consecutive_failures'])"

# Find the cron job that is restarting
hermes cron list | grep -i "guardian\|self-healer\|watchdog"
```

## Fix applied

1. **Remove the offending cron job** so it cannot restart the gateway:
   ```bash
   hermes cron remove <guardian-angel-job-id>
   ```

2. **Make the watchdog script respect `HERMES_HOME`**:
   ```python
   HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
   ```

3. **Reset the failure counter** in `guardian-angel-state.json`:
   ```json
   {
     "gateway": {
       "consecutive_failures": 0,
       "restart_count_last_hour": 0,
       "last_restart": null,
       "restart_history": []
     }
   }
   ```

4. **Replace Guardian Angel with a silent Self-Healer** that:
   - Runs every 15 minutes (`deliver: local`)
   - Only reports when it actually fixes something or finds a genuine failure
   - Does NOT restart the gateway automatically
   - Monitors: zombie Firefox, stale locks, gateway port, cron failures, config errors, disk space, MCP health

5. **Fix cron job script paths** that were failing with:
   ```
   Script not found: ${USER_HOME}\AppData\Local\hermes\scripts\python "C:\...\hermes_self_healer.py"
   ```
   Root cause: `script` field contained `python "path"`. The cron runner already prepends the interpreter.
   Correct value: just the filename or absolute path.

## Key operator preferences captured

- Watchdogs/self-healers should stay silent when healthy (`deliver: local`).
- Only report when an action is taken or a genuine unfixable failure occurs.
- Cron job `script` field must be the script path only, not `python "path"`.

## Files involved

- `${USER_HOME}/AppData/Local/hermes/scripts/guardian-angel.py`
- `${USER_HOME}/AppData/Local/hermes/scripts/hermes_self_healer.py`
- `${USER_HOME}/AppData/Local/hermes/guardian-angel-state.json`
- `${USER_HOME}/AppData/Local/hermes/gateway_state.json`
