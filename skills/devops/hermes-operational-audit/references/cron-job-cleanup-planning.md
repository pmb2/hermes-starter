# Cron Job Cleanup & Consolidation Planning

A structured methodology for taking a full cron job inventory, categorizing by importance and health, building a 4-phase cleanup/consolidation plan, saving to documentation, and reporting back.

## When to Use

- User asks "list all cron jobs and sort them"
- User asks for a cleanup/consolidation plan for cron jobs
- Monthly cron maintenance cycle
- After a major config change (provider migration, model switch) that invalidates many jobs
- When the number of cron jobs has grown unmanageable

## Workflow

### Step 1: Full Inventory

```python
cronjob(action='list')
```

This returns all jobs with their name, schedule, model, provider, delivery, last_run_at, last_status, enabled/disabled state, and error details.

### Step 2: Categorize by Status

Classify every job into one of:

| Status | Criteria | Color |
|--------|----------|-------|
| Working | `enabled=true` AND `last_status=ok` (or null for new) | 🟢 |
| Broken | `last_status=error` (or `last_delivery_error` non-null) | 🔴 |
| Disabled/Paused | `enabled=false` OR `paused_at` is set | ⚫ |

**Important:** A job can show `last_status: ok` but have a stale `last_error` from a previous run. Cross-check both fields. Also check `last_delivery_error` — a job may run fine but fail to deliver.

### Step 3: Sort by Importance

Within each status group, sort by business importance:

**Priority tiers (highest to lowest):**
1. **Revenue & Business-Critical** — C2C hunting, stock sniffers, sales pipelines, billing, cash-flow briefings
2. **Website Landlord & Land Agent** — site builds, rank checks, lead reports, tax roll refreshes, VA queues
3. **Health & Personal** — PBC medical watch, fitness accountability, project status checks
4. **Briefings & Intelligence** — morning briefs, pulsars, pulse scans, command briefs, council check-ins, weekly roundups, cyber intel
5. **Agent Pulse Council Team** — dev-lead, skills-lead, integration-lead, qa-lead, docs-lead pulses
6. **Legal Watchdog** — daily sweeps, compliance, background, reputation monitoring
7. **Infrastructure & System** — watchdogs, self-healers, PIM ingestion, log rotation, sync jobs, browser health

Within each tier, sub-sort by:
- Frequency (more frequent = higher priority)
- Delivery target (origin > discord > local — user-facing jobs matter more)
- Whether the user explicitly asked for it

### Step 4: Build the Cleanup Plan (4 Phases)

#### Phase 1: Cleanup — Delete Dead Weight

Identify jobs that are:
- **Superseded** — replaced by a newer, better version (e.g., Consolidated Morning Brief was replaced by Morning Brief 7:01)
- **Duplicate** — same intent, same script, different cadence (e.g., PIM every 3h AND every 4h)
- **Deprecated** — the system/process they monitored no longer exists (e.g., Kanban Pulse when Kanban is gone)
- **Campaign-paused** — the campaign/project was paused indefinitely (e.g., Data Scrub, PR Campaign, Options trading)

**Delete these outright.** No revival value.

#### Phase 2: Consolidation — Merge Redundant Jobs

Identify jobs that:
- **Share the same intent** — two pulse jobs that both do intelligence scans → merge into one
- **Share the same cadence** — three Legal Watchdog jobs all on Monday → merge into one Monday run
- **Share the same script** — two PIM ingestion jobs with different cadences → keep the faster one, delete the slower
- **Can be folded into a broader job** — Cyber Morning Briefing can be a section of Morning Brief 7:01 rather than a separate job

**Merge these into the canonical job.** Delete the redundant ones.

#### Phase 3: Improvement — Fix What's Broken

For each 🔴 broken job:
1. **Investigate the error** — run the script manually, check the error trace
2. **Fix the root cause** — bad path, missing dependency, config drift, quota exceeded
3. **Test** — re-run and verify it works
4. **Re-enable** — if it was disabled, unpause it

