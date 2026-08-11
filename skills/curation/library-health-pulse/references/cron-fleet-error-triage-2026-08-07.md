# Cron Fleet Error Triage — Dream Cycle 2026-08-07

Session playbook for the error classes the dream-cycle inventory script flags. Produced Aug 7 2026 while triaging 26 errored jobs.

## 1. Config-drift spend guard (error #44585) — most actionable class

**Signature:** `RuntimeError: Skipped to prevent unintended spend: global inference config drifted since this job was created (provider 'deepseek' -> 'custom'; model 'deepseek-v4-flash' -> 'gpt-5.6-sol'), and this job is unpinned. No inference call was made. To run on the new config, pin it explicitly: ... (or pin the original values to keep them). See #44585.`

**Nature:** deliberate spend-protection guard, not a crash. Hits ALL unpinned jobs at once when `model.default` changes — treat as one fleet-wide incident, not N independent bugs. `last_run_at` still updates (the scheduler tick ran; the inference call was skipped).

**Fix — pin via the CLI, not the cronjob tool.** The agent's `cronjob` tool cannot set provider/model. Only `hermes cron edit` can:

```bash
grep -A6 '^model:' ~/AppData/Local/hermes/config.yaml   # read current global config first
hermes cron edit <job_id> --provider custom:omniroute --model gpt-5.6-sol
```

Pin to the CURRENT global values so jobs run on the new config (matches the "never downgrade" rule). Drift direction varies per job — some drift from `auto/best-coding`, others from a concrete provider/model pair; the error text states each job's exact drift.

**Verify via jobs.json, NOT `hermes cron list`:** `cron list` still shows the OLD `last_error` (state-at-run-time) even after a successful pin. Authoritative check:

```bash
python -c "
import json; from pathlib import Path
jobs = json.loads(Path.home().joinpath('AppData/Local/hermes/cron/jobs.json').read_text(encoding='utf-8-sig'))
for j in (jobs if isinstance(jobs, list) else jobs.get('jobs', jobs)):
    if str(j.get('id',''))[:12] in ('<id1>','<id2>'):
        print(j.get('name'), '| model:', j.get('model'), '| provider:', j.get('provider'))
"
```

Confirmed pin = both fields set to the new values. Next scheduled tick runs normally — no manual re-fire needed.

**Real case:** 5 jobs (nationwide-daily-build, radicle-github-sync, legal-data-privacy-weekly, Fitness accountability, jailai-status) pinned in one pass, all verified in jobs.json.

## 2. Stale `last_error` vs. live break — verify before re-fixing

A cron job's `last_error` is state-at-run-time, not current state. If a maintenance pass fixed the wrapper AFTER the last failed run, the error persists in the record while the job is actually healthy. Before re-fixing a flagged script-path job:

1. Read the job's current `script` field in `~/AppData/Local/hermes/cron/jobs.json` — does it already point at the `.py` wrapper?
2. Check the `.sh` mtime — recreated today = fix likely landed; error predates it.
3. Test cheaply: `python <wrapper>.py` exits 0, `bash -n <script>.sh` passes, referenced helpers (e.g. `deep_scoring.py`) exist.

**Real case:** `AI Sharp Data Auto-Commit` showed code 127 (`ai-sharp-data-commit.sh: No such file or directory`) and `land-agent-weekly-taxroll-refresh` showed the `C:\c\` doubled-drive error — both from a 03:23 run, both fixed by 03:41–03:54 maintenance the same day. Correct action was "verified fixed", not re-applying the fix.

## 3. Provider-side errors (429/402/502/503) — NOT code fixes

| Class | Meaning | Action |
|-------|---------|--------|
| HTTP 429 "Monthly usage limit reached. Resets in N days" | opencode.ai account quota exhausted | Top up / enable usage from available balance — user action |
| HTTP 402 "Insufficient Balance" | tor exit-node provider unfunded | User funding action |
| HTTP 502 "Request dropped after exceeding the local rate-limit queue budget maxWaitMs" | cliproxyapi/grok-4.5 rate-limit queue | Transient — monitor; stagger job start times if recurring |
| HTTP 503 "all upstream accounts are inactive" | provider aggregate down | Transient — monitor |
| TimeoutError "idle for 600s (limit 600s)" | LLM job waiting on API response | Monitor; may resolve when provider recovers |
| "Script timed out after 3600s" | long-running no_agent script | Review script for chunking/parallelism |

Report these as "needs user action" (funding) or "transient — monitor", not as code bugs. Distinguish them from classes 1 and 2, which ARE fixable in-session.
