# Daily Command Brief Compilation — Practical Execution

> Step-by-step for the CoS morning brief cron. This supplements the
> `references/summarization-layer.md` architecture doc with the actual
> execution steps, discovered gaps, and cross-reference heuristics.

## Signals to Run This

- Cron job `daily-command-brief` (Schedule: `0 11 * * *`)
- the operator asks "what's the status?" or "compile the brief"
- Any CoS channel scan that needs to produce a consolidated report

## Step 1: Run the Auto-Fill Wrapper FIRST

The `daily_brief_auto.py` script in `scripts/` generates deterministic
fields from local data (priorities config, open_loops.py, last filled brief):

```bash
cd ${HERMES_HOME}/scripts
python daily_brief_auto.py
```

This writes to:
`${MY_REPOS}\Documents\github\_project\06-reports\daily-briefs\<date>.md`

**What it fills:** priorities, open loops (OL-IDs), pipeline value, date.
**What it leaves for the agent:** cash flow (revenue/expenses/runway),
opportunities, risks/blockers, delegated agent work, recommended decisions.

Read the output file and also check `open_loops.py list` for the current
loop state.

## Step 2: Query the Relay for 24h of Channel Events

Use `buzz_scan_channels.py` (or write a custom script per `brief_scan.py`):

```python
# Connect to ws://localhost:3000
# NIP-42 AUTH with operator key
# Query kind 9 + kind 1 events, since=NOW-86400, limit=800-1000
```

The relay is at `ws://localhost:3000` (local Postgres-backed relay).

**Council channels to scan** (defined in `buzz_channels.json`):
- P0: #admin, #development, #engineering, #revenue, #supervisor
- P1: #cybersecurity, #research, #osint, #legal, #finance, #investing, #betting, #sports
- P2: #health, #content, #media, #operations, #market-lead, #career, #tax
- P3: #skills, #docs, #testing, #releases, #monitoring, #automation

## Step 3: Council Lead Channel Gap — No "Daily Report" Summaries Exist

**📌 Critical finding from production (2026-08-11):** Council leads
(revenue, finance, intelligence, legal, health, operations, tax, investing)
do NOT post "Daily Report — {role} — {date}" format summaries in their
channels. The `buzz_scan_channels.py` "Daily Report" search returns zero
matches in 24h.

**What does exist:** Pulse agents post structured reports to their OWN
channels at their pulse intervals (every 4h or 6h):

| Channel | Agent | Report Format | Frequency |
|---------|-------|---------------|-----------|
| #engineering | dev-lead | Forge Pulse | every 4h |
| #devops | qa-lead | Sentry Pulse | every 4h |
| #integrations | integration-lead | Weaver Pulse | every 6h |
| #cybersecurity | threat-lead | Cyber Morning Briefing | every 12h |
| #sports | odds-lead | Sharp Betting Scan | every 4h |
| #skills | skills-lead | Skillmate Pulse | every 6h |
| #docs | docs-lead | Scribe Pulse | every 6h |
| #monitoring | pulse | the operator's Pulse / Live Scan | every 4h |

**Extract from pulse reports instead of dedicated lead summaries.**
Each pulse report contains: a RECAP section (✅ completed items), the
current state, and metrics. Parse these for the brief.

**If a council channel has zero messages in 24h:** flag it as a gap.
The brief should note "no lead report" for that domain.

## Step 4: Extract Data from Pulse Reports

For each pulse report found, extract:

**Forge (#engineering):**
- Divergence: `{N} behind / {M} ahead` — track velocity (delta/h)
- Push status: 403 blocked? Alternate remote needed?
- Stack integrity: commits intact?
- WIP fixes: any uncommitted changes found?

**Sentry (#devops):**
- Regression baseline: `{N} passed / {M} skipped` in {time}s
- Merge conflicts: count, which files, unchanged?
- NUL/0-byte artifacts: regenerated?

**Weaver (#integrations):**
- Bridge/fleet health
- MCP server status
- Integration fixes

**Cyber (#cybersecurity):**
- CISA KEV catalog freshness
- Auto-action handler status
- New intel or zero overnight

**Sports betting (#sports):**
- Betting record: `W-L (win%), +/-Xu, +/-X% return`
- Pending bets: 0 or N
- New picks: candidates + odds

**Pulse (#monitoring):**
- Git activity: commits in window, uncommitted work
- Blogwatcher: trending topics
- Cross-pulse digest highlights
- Crons: errors, recoveries
- Disk: capacity %, docker cleanup

**Skillmate (#skills):**
- SKILL.md audit: count, YAML errors, missing triggers
- Large skills flagged (>88KB)
- Collisions: gstack triad, etc.

**Scribe (#docs):**
- CHANGELOG status: gap-filled? Upstream version?
- Library health: coverage, staleness
- Release notes: current?

## Step 5: Cross-Reference Rules

Apply these to the extracted data before compiling:

### 1. Two leads mentioning same topic → flag as cross-domain connection
Example: Forge (divergence) + Sentry (merge conflicts) = same engineering
backlog root. Flag as "both Forge and Sentry tag the divergence/rebase."

### 2. Open loop with no update in 48h → flag as stale
Check OL-IDs from `open_loops.py list`. If the loop hasn't been touched
in the channel data and the deadline is >48h past, escalate.

### 3. Decision requested yesterday still not made → escalate
If yesterday's brief recommended a decision and no evidence of action
exists in the channel data (no @mentions, no discussion, no resolution),
escalate with "Requested yesterday — still undecided."

## Step 6: Compile the Brief

Format uses the `discord-report-format` skill rules. Sections:

```
# Daily Command Brief — {Day Mon DD YYYY}

## 🔴 Needs the operator
- {domain}: {decision} (deadline: {date})
  Escalate overdue decisions, push-403 blocks, OL loops past deadline.

## 🟡 Open Loops
- {domain}: {item} (owner: {agent}, ETA: {date})
  Include: divergence, merge conflicts, stale merges, repo-sync decisions.

## 🟢 Completed
- {domain}: {item}
  Per lead: one line per completed item from pulse report RECAP sections.

## 💰 Cash Flow
- Pipeline (active): ${value}
- Revenue MTD: ${value} or "no lead report" if finance/revenue channel silent
- Flag: "finance + revenue leads posted nothing" if applicable.

## 📊 Pulse
- Bridge: ✅ (PID {N}) or ❌
- OmniRoute: ✅ (healthz ok) or ❌
- Crons: {green}/{total} ok · {N} not yet due · ⚠️ {N} errored last run

## 📌 Top 3 Priorities
(From auto-fill — unchanged)

## 🔍 Cross-References
Connection entries from Step 5.
```

**Delete sections with no data.** Do not write "nothing new" or "no changes."

## Step 7: Fill Agent-Side Fields in the Template

The auto-filled brief has placeholders for:
- `${{amount}}` → Revenue MTD, Expenses MTD (from finance lead or billing)
- `{{days}}` → Cash runway
- `{{name}}` + `{{brief description}}` → New opportunities
- `{{critical risk}}` → Risks/blockers
- `{{lead}}`, `{{task}}`, `{{status}}`, `{{date}}` → Delegated agent work
- `{{decision topic}}` → Recommended decisions

If no data exists for a section, **delete it entirely** rather than
leaving placeholders.

## Infrastructure Checks

Run these in parallel with the relay query:

```bash
# Bridge
cat ${HERMES_HOME}/logs/buzz_bridge.pid
tasklist /FI "PID eq $(cat ${HERMES_HOME}/logs/buzz_bridge.pid)"

# OmniRoute
curl -s http://localhost:20128/healthz

# Crons
cd ${HERMES_HOME} && hermes cron list
# Count: active=ok, active=error, active=(no last run)
```

## Pitfalls

### Leads don't post "Daily Report" → don't assume they will
This is the default state, not a bug. Extract from pulse reports.
The summarization layer architecture doc describes the ideal (lead
summaries), but in practice only pulse agents post regularly.

### Finance and revenue channels are often silent
Cash-flow data must be carried forward from the pipeline baseline or
last known pipeline value. The `daily_brief_auto.py` wrapper handles
this via `_pipeline_flag()`.

### Self-healing claims of recovery may be stale
Self-healing pulse reports may claim a cron recovered, but the actual
cron run may still fail. Always verify the cron's last-run status
directly with `hermes cron list` rather than trusting a pulse report.

### Cron names differ between pulse reports and cron list
Pulse agents may refer to a cron by a short name ("Stock Sniffer")
while the cron list has the full name ("Stock Sniffer: Intraday
Trigger Watch"). Match by substring or description.