For 🟡 improvement opportunities:
- **Reduce cadence clutter** — if 8 jobs run every 15m, merge some into a single script
- **Add error logging** — no_agent scripts should log failures to a file
- **Standardize delivery targets** — move critical pulses from `local` to `origin`, keep infra watchdogs on `local`
- **Add `enabled_toolsets`** — reduce token overhead by restricting toolsets per job

#### Phase 4: Enhancement — Add Value

Identify what's missing:
- **Gap jobs** — what should be monitored but isn't? (e.g., Weekly Cron Health Report, MCP Server Health Pulse)
- **Enhancements to existing jobs** — `attach_to_session=true` for briefing jobs, `context_from` chaining for related jobs, model upgrades for reasoning-heavy jobs
- **Monitoring & alerting** — cron success rate dashboard, auto-pause on 3 consecutive failures, dedicated alert channel

### Step 5: Save to Documentation

```bash
# Save the plan to the the planning repo repo (or equivalent operations repo)
# The file should contain:
# 1. Executive summary: current vs target state
# 2. Phase 1: Delete — list of jobs to delete with reasons
# 3. Phase 2: Consolidate — merge targets with rationale
# 4. Phase 3: Improve — fix list with root causes
# 5. Phase 4: Enhance — new jobs and improvements
# 6. Target state table — before/after counts per category
# 7. Approval checklist — numbered items for the operator to sign off

# Example path:
# _project/06-reports/cron-cleanup-plan.md

# Commit:
git add <path>
git commit -m "Oracle: Cron job cleanup & consolidation plan — N→M jobs, 4-phase breakdown"
```

### Step 6: Report Back

Format the report for Discord delivery:

```
🟢 WORKING — REVENUE & BUSINESS-CRITICAL (X jobs)
[List top 5 with freq, model, status]

🟢 WORKING — BRIEFINGS & INTELLIGENCE (X jobs)
[Summary counts]

🔴 BROKEN (X jobs)
[List each with error]

⚫ DISABLED/PAUSED (X jobs)
[Summary by group]

📊 SUMMARY
| Category | Current | Target |
|----------|---------|--------|
| Working  | X       | Y      |
| Broken   | X       | 0      |
| Disabled | X       | Y      |
| **Total**| **X**   | **~Y** |

🎯 APPROVAL NEEDED
1. Delete N dead jobs — [link to plan]
2. Keep M paused — [ask]
3. Fix broken job — [detail]
...
```

## Execution Phase (verified 2026-08-11: 125 → 70 jobs)

The planning steps above produce the plan; execution has hard-won rules:

### Use the Guardian's mass-pause window as a cleanup opportunity
The Cron Guardian auto-pauses *all* LLM jobs when its health check fails (model 503/circuit-break). During that window the fleet is dark — execute deletions/consolidations THEN, before recovery auto-resumes everything. Check `cron/guardian_state.json` (`was_paused`, `last_action`) and `cronjob(action='list')` to confirm the pause is active and which jobs it covers.

### "Paused" vs "disabled" semantics — what comes back
- `state: paused` + `enabled: false` = **guardian-paused** (or user-paused). The guardian AUTO-RESUMES these (sets `enabled=true, state=scheduled`) on its next healthy cycle. **Pausing is NOT a stable terminal state** — if you want a job gone, `hermes cron remove`, don't just pause it.
- `state: scheduled` + `enabled: false` = **manually disabled** (shows as OFF). These are the truly dead jobs — safe to delete outright.
- The guardian only pauses `enabled && state == scheduled` jobs, and (after the 2026-08-11 fix) skips `no_agent` script jobs entirely.

### Backup before bulk deletion
```bash
mkdir -p ~/AppData/Local/hermes/cron/backups
cp ~/AppData/Local/hermes/cron/jobs.json ~/AppData/Local/hermes/cron/backups/jobs-YYYY-MM-DD-pre-audit.json
```
Full job configs (prompts, schedules, pins) restore from this file if a kill is wrong.

