# Hermes Agent — Forge Pulse Reference Notes

Durable facts for engineering pulses against the hermes-agent repo
(`${USER_HOME}\AppData\Local\hermes\hermes-agent`). Transient numbers
(divergence counts, patch inventory, pending restores) belong in
`PULSE.md`, NOT here — this file holds only facts stable across cycles.

## Test interpreter (verified Aug 4 2026)

- Repo `venv/` has NO pytest: `./venv/Scripts/python.exe -m pytest` →
  `No module named pytest`.
- Base Python311 — `${USER_HOME}/AppData/Local/Programs/Python/Python311/python`
  (on PATH as `python`) — has pytest 9.0.3 and runs the repo suites.
- Run targeted suites: `python -m pytest tests/<target> -q -p no:cacheprovider`
  (e.g. `tests/cron/`, `tests/tools/test_terminal_tool.py`).

## Pre-existing Windows failures (do NOT re-investigate)

- `tests/cron/test_file_permissions.py` — POSIX chmod mode asserts
  (0o700/0o600) fail on Windows: `os.stat` reports 0o777/0o666. 7 failures,
  permanent on Windows, unrelated to any change.

## File-location map (upstream relocations — don't grep stale paths)

- CDP override resolution lives in `tools/browser_tool.py`:
  `_resolve_cdp_override` (:434), `_get_cdp_override_raw` (:497),
  `_get_cdp_override` (:536). Tests: `tests/tools/test_browser_cdp_override.py`
  (15 tests). NOT in `hermes_cli/web_server.py`.
- Gateway slash commands: `hermes_cli/slash_exec.py` (renamed from
  `slash_commands.py`).
- Browser CDP tool: `hermes_cli/tools/browser_cdp_tool.py`.
- Approval allowlist lazy-init site: `tools/approval.py` — module-level
  `load_permanent_allowlist()` call (~:4374 after Aug 2026 upstream commits).
- Dev sandbox installer fixtures: upstream `feat(dev-sandbox)` wave lands in
  `dev-sandbox/` (fake installer / fake main / git clones).

## Patch-lost audit checklist (use after any rebase/reset)

1. `git fetch origin` FIRST — a stale origin ref makes divergence and
   "is it lost?" answers wrong (standing rule: always fetch before measuring).
2. Whole-tree case-insensitive grep for the feature identifiers:
   `grep -rli "<name>" --include="*.py" .`
3. Cross-check `search_files` negatives with terminal grep — the tool can
   return `total_count: 0` on alternation patterns when matches exist
   (verified Aug 4 2026).
4. Run the patch's own test file — green tests = feature present, not lost.
5. To restore a genuinely lost patch: `git cat-file -t <sha>` (object still
   valid?) then cherry-pick / re-apply from the object DB.

## Windows test-execution notes

- 380+ tests in `tests/cron/` + `test_terminal_tool.py` pass with the 7
  chmod failures above; runtime ~67s.
- The NUL-byte binary-scan regression suite is
  `tests/cron/test_lifecycle_guard_binary_scan.py` (4 tests, ~0.4s) — guards
  `cron/lifecycle_guard.py` + `tools/terminal_tool.py` `_read_local_script_text`.
