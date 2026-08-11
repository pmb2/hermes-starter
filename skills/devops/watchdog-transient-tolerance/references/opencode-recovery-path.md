# OpenCode Recovery Path for Watchdog-Agent Hybrid (2026-08-10)

When a watchdog detects a real error (not a false positive, after the 3x
threshold), it can invoke OpenCode as a recovery agent — using a different
LLM provider than Hermes itself, so a provider outage on Hermes doesn't
take down the recovery path.

## Architecture

```
Watchdog (no_agent, every 5 min)
  → Detect errors (log scan, ignore_re, 3x threshold)
  → Write recovery brief to temp file
  → Invoke OpenCode: `opencode run --model deepseek/deepseek-chat -f <brief>`
  → OpenCode diagnoses + fixes using DeepSeek API
  → Report success/failure
```

## Key Design Decisions

### 1. Separate provider for recovery
Hermes uses OmniRoute (GPT-5.6-SOL). OpenCode uses DeepSeek (`deepseek/deepseek-chat`). If OmniRoute goes down, the watchdog still works because it runs as a no_agent script (zero tokens). Only when it needs to fix something does it call OpenCode — which uses DeepSeek, a completely independent provider.

### 2. Shell=True on Windows
OpenCode is installed via npm at `${USER_HOME}\AppData\Roaming\npm\opencode.cmd`. On Windows, `.cmd` files need `shell=True` in `subprocess.run`:

```python
proc = subprocess.run(
    cmd, shell=True, capture_output=True, text=True,
    timeout=300  # 5 min — OpenCode session init takes ~30s
)
```

### 3. 5-minute timeout
OpenCode's session initialization takes ~30s, and the fix itself may take 1-2 min. A 300s timeout is safe for the full recovery cycle.

### 4. Error brief as temp file
The watchdog writes a markdown brief to a temp file with the error details, then passes `-f <brief_path>` to OpenCode. This is more reliable than piping via stdin because OpenCode's CLI reads from files directly.

```python
brief_path = config.LOG_DIR / f"recovery_brief_{datetime.now():%Y%m%d_%H%M%S}.md"
brief_path.write_text(brief)

cmd = (
    f'{config.OPENCODE_BIN} run '
    f'"Fix the errors described in {brief_path}. Read the file, fix, verify." '
    f'--model {config.BACKUP_MODEL} '
    f'-f {brief_path} '
    f'--dir {config.HERMES_DIR}'
)
```

## Verification

Test that OpenCode is reachable with the backup model:

```bash
opencode run "echo OPENCODE_OK" --model deepseek/deepseek-chat
# Expected: exit 0, stdout contains "OPENCODE_OK"
```

If this fails:
- Check `opencode auth list` — verify credentials for the backup model
- Check `opencode.db` — corrupt SQLite DB kills all OpenCode invocations
  (fix: `kill stale opencode/bun processes; remove opencode.db; it regenerates`)

## Files

- `pmb2/coding-buddy` — full repo with supervisor.py, cron wrapper
- `src/supervisor.py` — RecoveryEngine.invoke_recovery()
- `scripts/coding_buddy.py` — cron wrapper with state file + 3x threshold