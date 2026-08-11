# Pipeline Health Overview

Captures systemic pipeline health issues discovered during the July 2026 morning briefing cycles. Separate from the keyword routing gaps in `references/auto-action-gaps.md`.

## Issue 1: Config Drift on Unpinned Cron Jobs

**Discovered:** 2026-07-13 morning briefing

**Symptom:** `cyber-intel-scanner` (ID `8b5378a8abe8`) fails silently:

```
RuntimeError: Skipped to prevent unintended spend: global inference config drifted since
this job was created (model 'deepseek-v4-flash' -> 'kimi-k2.7-code'), and this job is
unpinned. No inference call was made.
```

**Root Cause:** The global inference provider/model changed (snapshot switch, provider migration, etc.) leaving the job's `model_snapshot`/`provider_snapshot` stale. Hermes blocks execution to prevent unexpected billing.

**Detection Method:**
1. Check cron job `last_status` in `cron/jobs.json` — if `"error"`, inspect `last_error`
2. Error string contains `"config drifted"` and `"unpinned"`
3. The job's `model_snapshot` differs from current global model

**Fix:** Pin the job explicitly:
```
hermes cron update 8b5378a8abe8 --provider opencode-go --model deepseek-v4-flash
```
Or use the JSON path: update the `jobs.json` entry to include explicit `model` and `provider` fields (not just snapshots).

**Prevention:** Any no_agent script cron job with a `model_snapshot`/`provider_snapshot` from auto-capture should be pinned. After a global config migration, audit all cron jobs for drift errors.

## Issue 2: auto_action_handler.py UnboundLocalError

**Discovered:** 2026-07-13 morning briefing (last successful run was Jul 10)

**Symptom:** Central auto-action handler crashes with:
```
UnboundLocalError: cannot access local variable 'headline' where it is not associated with a value
  File "...auto_action_handler.py", line 420, in execute_actions
    result = action_enhance_config(headline, finding)
```

**Root Cause:** The `execute_actions()` function in `auto_action_handler.py` has three branches that reference a variable `headline` that is never defined in the function's scope:

```python
def execute_actions(actions):
    results = []
    for action in actions:
        action_type = action[0]
        target = action[1]
        finding = action[2]
        ...
        elif action_type == "enhance_soul":
            result = action_enhance_soul(headline, finding)  # BUG: headline undefined
        elif action_type == "enhance_skill":
            result = action_enhance_skill(headline, finding)  # BUG: headline undefined
        elif action_type == "enhance_config":
            result = action_enhance_config(headline, finding)  # BUG: headline undefined
```

**Impact:** The handler crashes mid-cycle, losing ALL actions for that batch (not just the config-related one). Other pending actions (clones, paper downloads, research notes) are also lost because the exception propagates out of the loop before execution saves state.

**Condition to trigger:** A finding with `change_type == "config"` and `tier == 1` must be present in any of the finding sources (cyber, PIM, AI ecosystem). The `analyze_scored_finding()` router produces `("enhance_config", headline, finding)` tuples when:
- `change_type == "config"` and `cat in ("hermes_security", "system_config")`
- Any cyber finding with `change_type == "config"` (breach data with tier 1)

**Detection:**
1. Check `cron/jobs.json` for job ID `9843a00bd786` — last_status should be "error"
2. `last_error` contains `UnboundLocalError`
3. Compare `auto_action_state.json` mtime vs `cyber_intel_findings.json` mtime — if state is older, handler hasn't successfully completed since the findings were produced

## Issue 3: Missing Cron Entry for cyber_auto_actions.py

**Discovered:** 2026-07-13 morning briefing

**Symptom:** `cyber_actions_log.jsonl` and `cyber_auto_action_state.json` have stale timestamps (last modified Jul 10 at 23:25 ET). Cyber-specific actions (hardening notes, IP blocklisting, PoC cloning) never execute even when findings exist.

**Root Cause:** `cyber_auto_actions.py` was never registered as a cron job. It exists at `~/AppData/Local/hermes/scripts/cyber_auto_actions.py` but has no entry in `cron/jobs.json`. The pipeline architecture diagram in the skill assumed it runs at 07:00 but no one created the cron entry.

**Impact:** ALL cyber-specific hardening actions are dead code:
- PoC exploit repos are never cloned
- Malicious IPs are never blocklisted
- Hardening notes from cyber findings are never generated (breach/leak Tier 1 findings only get `intel_logged` via the central handler)

**Fix:** Create a cron entry:
```json
{
  "id": "(auto-generate)",
  "name": "cyber-auto-actions",
  "prompt": "",
  "script": "cyber_auto_actions.py",
  "no_agent": true,
  "schedule": { "kind": "cron", "expr": "0 7 * * *", "display": "0 7 * * *" },
  "enabled": true,
  "deliver": "origin",
  "origin": { "platform": "discord", "chat_id": "<discord-channel-id>",
    "chat_name": "Automation Team / #cyber / red team",
    "thread_id": "<discord-channel-id>" }
}
```

Also pin provider/model to prevent config drift (see Issue 1).

## Verification Methodology

When producing a morning briefing, use this checklist:

### 1. Verify deep-spider-sweep ran today
```
ls -la ~/deep-spider/results/*2026-07-13*  # Check for today's files
```
Alternatively: check `cron/jobs.json` for ID `9c3bcff4956e` → `last_run_at` should be today

### 2. Verify cyber-intel-scanner ran
```
cat ~/trumpian-accounting-kb/monitoring/findings/cyber_intel_scan_state.json | python -m json.tool
stat ~/trumpian-accounting-kb/monitoring/findings/cyber_intel_findings.json  # mtime should be today
```
Check `cron/jobs.json` for ID `8b5378a8abe8` → `last_status` must be "ok"

### 3. Verify auto-action handler(s) ran
```
stat ~/trumpian-accounting-kb/monitoring/findings/cyber_actions_log.jsonl  # mtime = when it last appended
stat ~/trumpian-accounting-kb/monitoring/findings/cyber_auto_action_state.json  # cyber-specific state
stat ~/trumpian-accounting-kb/monitoring/findings/auto_action_state.json  # central handler state
```
Compare all three to `cyber_intel_findings.json` mtime. If state files are older, handler missed this cycle.