### Verify model pins against CURRENT provider reality
LLM jobs may be pinned to aliases that no longer resolve. Probe before trusting a pin:
- `deepseek/deepseek-v4-flash` → **400** (alias rejected by OmniRoute — silent fleet-wide failure)
- `yunwu/gpt-5.6-sol` → **503** (provider circuit-broken)
- `auto/best-fast` → **200** (verified working) — the safe repin target
Batch repin: `hermes cron edit <id> --provider custom:omniroute --model auto/best-fast`. Verify via `hermes cron run <id>` + `hermes cron runs <id>` showing `running`→`completed`, and NO `last_delivery_error`.

### LLM→script conversion (the big token lever)
Any cron whose prompt is deterministic or script-exists ("run radicle_sync.py", "check PID liveness", "rotate tor") should be `no_agent` with a `--script` — zero tokens, immune to model outages, and (2026-08-11 fix) never guardian-paused. Converted this session: radicle-github-sync, jailai-watchdog, CoS Pulse Check, tor-circuit-rotation (4 jobs).

### Pulse-merge economics
Per-agent pulses (dev-lead/qa-lead/integration-lead/docs-lead/skills-lead) each loading 3-4 heavyweight skills every 4-6h dominated cron token cost (~33% of ALL cron tokens). **Skill loading is the cost** — merge into one lean pulse with 1 skill. Merge rule beyond the >50%-overlap threshold: if N jobs each load large skills to do "quiet unless action", one consolidated job with a fraction of the skill-load does the same job.

### Pitfalls
- **Cron Watchdog LLM jobs are pure waste** — an LLM "detect & re-fire missed runs" job every 15m burns ~$1.40/14d + 4.2M input tokens while a `no_agent` script (safety-fallback-watchdog, every 5m) does it free. Watchdog/monitor jobs should ALWAYS be scripts, never LLM.
- **Deleting while paused is safe; deleting while healthy is also safe** — the risk window is the guardian RESUME: if you pause-but-keep a job you wanted gone, it comes back. Remove is the only permanent action.
- **`hermes cron remove` on a disabled job works fine** — no need to enable/pause first.

## User Preference Patterns (the operator's Setup)

From observed sessions (Aug 2026):

- **Sorting:** Working at top sorted by importance (revenue first), broken at bottom, disabled at very bottom
- **Delivery:** Report back to the origin channel, save full detail to a file, commit to the planning repo
- **Format:** Discord tables with emoji status indicators, bold headers, separators between sections
- **Decision style:** Options-first — present the plan with numbered approval items, let the operator pick
- **Cleanup appetite:** High — prefers deleting dead weight over keeping "just in case" jobs
- **Consolidation threshold:** If two jobs overlap in intent by >50%, merge them

## Pitfalls

- **`last_status: ok` doesn't mean healthy** — a job can report OK while having a stale error from a previous run or a delivery failure. Check `last_error` AND `last_delivery_error`.
- **Disabled jobs still count toward the total** — `cronjob(action='list')` returns ALL jobs, including disabled/paused. Filter by `enabled` and `paused_at` for the real active count.
- **Jobs can be "new, never ran"** — `last_status: null` and `last_run_at: null` means the job was created but hasn't hit its first scheduled window yet. Don't flag these as broken.
- **Some disabled jobs have runnable repos** — e.g., ai-sharp jobs are disabled because the repo moved, but the repo exists at a different path. Check actual filesystem paths before declaring a job dead.
- **Script errors may be transient** — a script that errored once might work when re-run. Test before adding to the "broken" list.
- **Don't delete jobs the operator might revive** — keep paused jobs with a clear revival condition. Only delete jobs that are truly superseded or duplicate.
- **The plan is a proposal, not an execution order** — the operator needs to approve before any destructive action. Present options, don't auto-execute.