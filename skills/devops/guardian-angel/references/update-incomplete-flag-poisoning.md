# `.update-incomplete` Flag Poisoning — Cross-Cutting Failure

The `.update-incomplete` flag at `~/AppData/Local/hermes/hermes-agent/.update-incomplete` is created when `hermes update` starts and is cleaned on success. If the update process is killed (watchdog timeout, manual kill, crash), the flag **persists on disk** and poisons every subsequent command that shares the init path.

## Symptoms

- `hermes cron list` hangs for 15+ seconds then times out with "A previous hermes update was interrupted mid-install"
- `hermes kanban` commands show the same timeout
- Kanban worker agents crash at spawn with "pid XXXX not alive" — the spawned agent can't finish init before the update-completion step times out
- **Every** CLI command shows the same symptom, regardless of domain

## Detection

```bash
ls -la ~/AppData/Local/hermes/hermes-agent/.update-incomplete
cat ~/AppData/Local/hermes/hermes-agent/.update-incomplete
# Contains: started=<epoch> / pid=<PID>
# If process <PID> is no longer running → flag is stale
```

## Fix

```bash
rm -f ~/AppData/Local/hermes/hermes-agent/.update-incomplete
```

⚠️ Only remove if the original PID is confirmed dead.

## Recurring Marker Pattern

This flag has reappeared **multiple times** (Jun 25, Jun 27) after being cleared. Each recurrence indicates a hermes update or auto-updater that gets interrupted mid-install. To trace the source:

```bash
# Search for what writes the marker
grep -rn "update-incomplete" ~/AppData/Local/hermes/ --include="*.py" --include="*.ts" --include="*.json"

# Check session history for hermes update commands
session_search(query="hermes update OR interrupted update")
```

## Impact on Guardian Angel

The Guardian Angel runs health checks via cron every 5min. When the `.update-incomplete` flag is present, the GA's cron session hangs during the init phase (trying to finish the update first), causing the watchdog to miss its check window. This can cascade into false "gateway down" alerts because the GA can't reach the gateway health check fast enough.

## Prevention

A permanent fix would detect stale PIDs in the scheduler's init path — if the marker file contains a PID that is no longer alive, auto-clear the marker and proceed instead of attempting to finish a dead update.
