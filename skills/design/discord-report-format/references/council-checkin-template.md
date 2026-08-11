# Council Check-In Template

Weekly executive council check-in report. Covers 8 leads (Finance, Legal, Tax, Investment, Technology, Revenue, Operations, Intelligence). Follow all discord-report-format rules (compact, no em dashes, no blank lines between items, Recommended Actions always present).

``` 
🔴 **WEEKLY COUNCIL CHECK-IN** | Mon DD, HH:MM AM/PM ET
━━━━━━━━━━━━━━━━━━━━━━
🚨 **SCRIPT ERROR** | if automation missing, state which run consecutively

⚠️ **WEEK N: EXECUTIVE SUMMARY**
1-2 lines capturing the week's key signal. Include a week-on-week trend if available.

📊 **AT A GLANCE**
**Finance** 🟡/✅/🔴 | status, key blocker
**Legal** 🟡/✅/🔴 | status, key blocker
**Tax** 🟡/✅/🔴 | status, key blocker
**Investment** 🟡/✅/🔴 | status, key blocker
**Technology** 🟡/✅/🔴 | status, key blocker
**Revenue** 🟡/✅/🔴 | status, key blocker
**Operations** 🟡/✅/🔴 | status, key blocker
**Intelligence** 🟡/✅/🔴 | status, key blocker

📈 **WEEK-ON-WEEK**
0/8 leads progressed, X/Y recs acted on, deadline tracker, metric drift

🔴 **BLOCKERS**
**Lead** | description, impact, days unresolved
**Lead** | description, impact, days unresolved

🔄 **CROSS-COUNCIL DEPENDENCIES**
**Dependency** | A needs B by date, status

━━━━━━━━━━━━━━━━━━━━━━
🎯 **RECOMMENDED ACTIONS**
**Action 1** | specific step, who does it, timeframe
**Action 2** | concrete follow-up based on report findings
**Action 3** | escalation if no action taken on repeat items

━━━━━━━━━━━━━━━━━━━━━━
🔍 Archived to `path/file.md` | Mon DD, HH:MM AM/PM ET
```

## Escalation Tracking

When recommendations appear in consecutive reports with zero action, increment an escalation counter:

```
| # | Issue | Weeks Flagged | Escalation Level |
|---|-------|--------------|------------------|
| 1 | Q2 Tax Payment | 4 | 🔴 CRITICAL |
| 2 | D-006 Decision | 4 | 🔴 CRITICAL |
```

Escalation levels: 🟢 First flag → 🟡 Repeated (2-3) → 🔴 Critical (4+) → ❌ Deadline passed

## Silent / No-Change Pattern

If a freshness check (session_search for last output) shows identical findings to the current check, respond `[SILENT]` to suppress delivery. Only deliver when there is genuinely new information or when enough time has passed to warrant a status update regardless.

## Finding Status When Live Polling Is Unavailable

In cron context (no user present, no live messaging channels), reconstruct status from:
1. Previous report(s) for baseline state and tracked items
2. Council lead memory.md files for structural context
3. Recent daily briefs for interim changes and priority shifts — check `daily-digest/` directory specifically
4. Git logs and file timestamps for activity signals
5. gbrain or other knowledge stores for any new information
6. Delta comparison against last report to identify changes
7. `gateway_state.json` if present (typically at `~/AppData/Local/hermes/gateway_state.json`) — provides live gateway PID, Discord/API connectivity state, and active agent count. Gateway resurrection is a high-signal finding.
8. `council-state.json` if present (typically at `~/AppData/Local/hermes/council-state.json`) — provides PID-level tracking across all council leads; useful for confirming process liveness vs stale profiles.
9. Docker live inspection — `docker ps` reveals fleet expansion, container health, and new stacks that may indicate lead activity not captured elsewhere.
