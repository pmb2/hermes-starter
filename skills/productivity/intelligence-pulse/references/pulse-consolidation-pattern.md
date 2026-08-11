# Cron Job Pulse Consolidation Pattern

When the operator's cron ecosystem accumulates overlapping pulse jobs (same frequency, similar scanning scope, redundant deliverables), use this pattern to consolidate.

## Detection Signals

Overlap exists when any of these are true:
- Two+ jobs run on the same schedule and both do web_search intel scanning
- Two+ jobs deliver to the same channel at the same time of day
- A Morning Brief exists alongside a Local Pulse and a Cyber Brief, all within 60min
- A job's prompt says "mid-day intelligence check" and another says "heartbeat check" — same intent

## Audit Steps

1. List all cron jobs: `cronjob(action='list')` — look at schedule, skills, enabled_toolsets, prompts
2. Group by frequency: all every-4h jobs, all daily jobs, all weekly jobs
3. Read overlapping prompts to compare scope
4. Identify which are truly redundant (same scanning pattern) vs specialized (domain-specific)

## Consolidation Template

### What to pause
Pause the redundant jobs (don't delete — preserve as historical reference):
```python
cronjob(action='pause', job_id='old-redundant-job')
```

### What to create
Create one consolidated replacement that covers the merged scope. Use `deliver: all` so it reaches every connected channel.

### What to keep separate
Keep specialized jobs that target a specific domain:
- C2C Hunter — opportunity-specific, separate from general intel
- Cyber Night/Morning — security-specific research pipeline
- Sports Betting — domain-specific odds scanning
- Hermes Dev pulses (dev-lead/skills-lead/integration-lead/qa-lead/docs-lead) — codebase/QA focused

## Real Example (the operator's ecosystem, Jun 21)

### Paused (6 jobs):
| Original | Frequency | Replaced By |
|----------|-----------|-------------|
| the operator's Pulse | every 4h | Consolidated Pulse Scan (every 4h) |
| Pulse Every 4h Live Scan | every 4h | Consolidated Pulse Scan |
| Pulse Morning Wrap-Up | 6AM | Consolidated Morning Brief (7AM) |
| Pulse Evening Wrap-Up | 6PM | Consolidated Evening Brief (8PM) |
| Daily Pulsar | 8PM | Consolidated Evening Brief |
| Duplicate Strategic Advisor | 8AM/8PM | (was superseded by real one) |

### Created (3 consolidated jobs):
| Job | Schedule | Covers |
|-----|----------|--------|
| Consolidated Pulse Scan | every 4h | blogwatcher + web intel + cron health + kanban check |
| Consolidated Morning Brief | 7AM ET | overnight intel + local pulse + cyber brief + cron health + session review |
| Consolidated Evening Brief | 8PM ET | EOD summary + intel roundup + tomorrow outlook + kanban status |

### Unchanged (specialized):
C2C Hunter, Cyber Night Research, Cyber Morning Brief, Sports Betting, Self-Healing Pulse, Daily Cash-Flow, Legal Watchdog (4), all Hermes Dev pulses, tor-circuit-rotation

## After Consolidation

- Update the Kanban board card for "Pulse Consolidation Analysis" to reflect what was done
- Comment on any related cards with the changes
- Future audits should check if the consolidated jobs need further tuning
