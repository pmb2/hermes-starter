# Cron Timeout Fix: LLM-Driven → No-Agent Script

When a cron job consistently times out (Hermes hard cap: 600s / ~10 min), the root cause is usually an **LLM-driven agent** running sequential terminal commands through the agent loop. Each command adds context overhead, and complex multi-step workflows (import + embed + dream cycle) easily exceed the limit.

## The Pattern

**Problem:** LLM-driven cron job runs `gbrain import . --embed --yes` then `gbrain dream --json --yes`. Import takes 10s, dream takes 2s, but the agent loop adds margin for each turn and the 600s timer fires.

**Fix:** Convert to `no_agent=true` script job. The script IS the job — stdout is delivered verbatim.

## Steps

1. **Create the script** at `~/.hermes/scripts/<name>.sh`:
   - Use absolute paths (no `~` — it resolves inconsistently in cron context on Windows)
   - Set `PATH` explicitly (`~/.bun/bin`, `~/AppData/Roaming/npm`) — cron context doesn't inherit the user's shell
   - Add `set -o pipefail` for safety
   - Structure output clearly — it becomes the delivered message
   - Use `|| exit 1` on critical steps so failures are visible

2. **Update the cron job:**
   Via the cronjob tool:
   ```
   cronjob(action='update', job_id='...', no_agent=true, script='<name>.sh')
   ```
   Clear the prompt field — it's ignored in no_agent mode.

3. **Test** — trigger it manually and verify delivery:
   ```bash
   bash ~/.hermes/scripts/<name>.sh   # test output
   ```

## When to Use This Pattern

| Use `no_agent` | Keep LLM-driven |
|----------------|-----------------|
| Deterministic work (import, sync, embed, lint) | Need synthesis or judgment |
| Pure script ops (CLI tools, git, file ops) | Output needs rephrasing |
| Data collection (disk usage, health checks) | Multi-step conditional logic |
| Watchdog / heartbeat patterns | Need reasoning to filter results |
| Under 600s total wall time | Task duration unpredictable |

## When NOT to Use

- The script calls an API that needs auth — make sure the script has the env vars
- The job is genuinely fast (<60s) and works fine as LLM-driven — no need
- The job needs to ask the user questions or adapt based on results (no_agent jobs can't do either)

## Windows Cron Context Quirks

- **`~` resolution**: resolves to the Hermes profile home, NOT `C:\Users\<user>`. Always use `/c/Users/<user>/` absolute paths.
- **PATH**: cron context has a minimal PATH — the user's `~/.bashrc` additions (`~/.bun/bin`, `~/AppData/Roaming/npm`) are not inherited. Set `PATH` explicitly in the script.
- **Exit codes**: scripts must exit cleanly (0 = success). Non-zero exits trigger error delivery.
- **Output capture**: all stdout is captured and delivered. Use stderr for debug logging that shouldn't appear in delivery.
- **Empty stdout = SILENT**: nothing is sent to the user if stdout is empty. Use this for quiet watchdog jobs.
