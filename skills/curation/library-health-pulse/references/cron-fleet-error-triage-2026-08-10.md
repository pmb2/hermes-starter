# Cron Fleet Error Triage — Addendum 2026-08-10

Extends `references/cron-fleet-error-triage-2026-08-07.md` (the base playbook: drift spend-guard, stale `last_error`, provider-side 429/402/502/503). Three new error classes discovered during the Aug 10 dream cycle.

## 4. `enabled: false` — the disabled-job class (invisible to `hermes cron list`)

The dream-cycle inventory flags jobs with stale `last_error` as "failures". A big chunk of those are jobs with **`enabled: false`** in jobs.json — deliberately disabled (cost control, superseded by a newer engine, user pause) — NOT broken.

**Diagnostic (do this before treating any flagged job as broken):**
```bash
python -c "
import json; from pathlib import Path
jobs = json.loads(Path.home().joinpath('AppData/Local/hermes/cron/jobs.json').read_text(encoding='utf-8-sig'))
jobs = jobs if isinstance(jobs, list) else jobs.get('jobs', jobs)
print('total:', len(jobs), '| enabled:', sum(1 for j in jobs if j.get('enabled')), '| disabled:', sum(1 for j in jobs if not j.get('enabled')))
"
```
- **`hermes cron list` shows ONLY enabled/active jobs** — a disabled job appears nowhere (not `[paused]`, not `[error]`, just absent) and its `next_run_at` freezes in the past. Absence from the list + `enabled: false` in jobs.json = intentional disablement, not a scheduler bug.
- `state` stays `scheduled` and `last_error` keeps its old value — both mislead. Check `enabled` first.
- **Do NOT re-enable autonomously.** Re-enabling revenue jobs (picks, reminders, scrubs) is a spend/business decision. Report as "needs user decision: re-enable + re-pin, or retire" with a table of jobs. Recovery when approved: `hermes cron edit <id> --enabled true` + re-pin to current global (`custom:omniroute` / `hermes/workhorse`).
- Real case Aug 10 2026: 14 disabled jobs (ai-sharp ×2, options-daily-picks, daily-picks-generation, daily-strategy-bots, finance-agent ×3, Data Scrub ×2, PR Campaign, Auto Skip Trace, YouTube Archive, hermes-nightly-watchdog) — all flagged by the dream script as "HTTP 429 failures"; all `enabled: false` since early July with stale opencode.ai quota errors (that quota resets monthly — the 429s were history).

## 5. Scheduler catch-up tick — odd run times, and when drift-guard errors are LIVE

When the scheduler finds overdue jobs (PC asleep/off at the scheduled slot), it re-ticks them in a batch (real case: 14:52 ET catch-up ran PBC Watch, admin Scout, land-agent, and all pulses at once). Consequences:
- A `last_run_at` far from the scheduled time is catch-up, not a bug.
- A job that catches up and hits the **drift spend-guard is a LIVE break** — the guard blocks every tick. The error text names the job id and the exact pin command; pin immediately via `hermes cron edit <id> --provider custom:omniroute --model <original-quality-model>` (keep the ORIGINAL model for quality jobs, per the never-downgrade rule), verify in jobs.json, then `hermes cron run <id>` to clear the missed run (delivers to origin — that's the job's designed output).
- A catch-up that SUCCEEDS clears the stale `last_error` — re-poll jobs.json before re-fixing anything flagged older than the catch-up batch (Aug 10 2026: land-agent, jailai-status, the operator's Pulse all showed `ok` after the 14:52 catch-up).
- Provider-recovery fallback may engage during catch-up runs ("GPT-5.6 Sol ... having issues — switching models"): the job can still report "succeeded" while running on gemini-3-flash/gemma4:12b. Treat that warning as a provider-health signal (OmniRoute flaky), not a job failure.

## 6. Hermes managed-runtime venv recreation wipes no_agent script deps

`~/AppData/Local/hermes/hermes-agent/venv/` is a Hermes-managed runtime python (resolves into `.hermes-runtime/python/generation-<ts>-<hash>/`). **Upgrades recreate it, silently wiping every package installed for no_agent cron scripts** → `ModuleNotFoundError` crashes (real case Aug 10 2026: admin Scout crashed on `pandas` after an upgrade).

**Fix (one pass, not whack-a-mole):** install the project's full `requirements.txt` into the venv. The venv has NO pip (`python -m pip` → "No module named pip") — use uv:
```bash
uv pip install --python "${USER_HOME}/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe" -r <project>/requirements.txt
```
Then verify by running the script directly with a NATIVE Windows path — the `~/...` MSYS form fails with the `C:\c\` doubled-drive error (same class as land-agent's old bug):
```bash
"${USER_HOME}/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe" "${USER_HOME}/AppData/Local/hermes/scripts/run-<script>.py"
```
TextBlob/NLTK-class deps may also need corpus downloads at first real use — check runtime behavior, not just import success.
