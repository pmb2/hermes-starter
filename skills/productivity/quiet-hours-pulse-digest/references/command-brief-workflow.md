# Daily Command Brief — Council Lead Query Workflow

## Purpose
Gather live council lead status from MCP services and git repos to populate the Daily Command Brief (7-section template). Run as the Morning Brief cron (07:01 AM EST) or on demand.

## MCP Queries — Live Council Lead Status

Query these in parallel where possible:

### Revenue / BizDev Lead
```python
mcp_bizdev_agent_bizdev_dashboard()
# Returns: total_target_companies, total_contacts, decision_makers,
#          active_contracts, total_outreach, pipeline_value_min/max,
#          contracts_won, contracts_lost
```

Key signals:
- `total_outreach == 0` + targets > 30 → pipeline stall, flag as risk
- `contracts_won == 0` for >2 weeks → conversion gap
- `pipeline_value` not growing between briefs → inactive pipeline

### Job Agent (Recruiter Leads)
```python
mcp_job_agent_heartbeat()
# Returns: status, timestamp (confirms service is live)
```

Cross-reference recruiter emails from the daily digest for cash-gen leads.

### Intelligence / Brain Health
```python
mcp_gbrain_get_recent_salience(days=2, limit=15)
# Returns recent highly-salient pages — use to detect fresh activity

mcp_gbrain_get_health()
# Returns: page_count, embed_coverage, brain_score, orphan_pages, etc.
```

### Technology Lead (Git Activity)

Dynamic repo scan — covers ALL repos, not a hardcoded list:

```bash
# Today's commits across all repos
TODAY=$(date +%Y-%m-%d)
for d in ${MY_REPOS}/*/; do
  repo=$(basename "$d")
  if git -C "$d" rev-parse --git-dir >/dev/null 2>&1; then
    commits=$(git -C "$d" log --oneline --since="${TODAY}T00:00:00" 2>/dev/null | wc -l)
    if [ "$commits" -gt "0" ]; then
      echo "$repo: $commits commits today"
      git -C "$d" log --oneline --since="${TODAY}T00:00:00" --format="%ai %an: %s" 2>/dev/null | head -10
    fi
  fi
done
```

Check frozen P0 repos for days-since-last-commit:
```bash
for repo in bookends constructManage model-gateway; do
  last=$(git -C "${MY_REPOS}/$repo" log -1 --format="%as %s" 2>/dev/null)
  echo "$repo: $last"
done
```

## Prior Brief Continuity

Read yesterday's brief before compiling today's:
```bash
read_file "${MY_REPOS}/Documents/github/_project/06-reports/daily-briefs/YYYY-MM-DD.md"
```

Carry forward:
- Financial data (Revenue MTD, Expenses MTD, Pipeline, Runway) — update only if new data appears
- Open loop status (increment overdue days, escalate framing)
- Agent task baselines (track status changes day-over-day)
- Escalation counter for repeated findings

## Brief Compilation

### Write-file approach (preferred for rich briefs with 5+ agent statuses)

Write the markdown directly using all 7 sections. The `daily_brief.py` CLI's single `--agent-task` flag can't represent the full delegated-agent table.

### daily_brief.py CLI (use when data is sparse or as a baseline)

```bash
cd ${MY_REPOS}/_project
python scripts/daily_brief.py \
    --priority-1 "..." --priority-2 "..." --priority-3 "..." \
    --revenue "42,500" --expenses "18,200" --pipeline "450,000" \
    --runway "180" --runway-trend "✅" \
    --open-loop-1 "OL-001: description" \
    --open-loop-1-deadline "2026-06-10" --open-loop-1-status "🔴" \
    --open-loop-2 "OL-002: description" \
    --open-loop-2-deadline "2026-06-12" --open-loop-2-status "🔴" \
    --risk-critical "description" \
    --risk-emerging "description" \
    --decision-topic "..." --decision-context "..." \
    --decision-option-a "..." --decision-option-b "..." \
    --decision-reco "..."
```

Then manually expand the agent task table if needed. **Pitfall:** passing multiple `--agent-task` flags only renders the LAST one — 5 flags = 1 row. Use the write-file approach instead when you have 2+ agents to report.

### Multi-Agent Status Section (Write-File Format)

When using the write-file approach for rich briefs, the delegated agent table goes in Section 6. Keep each agent to one line:

```
| Agent | Task | Status | ETA |
|-------|------|--------|-----|
| Weaver | brain.md NNNh uptime, fleet N/N Up, all nominal | 🟢 | YYYY-MM-DD |
| Scribe | N/N skills healthy, N over-limit, frontmatter clean | ✅ | YYYY-MM-DD |
| Skillmate | N active skills, N% trigger coverage, N near cap | ✅ | YYYY-MM-DD |
| Sentry | All N suites green (Approval N/N, Tirith N/N). N behind, N ahead | 🟢 | YYYY-MM-DD |
| Forge | N-commit rebase clean/outstanding. Working tree clean/dirty | ✅/🟢 | YYYY-MM-DD |
| BizDev | N targets, N contacts, N contracts. N won. Pipeline $N-N | 🟡/✅/🔴 | YYYY-MM-DD |
```

Pull agent status from the most recent daily-digest pulses (write the date each agent reported), not from stale briefs. If a pulse is missing from today's digest, carry forward from the prior day's brief and note it.

## Section 7 — Recommended Decision Escalation

When a recommended decision appears for 3+ consecutive days:
1. **Days 1-2** — Standard framing: "Context. Options. Recommendation."
2. **Days 3-5** — Add escalation counter: "3rd consecutive brief recommending same decision."
3. **Days 6-10** — Call the pattern outright: "Day 21. 16th consecutive brief. Zero action. The cost of indecision now exceeds the cost of a wrong decision."
4. **Day 10+** — Change the ask from a decision to a micro-commitment: "Read this recommendation and respond with one word — 'repurpose' or 'status-quo'. That's the task."

## Footer Escalation Counter

```
*Generated by Chief of Staff | Daily Command Brief | YYYY-MM-DD | N consecutive briefs with zero action on [repeated finding]*
```

This creates a visible streak that makes the pattern impossible to miss.
