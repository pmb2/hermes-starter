# Runtime interpreter dep diagnosis — worked example (admin Scout, Aug 2026)

## Symptom

A weekly `no-agent` cron job (`run-admin-scout.py`, "admin Scout — Weekly
trading signals") failed every run with:
```
ModuleNotFoundError: No module named 'pandas'
```
The traceback pointed at a repo module (`eddie_sec.py -> import pandas`).
`last_status` was `error: Script exited with code 1`.

The failure date (Aug 10 14:52) matched the window when the hermes venv was
recreated on upgrade (which wipes deps) — so the initial hypothesis was the
known venv-recreation dep wipe.

## The trap: checking the wrong interpreter

1. `ls .../hermes-agent/venv/Scripts/python.exe` existed and `import pandas`
   returned `OK 3.0.5` — naive check said "already fixed."
2. But `uv pip install --python <venv> pandas` flatly refused:
   `No virtual environment or system Python installation found for path`.
   uv does not recognize the bundled tree as a venv.
3. The job record showed `script: run-admin-scout.py`, `python: null` — no
   interpreter is stored in the job; the runner resolves it.

## Root cause

Hermes cron runs no-agent scripts under the **bundled `.hermes-runtime`
cpython**, NOT the venv:

```
~/AppData/Local/hermes/hermes-agent/.hermes-runtime/python/
  generation-<hash>/cpython-3.11-windows-x86_64-none/python.exe
```

That interpreter has its own isolated `site-packages`. pandas was present in
the venv but the *runtime* interpreter (which the cron actually executes)
had been stripped by the upgrade recreation.

## Verification

Live-run the failing script with the discovered runtime interpreter:
```bash
RT=$(ls -d ${HERMES_HOME}/hermes-agent/.hermes-runtime/python/generation-*/*/python.exe | head -1)
cd ${HERMES_HOME}/scripts && timeout 120 "$RT" -u run-admin-scout.py
```
Expected healthy output: `Scout admin completed: 5 signals produced` and
`EXIT=0`. (In this session the recovery pass had already restored pandas to
the runtime interpreter before inspection, so the live run passed clean —
the right move is to re-verify live rather than re-declare RED on a stale
error timestamp.)

## Rules distilled

- Deps for a cron no-agent script must exist in the **`.hermes-runtime`
  interpreter**, not just the venv.
- Install with `"$RT" -m pip install <pkg>` (its own pip), not
  `uv pip install --python <venv>`.
- A job `error` dated before a recovery/upgrade window may already be fixed —
  live-run the script with `$RT` before flagging it RED in a health pulse.