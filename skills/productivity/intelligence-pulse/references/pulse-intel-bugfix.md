# pulse_intel.py — Bug Fix: UnboundLocalError (datetime scoping)

## Bug

`pulse_intel.py` at `${USER_HOME}/AppData/Local/hermes/skills/productivity/intelligence-pulse/scripts/pulse_intel.py` had a Python scoping bug.

### Symptom

```
UnboundLocalError: cannot access local variable 'datetime' where it is not associated with a value
```

at line 177 (`now_iso = datetime.now(timezone.utc)...` inside `main()`).

### Root Cause

Module-level import:
```python
from datetime import datetime, timezone
```

Inside `main()`, inside a `try/except` in the `if total == 0:` block:
```python
try:
    from datetime import datetime  # <-- THIS CAUSES THE BUG
    last_dt = datetime.fromisoformat(...)
```

Python's scoping rules: if a variable name appears in ANY `import` or assignment inside a function (even inside a `try` block that may never execute), Python treats that name as **local** for the entire function. The module-level `datetime` is shadowed by the local-but-not-yet-assigned `datetime`. Any use of `datetime` before that line raises `UnboundLocalError`.

### Fix

Remove the redundant inner import. `datetime` is already available from the module-level import:

```python
try:
    # datetime is already imported at module level — no re-import needed
    last_dt = datetime.fromisoformat(last_check_time.rstrip("Z"))
    delta = datetime.now(timezone.utc) - last_dt.replace(tzinfo=timezone.utc)
```

### Prevention

- Never re-import a module-level name inside a function body
- If you MUST import inside a function (e.g., optional dependency), use `import datetime as dt_mod` or alias to avoid shadowing
- Linters (pylint, pyflakes) may not catch this if the inner import is inside a `try/except` block
- Test pattern: run the script in a context where the `if total == 0:` branch executes (all data sources return empty)
