# Coding Buddy Cron Wrapper — Worked Example

This is the production cron wrapper from `pmb2/coding-buddy` that implements all
five patterns from the `autonomous-system-supervision` skill.

## Production Script

```python
"""
Coding Buddy cron wrapper — self-contained, no imports.
SILENT when healthy. Only outputs (and thus delivers) on actual recovery actions.

Key rules:
- No errors found → SILENT (no stdout)
- Errors but in cooldown → SILENT (no stdout) 
- Errors with successful recovery → OUTPUT (delivered to chat)
- Errors with failed recovery → OUTPUT (delivered to chat)
- Mutual health check failures → OUTPUT
"""

import sys, os, subprocess, json
from pathlib import Path

REPO_ROOT = Path(r"${MY_REPOS}\Documents\github\coding-buddy")
SUPERVISOR = REPO_ROOT / "src" / "supervisor.py"


def run_supervision():
    """Run the supervisor. Returns (should_output, message_lines, exit_code)."""
    if not SUPERVISOR.exists():
        return True, ["CODING BUDDY: Supervisor missing"], 1
    
    try:
        result = subprocess.run(
            [sys.executable, str(SUPERVISOR), "--once", "--json"],
            capture_output=True, text=True, timeout=120,
            cwd=str(REPO_ROOT),
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
        )
        
        if result.returncode != 0:
            return True, ["CODING BUDDY ERROR: supervisor crashed", result.stderr[-500:]], 1
        
        data = json.loads(result.stdout)
        errors_found = data.get('errors_found', 0)
        recovery_attempted = data.get('recovery_attempted', False)
        recovery_success = data.get('recovery_success', False)
        
        # HEALTHY: no errors → SILENT
        if errors_found == 0:
            return False, [], 0
        
        # COOLDOWN: errors but no recovery attempted → SILENT
        if not recovery_attempted:
            return False, [], 0
        
        # RECOVERY: always report
        if recovery_success:
            return True, [f"CODING BUDDY — RECOVERED: Fixed {errors_found} error(s)"], 0
        else:
            return True, [f"CODING BUDDY — RECOVERY FAILED: {errors_found} errors"], 1
    
    except subprocess.TimeoutExpired:
        return True, ["CODING BUDDY — timed out"], 1
    except Exception as e:
        return True, [f"CODING BUDDY ERROR: {e}"], 1


def check_mutual_health():
    """Check if the Self-Enhancing Loop is healthy."""
    try:
        result = subprocess.run(
            ['hermes', 'cron', 'list'], capture_output=True, text=True, timeout=10
        )
        if '27c6327ad9e1' not in result.stdout:
            return True, ["CODING BUDDY: Self-Enhancing Loop cron missing"]
        if 'Self-Enhancing Loop' in result.stdout:
            lines = result.stdout.split('\n')
            in_block = False
            for line in lines:
                if 'Self-Enhancing Loop' in line:
                    in_block = True
                if in_block and 'error:' in line.lower():
                    return True, ["CODING BUDDY: Self-Enhancing Loop has errors"]
        return False, []
    except Exception:
        return False, []


def main():
    should_output, messages, exit_code = run_supervision()
    
    alert, health_msgs = check_mutual_health()
    if alert:
        should_output = True
        messages.extend(health_msgs)
    
    if should_output and messages:
        print('\n'.join(messages))
    
    sys.exit(exit_code if should_output else 0)


if __name__ == "__main__":
    main()
```

## What This Demonstrates

1. **Self-Contained** — zero imports from the repo. Uses `subprocess` to call `src/supervisor.py`
2. **Silent When Healthy** — three levels of silence: no errors (return without print), cooldown (return without print), healthy mutual check (return without print)
3. **Mutual Health** — checks that the Self-Enhancing Loop cron exists and has no errors
4. **Output-Only-On-Action** — only prints when a recovery was actually attempted
5. **Graceful Degradation** — every subprocess call has a timeout and try/except

## Cron Configuration

```bash
hermes cron create \
  --name "Coding Buddy Watchdog" \
  --schedule "*/5 * * * *" \
  --script coding_buddy.py \
  --no-agent \
  --deliver origin
```

The `--no-agent` flag means: no LLM is involved, the script's stdout is delivered directly. Empty stdout = no delivery. Perfect for watchdogs.
