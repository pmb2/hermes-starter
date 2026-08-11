# Tracing Cross-File Pytest State Pollution

A concrete application of "Build to Understand" and "Be a Scientist" from karpathy-principles. Use when a test passes in isolation but fails when run after another test file in the same pytest process.

## Detection Pattern

A test passes with `pytest tests/path/to/test_file.py` but fails with `pytest tests/path/` (whole directory). The failing assertion involves state that shouldn't change between test files.

## Systematic Investigation

### Phase 1 — Narrow the polluter

1. **Binary search by file**: Run pairs of test files until you find the one whose prior execution causes the failure:
   ```bash
   python -m pytest tests/path/test_alice.py tests/path/test_suspect.py -q
   ```
   If `test_suspect` fails only when `test_alice` runs first, you've found the polluter.

2. **Binary search by test**: Narrow further by running individual tests from the polluter file before the failing test:
   ```bash
   python -m pytest tests/path/test_alice.py::TestFoo::test_bar tests/path/test_suspect.py::TestFailing::test_baz -q
   ```

3. **Verify same-process vs subprocess**: If `subprocess.run` of the two files in sequence passes but `pytest path/` fails, the pollution is within the same Python process (module-level caches, ContextVars, global dicts).

### Phase 2 — Find the leaked state

**Check env vars first** (most common polluter): Run a script between polluter and suspect to dump the diff:
```python
import os
# Check for env vars that shouldn't be set
env_before = set(os.environ.keys())
# ... run polluter ...
env_after = set(os.environ.keys())
print("Set by polluter:", env_after - env_before)
```

Key env vars to watch:
- `HERMES_*` behavioral vars (`HERMES_CRON_SESSION`, `HERMES_INTERACTIVE`, etc.)
- `TIRITH_ENABLED`, other feature-flag env vars
- Credential vars that conftest should have stripped

**Check module-level caches**: Python's `sys.modules` caches imports. If a module has a top-level call like `load_permanent_allowlist()` at the bottom of the file, it runs at import time — before any conftest fixture can set up test isolation.

Common module-level offenders:
```python
# Last line of the file — runs at import time, not lazily
initialize_something()  # reads config → caches result → persists across tests
load_permanent_allowlist()  # reads real config even when conftest sets fake HERMES_HOME
```

**Check ContextVars**: Thread- or task-local state. A ContextVar set in one test and not reset leaks to the next test in the same thread:
```python
# If test A sets this and doesn't clean up, test B sees it
_hermes_interactive_ctx: ContextVar = ContextVar("hermes_interactive", default=None)
```
Look for `_hermes_interactive_ctx.get()` returning non-None when it should be None.

### Phase 3 — Isolate with a reproduction script

Write a standalone Python script that reproduces the import order and state:

```python
"""Reproduce the pollution in isolation."""
# 1. Import the polluter's module-level imports
from model_tools import handle_function_call  # triggers tools/approval import

# 2. Simulate conftest setup
os.environ['HERMES_HOME'] = str(tempdir)
import hermes_cli.config as cfg
cfg._LOAD_CONFIG_CACHE.clear()

# 3. Check the leaked state
from tools.approval import load_permanent_allowlist  # was pre-populated at import

# 4. Run the failing test logic
...
```

### Phase 4 — Fix

Choose the right fix based on what leaked:

| Leak Type | Fix |
|-----------|-----|
| Module-level side effect at import | Convert to lazy-init with flag: `if _loaded: return; _loaded = True; load()` |
| Env var not cleaned by conftest | Add to `_HERMES_BEHAVIORAL_VARS` in `conftest.py` |
| ContextVar not reset | Wrap in try/finally with `ctxvar.reset(token)` |
| Config cache primed with real path | Clear cache in autouse fixture: `_LOAD_CONFIG_CACHE.clear()` |
| Global set populated at import | Add lazy-init to read paths (see lazy-init pattern below) |

#### Lazy-init Pattern for Module-Level Side Effects

```python
# OLD (pollutes at import time):
load_permanent_allowlist()  # last line of module

# NEW:
_loaded: bool = False

def load_thing() -> set:
    global _loaded
    if _loaded:
        return set(_approved)
    _loaded = True
    # ... actual load logic ...

def check_thing() -> bool:
    load_thing()  # lazy-init on first read
    # ... check logic ...

def approve_thing() -> None:
    load_thing()  # lazy-init on first write
    # ... approve logic ...
```

### Key Principles Applied

- **Build to Understand**: The reproduction script isolates the phenomenon so you observe the leak directly instead of guessing.
- **Layer by Layer**: Start at the outermost layer (test file ordering), then drill into module-level code, then into individual functions.
- **Be a Scientist**: Each step is a single hypothesis test — "does test_file_A cause the failure?" → run → observe → update model.
- **Read the Source, Luke**: The answer is at the bottom of `tools/approval.py`, line 3242. Always check the last few lines of a module for side effects.
