# Diagnosing Cron Job Failures

When a `hermes cron list` run shows `error:` in the Last run column, follow this diagnostic chain to find and classify the root cause.

## Step 1: Parse the Error Type

From `hermes cron list`, the error field tells you the failure mode:

| Error Pattern | Meaning | Most Common Cause |
|---|---|---|
| `Script not found: <path>` | The cron runner can't stat the script at the resolved path | Bad path in cron config (double prefix, wrong dir) |
| `Script exited with code 127` | bash exited because `exec` failed | MSYS2 path mangling (backslashes eaten) OR file truly missing OR wrong shebang |
| `Script exited with code 1` | Script ran but failed internally | Check script content, dependencies |
| `Script exited with code 124` | Script timed out | Long-running operation, hung process |
| `error: <Python traceback>` | Python script exception | Logs, dependencies, env |
| `stderr: <msg>` | Always present alongside other errors | The stderr line IS the primary signal |

## Step 2: Verify Script Existence

The cron runner resolves the script relative to `~/AppData/Local/hermes/scripts/`. If the cron config says `Script: scripts/foo.sh`, the runner tries `~/AppData/Local/hermes/scripts/scripts/foo.sh` — double prefix.

```
ls -la ~/AppData/Local/hermes/scripts/<script-name>   # Does it exist at ALL?
ls ~/AppData/Local/hermes/scripts/                      # List all scripts
```

**Double-prefix pattern:** If the cron config already starts with `scripts/` and the runner also prepends the scripts directory, you get `scripts/scripts/...`. Fix: remove `scripts/` from the cron config's Script field — just give the bare filename.

## Step 3: Check MSYS2 Path Translation (Windows/Git-Bash Only)

When the error shows a path with backslashes stripped — e.g.
```
/bin/bash: C:/Users/<you>/AppDataLocalhermesscriptsfoo.sh: No such file or directory
```
Bash has eaten the backslashes (`\U` → escape, `\L` → escape, etc.). This happens when the path is passed unquoted through MSYS2.

**Diagnose:**
```bash
# Does the script exist at the intended path?
stat ${HERMES_HOME}/scripts/foo.sh

# Can bash find it with a clean path?
/usr/bin/bash ${HERMES_HOME}/scripts/foo.sh   # Try MSYS path

# Does it have the right shebang?
head -1 ${HERMES_HOME}/scripts/foo.sh
```
Expect `#!/usr/bin/bash` or `#!/bin/bash`. A shebang pointing to a non-existent shell also yields code 127.

## Fix: Python Wrapper with Stdin Pipe (for MSYS-Path-Vulnerable Scripts)

When a `.sh` script consistently fails with code 127 due to MSYS path mangling but works fine from the terminal, the most reliable fix is a Python wrapper that reads the script content and pipes it to `bash -s` via stdin. This bypasses all path-passing to the bash process.

### The Pattern

```python
import subprocess, sys, os

SCRIPT_PATH = r"${USER_HOME}\AppData\Local\hermes\scripts\your-script.sh"

def main():
    if not os.path.exists(SCRIPT_PATH):
        print(f"ERROR: Script not found at {SCRIPT_PATH}")
        sys.exit(1)

    with open(SCRIPT_PATH, 'r', newline='\n') as f:
        script_content = f.read()

    result = subprocess.run(
        ["bash", "-s"],
        input=script_content.encode("utf-8"),
        capture_output=True,
        text=False,
        timeout=600
    )

    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")

    if stdout:
        print(stdout)
    if stderr:
        print(stderr)

    if result.returncode == 0:
        sys.exit(0)
    else:
        sys.exit(result.returncode)
```

### Why This Works

The root cause is that `subprocess.run(["bash", "C:/some/path.sh"])` on Windows passes the path through the Windows CreateProcess API to bash. Git-bash's MSYS2 DLL then translates `C:\...` → `C:...` (stripping backslashes which it interprets as shell escapes). Even forward slashes (`C:/...`) and MSYS paths (`/c/...`) can fail because the subprocess environment may not have MSYS path translation active.

By sending the script content via stdin (`bash -s`), we never pass a file path as a command-line argument — bash reads the script from its standard input. No path translation required.

### CRLF Pitfall

On Windows, `subprocess.run` with `text=True` (the default when `input` is a string) converts `\n` to `\r\n` on stdin. Bash receives `\r\n` line endings, which cause:

```
/bin/bash: line 8: set: pipefail\r: invalid option name
/bin/bash: line 9: $'\r': command not found
```

**Fix:** Always use `input=script_content.encode("utf-8")` with `text=False` when piping scripts to bash. This sends raw bytes with no newline conversion.

