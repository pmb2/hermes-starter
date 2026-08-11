# PYTHONPATH Cross-Version Venv Shadowing — Discovery & Debugging

Discovered during Sentry pulse (2026-07-30) on Hermes Agent codebase.

## Symptom

```
tests/hermes_state/test_aux_usage_accounting.py:
  SystemExit: Web UI requires fastapi and uvicorn.
```

The misleading error message pointed at missing `fastapi`, but fastapi/uvicorn/pydantic were all installed. The real failure was deeper.

## Full Error Chain (abbreviated)

```
venv/Lib/site-packages/pydantic_core/__init__.py
  → from ._pydantic_core import ...
  → ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'

During handling of the above exception:
hermes_cli/web_server.py
  → lazy_ensure("tool.dashboard", prompt=False) failed
  → raise SystemExit("Web UI requires fastapi and uvicorn.")
```

The **first** `ModuleNotFoundError` is the real root cause. The `SystemExit` from the lazy-import handler is a red herring.

## Root Cause

Two venvs coexisted in the same project directory:

| Venv     | Python | C extension ABI | Status        |
|----------|--------|-----------------|---------------|
| `venv/`  | 3.11.9 | `cp311`         | Has pytest, complete |
| `.venv/` | 3.13.3 | `cp313`         | Missing test deps, partial migration |

The `PYTHONPATH` environment variable listed `venv/Lib/site-packages` (the 3.11 venv) **before** `.venv/Lib/site-packages` (the 3.13 venv):

```
PYTHONPATH=...;C:\...\hermes-agent\venv\Lib\site-packages;...;C:\...\hermes-agent\.venv\Lib\site-packages
```

When `.venv/Scripts/python` (3.13) ran, it found `pydantic` in the old `venv/Lib/site-packages` first. That pydantic in turn tried to load `_pydantic_core.cp311-win_amd64.pyd` — a binary compiled for Python 3.11, which Python 3.13 cannot load.

## Diagnosis Steps Taken

1. **Check sys.path** — `.venv/Scripts/python -c "import sys; print('\n'.join(sys.path))"` revealed `venv/Lib/site-packages` appeared before `.venv/Lib/site-packages`.

2. **Check PYTHONPATH** — `echo $PYTHONPATH` confirmed the old venv was listed first.

3. **Check which Python ran** — `which python` showed `.venv/Scripts/python` (3.13), not `venv/Scripts/python` (3.11).

4. **Check .pyd ABI tag** — `ls venv/Lib/site-packages/pydantic_core/*.pyd` → `_pydantic_core.cp311-win_amd64.pyd` confirmed binary was for 3.11.

5. **Verify the old venv works** — `venv/Scripts/python -c "import pydantic_core"` succeeded, confirming the old venv's own Python (3.11) could load its own C extension.

6. **Check pytest availability** — Only the old `venv/` had pytest installed. New `.venv/` was missing test dependencies.

## Resolution

Since pytest lived only in the old complete venv (3.11), the fix was to run tests using that venv's Python directly:

```bash
/path/to/hermes-agent/venv/Scripts/python -m pytest tests/...
```

This restored 399/399 passes.

## Long-term Fix

Complete the `.venv` migration: install pytest and all test dependencies in `.venv/`, then fix `PYTHONPATH` to exclude the old `venv/` or unset it before running tests under the new venv.
