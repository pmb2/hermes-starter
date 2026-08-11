# Weekly Intelligence Digest — the operator

Template for the weekly digest delivered to the operator via Discord cron. Covers the last 7 days.

## Content Structure (required order)

1. **Header** — bold emoji + "WEEKLY INTELLIGENCE DIGEST" + Sun Jul 19 · Weekly Edition
2. **This week's theme:** — one-sentence characterization of the week (e.g., "Rebase and recalibrate", "Quiet week, maintenance mode")
3. **Land Sales CRM** section — always first, always the most detailed
4. **C2C MES Revenue** section — always second
5. **Infrastructure** section — always third
6. **Skills & Docs** section — if anything to report
7. **🎯 RECOMMENDED ACTIONS** — concrete next steps, required
8. **Next week's focus:** — one-line call forward
9. **🔍 Checked:** — timestamp + data source note

## Tone & Voice
- **Reflective and forward-looking** — not a firehose of events. Curated summary of what actually mattered
- Curated over comprehensive — the reader already lived the week; they need the signal, not the noise
- Direct, no filler phrases ("it's worth noting that", "it appears that", "interestingly")
- One item per line, compact format, no blank lines between related items
- Under **3000 chars**

## Section Content Rules

### Land Sales CRM
Check for: new tier data exports (look in `AppData/Local/hermes/data/` for CSV dates), builder research files, Adams Homes / Century Communities buy-box work, any GHL activity, CRM-ready leads. Call out staleness explicitly ("X weeks stale" if over 2 weeks). End with a one-line `📌 Next:`.

### C2C MES Revenue
Pull from BizDev MCP (`mcp__bizdev_agent__bizdev_dashboard`, `bizdev_followups`). Report: total targets, contacts, decision makers, outreach sent, pending followups, pipeline value range. Call out warmest contacts. End with `📌 Next:`.

### Infrastructure
Pull from hermes-config CHANGELOG, git activity across all repo roots, pulse digests. Cover: config changes, dev-lead state, divergence/rebase status, god-file sizes, Docker fleet, brain.md health, cron status. Keep curated — don't list every pulse finding.

### Recommended Actions
Required. 3-5 concrete, actionable items with clear priority ordering. Use bold for urgency indicators.

## Data Sources (in priority order)
1. **Digests** — check `${USER_HOME}/Documents/github/_project/digests/` for the most recent digest file(s) from this week. Read at least the last 2-3 to understand the week's arc
2. **Git activity** — dynamic scan across all repo roots: `${USER_HOME}/github/`, `${USER_HOME}/projects/`, `${USER_HOME}/Documents/github/`, `${USER_HOME}/Documents/github/`
3. **BizDev pipeline** — via `mcp__bizdev_agent__bizdev_dashboard` and `bizdev_followups`
4. **Land data** — check timestamps on CSVs in `AppData/Local/hermes/data/` for recentness
5. **hermes-config CHANGELOG** — for infrastructure/config changes
6. **Pulse MCPs** — tradesignals, gbrain, etc. for system state

## Priority Ranking
the operator's focus hierarchy: **Land Sales CRM** > **C2C MES consulting** > everything else. Any finding in Land Sales CRM gets prominent placement. C2C gets a section but shorter. Infrastructure is for signal only (config changes, cron issues, system health alerts).
