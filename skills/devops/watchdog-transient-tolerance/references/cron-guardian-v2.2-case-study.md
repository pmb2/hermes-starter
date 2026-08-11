# Cron Guardian v2.2 — Transient-Failure Tolerance Case Study (2026-07-31)

Session detail behind `watchdog-transient-tolerance`. Recorded from the Forge
pulse that implemented and verified the fix.

## Incident Timeline

| Time (ET) | Event |
|-----------|-------|
| 22:30:48 | Tier-1 health check (`GET api.deepseek.com/v1/models`) fails with `getaddrinfo failed` — transient DNS resolution blip |
| 22:30:48 | Guardian v2.1 pauses 54/61 enabled jobs (only 7 left running); fleet dark |
| 22:45:07 | Next 15-min cycle: endpoint reachable (HTTP 401 = up, auth-only) → resumed 54, repaired 13 errored, recovery_count=7 |

The API never went down. A single resolver hiccup cost the fleet 15 minutes
of dark plus gap-report/repair churn. Root cause: `cmd_watch()` called
`check_model_health()` ONCE and paused on the first `not healthy` — no
retry, no error classification, no tolerance window.

## The Fix (v2.2, live at `AppData/Local/hermes/scripts/cron-guardian.py`)

Three changes to `cmd_watch()`:

1. **In-cycle retry** — if `not healthy and is_transient_tier1(detail)`:
   `time.sleep(5)`, re-check. Retry success (`healthy and has_credits`) →
   reset streak, `last_action = "transient error self-healed on retry"`,
   return 0.
2. **Tolerance window** — if still failing transiently: `streak =
   state["transient_streak"] + 1`; while `streak < TRANSIENT_TOLERANCE_CYCLES`
   (2): update state, log "NOT pausing fleet (recheck next cycle)", return 1.
   Only on `streak >= 2` does execution fall through to the pause path.
3. **Exit-code correction** — `return 0 if (healthy and has_credits) else 1`.
   v2.1's `return 0 if healthy else 1` returned 0 on credits-down cycles
   (healthy=True, has_credits=False) — i.e. reported "ok" on the exact
   cycle that paused the fleet.

Supporting additions: `TRANSIENT_MARKERS` list + `is_transient_tier1()`
helper; `"transient_streak": 0` in the default state dict; reset of the
streak in the healthy branch.

## State File Evolution

`~/AppData/Local/hermes/cron/guardian_state.json` after the incident:
`was_paused: false`, `recovery_count: 7`, `last_down_at: 2026-07-31T02:30:48Z`,
`last_healthy_at: 2026-07-31T02:45:07Z`. Steady-state runs show
`last_action: "no action (healthy)"` and NO `transient_streak` field (it
only appears while a transient streak is in progress).

## Verification Results (behavioral test)

4 phases, all passed on the patched script:
1. Single blip → rc=1, streak=1, `was_paused=False`, test job still enabled
2. 2nd transient → pause fires, infra job (NEVER_PAUSE) untouched
3. Recovery → rc=0, resumed, streak=0, recovery_count incremented
4. HTTP 401 (non-transient) → immediate pause, rc=1 (after exit-code fix)

## Environment Notes

- **Live vs stale copy**: live guardian is `cron-guardian.py` (v2.2) at
  `AppData/Local/hermes/scripts/`; a stale v1.0 (different architecture —
  `hermes cron` CLI subprocesses) sits at `~/.hermes/scripts/cron-guardian.py`
  and is dead code. Confirm liveness via `guardian_state.json` location and
  `last_check_at` matching the cron job's `Last run` timestamp.
- **`git -C <msys-path>` fails in this git-bash** — silent "not a git
  repository" or `cannot change to '<path>'` while `ls`/`cd` work. Use
  `cd` + plain git.
- The guardian cron job (`31f8ee7d78c7`, `*/15 * * * *`, no-agent, script
  `cron-guardian.py`) shows "Last run: ok" even on down-cycles that exit 1 —
  exit 1 is expected/tolerated on degraded cycles.