Also ensure the script file itself has LF (`\n`) line endings, not CRLF (`\r\n`):

```bash
sed -i 's/\r$//' ${HERMES_HOME}/scripts/your-script.sh
```

### Testing

After creating the wrapper, test it:
```bash
# Direct
python ${HERMES_HOME}/scripts/your-wrapper.py

# Via cron (if it's a cron job)
cronjob action=run job_id=<id>
```

Then update the cron job to point to the Python wrapper instead of the `.sh` script:
```bash
cronjob action=update job_id=<id> script=your-wrapper.py
```

## Step 4: Test Direct Execution

```bash
# Run the script directly, same environment as cron
/usr/bin/bash ${HERMES_HOME}/scripts/foo.sh 2>&1
echo "Exit: $?"
```

- **Times out** (exit 124) → script hangs under cron conditions too.
- **Same 127 error** → the script truly can't execute (shebang, permissions, missing binary).
- **Runs fine** → the issue is in how the cron runner resolves/passes the path, not the script itself.

## Step 5: Check for Secondary Evidence

Not all cron failures are script execution — some are service-liveness failures that only manifest at run time:

```bash
# Is there a PID file from a previous run?
stat ~/AppData/Local/hermes/<service>.pid 2>/dev/null

# Is the process actually running?
ps aux | grep -iE "<service>|<script-name>" | grep -v grep

# Is the expected port open?
ss -tlnp | grep -E "<expected-port>"

# Are containers healthy (for docker-cron jobs)?
docker ps --format "{{.Names}} {{.Status}}" | grep -iE "<service>"
```

## Edge Case: "No model configured" Error

When a cron job fails with:
```
RuntimeError: Cron job '<name>' has no model configured (job.model=None,
HERMES_MODEL='', config.yaml model.default missing or empty).
Set a per-job model via `cronjob action=update job_id=<id> model=<name>`
or set a default with `hermes model <name>`.
```

### Three Possible Causes

| Cause | Check | Fix |
|-------|-------|-----|
| **Per-job model missing** | `cronjob action=list` → check job's `model` field | `cronjob action=update job_id=<id> model={"model":"deepseek-v4-flash","provider":"opencode-go"}` |
| **config.yaml model.default empty** | Check `~/.hermes/config.yaml` for `model.default` or the bare `model:` key above `api_mode` | Set `hermes model <name>` or edit config.yaml directly |
| **config.yaml model section missing default** | Look for the top-level `model:` section (not inside `auxiliary` or `agent`) | Add `default: <model>` and `provider: <provider>` under the top-level `model:` key |

**The subtle case:** The `model.default` key exists but there's a separate top-level `model: ''` key that shadows it. When the cron runner reads the config, it may read the wrong key. Check for both `model:` (bare key) and `model.default:` (nested key) — if both exist, the bare `model: ''` may be read instead.

### Fix

```bash
# Fix by setting per-job model (most reliable)
cronjob action=update job_id=<id> model='{"model":"deepseek-v4-flash","provider":"opencode-go"}'

# Or fix the global default
hermes model deepseek-v4-flash
```

### Systemic Pattern

If many jobs fail simultaneously with the same error, it's likely a global config issue
(config.yaml model.default), not individual job configs. Fix the global default first,
then re-fire the batch.

## Edge Case: Stale Hardcoded Date in Cron Prompt

When a cron job has a prompt with a hardcoded date reference (e.g., `"Current time: approximately June 23, 2026"`), the job's reasoning will be based on wrong temporal context:

### Detection
- Cron jobs that run but produce obviously stale reports (e.g., referencing events from days ago as "today")
- Watchdog-style jobs that fail to detect current incidents because their reference timestamp is wrong
- Checking the prompt text reveals date literals embedded in the instructions

### Fix
```bash
# Update the cron job prompt to use dynamic time detection
cronjob action=update job_id=<id> prompt="[Updated prompt without hardcoded dates]"
```

### Prevention
- Never write date literals in cron job prompts — use relative language ("current time", "today", "in the last 24 hours")
- If a date reference is needed for context, derive it dynamically from the system clock
- Watchdog-style jobs are the most vulnerable because they compare last_run_at against "current time"

## Step 7: Classify the Severity

| Classification | Criteria | Action |
|---|---|---|
| **Known/unchanged** | Same error as previous pulse run, not blocking active work | Note as lingering, don't re-alert |
| **New failure** | First occurrence or recurrence after a fix | Report immediately |
| **Spontaneous recovery** | Was errored, now ok without intervention | Note recovery, investigate what changed |
| **Cascading failure** | Cron B depends on service A that is also down | Fix root cause (service A), not cron B |
