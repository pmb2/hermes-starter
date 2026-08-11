# Prompts & Templates

Reusable prompt and report-template files for cron jobs. Copy, edit, point a cron job
at them (or inline them via `hermes cron edit`). All prompts are **generic** — no
personal names, companies, or market specifics.

## Prompts

| File | Use for |
|------|---------|
| `cos-morning-brief.md` | Daily opening brief — yesterday, today, open loops |
| `cos-pulse-check.md` | Periodic system/pulse health check |
| `cos-open-loop-check.md` | Sweep unfinished work items across sessions |
| `cos-channel-scan.md` | Scan channel activity and summarize |
| `lead-daily-*.md` (dev, ops, finance, health, intel, cyber, legal, revenue, betting) | Vertical daily scans — structure adapts to any domain |

The `lead-daily-*` set is a namespaced pattern: take one, rename the namespace, and
you have a daily scan for any vertical you care about.

## Templates

| File | Use for |
|------|---------|
| `cos-daily-command-brief.md` | Structure for a daily command/ops brief |
| `lead-daily-summary.md` | Structure for a lead-summary report |

## Wiring into cron

```bash
hermes cron create '0 7 * * *' --prompt "$(cat prompts/cos-morning-brief.md)"
# or reference the file from a job's prompt field once copied into Hermes home:
#   cp prompts/* ~/AppData/Local/hermes/prompts/
```