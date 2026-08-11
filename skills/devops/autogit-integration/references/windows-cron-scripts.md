# Windows Cron: no_agent Script Path Workaround

## Problem

The Hermes cron scheduler resolves relative script paths using
`~/AppData\Local\hermes\scripts\` as the base directory.

On Windows/MSYS, the backslash characters in this path get consumed as
escape characters when the resolved path is passed to bash. The result
is a mangled path:

```
Expected:  ${USER_HOME}\AppData\Local\hermes\scripts\myscript.sh
Actual:    C:\Users\<you>\AppData\Local\hermes\scripts\myscript.sh
```

This produces error: `No such file or directory` (exit code 127).

## Root Cause

The scheduler's base path is hardcoded with Windows backslash separators
(e.g. `AppData\Local\hermes\scripts\`). When concatenated and passed to
bash on MSYS, `\` is interpreted as an escape character:
- `\U` → `U`, `\T` → `T`, `\A` → `A`, `\L` → `L`, `\h` → `h`, `\s` → `s`
- The backslash is silently dropped, collapsing the path.

## Solution

Always use **Python scripts** (`.py`) for `no_agent=true` cron jobs on
Windows. Python handles the scheduler's absolute path resolution correctly
through `subprocess.run()`.

## Migration Pattern

### .sh (broken)
```json
{
  "script": "my-watchdog.sh",
  "no_agent": true
}
```

### .py (works)
```json
{
  "script": "my-watchdog.py",
  "no_agent": true
}
```

## Python Script Pattern

When writing no_agent Python scripts for Windows cron, always:

1. **Use `shell=True` in subprocess** — the cron context has a minimal
   PATH. `shell=True` goes through cmd.exe which finds common binaries.

2. **Set PATH explicitly** — npm/node/bun binaries aren't on the default
   cron PATH. Set them before any subprocess call:

```python
def run(cmd_str, timeout=300, cwd=None):
    env = os.environ.copy()
    env["PATH"] = (
        r"${USER_HOME}\.bun\bin;"
        r"${USER_HOME}\AppData\Roaming\npm;"
        + env.get("PATH", "")
    )
    result = subprocess.run(
        cmd_str, capture_output=True, text=True,
        timeout=timeout, cwd=cwd, env=env, shell=True
    )
    return result.returncode, (result.stdout or "") + (result.stderr or "")
```

3. **Use full paths for special binaries** when possible (e.g. `node
   C:\path\to\index.js` instead of relying on npm shims). npm shims
   are POSIX shell scripts that can't run from cmd.exe/Python directly.

4. **Strings, not lists** — with `shell=True`, pass command strings
   (e.g. `"gbrain dream --json --yes"`) not argument lists. Lists get
   joined incorrectly on Windows.

## Affected Cron Jobs

Any `no_agent=true` job with a `.sh` scripts will fail. Convert them
to `.py` using the pattern above.
