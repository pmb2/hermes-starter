# CoS Channel Scan — Reading the Output (false positives)

The recurring Chief-of-Staff cron scan runs `scripts/buzz_scan_channels.py`
against the local relay (`ws://localhost:3000`) and prints a banner,
`URGENT=YES/NO`, urgent flags, @Chief mentions, new threads, and stalled list.

**Key lesson: `URGENT=YES` is almost always a false positive on a healthy fleet.**
The scanner's `urgent_kw` list (`urgent, crisis, emergency, critical, 🚨, 🔴,
down, broken, outage, blocker, p0, P0, fire, asap, failing, failed`) matches
**substrings inside routine self-healing / pulse digests**. Every agent posts a
`*-pulse` digest on its own cadence to its channel, and those digests routinely
contain the words "down", "failed", "🚨", "🔴", "p0" in their *reporting body*
(e.g. a "SELF-HEALING INFRA PULSE" recap that documents what it checked).
These match the crude keyword filter even though nothing is wrong.

## Two pass rule (always)

1. **Run the scanner** → capture URGENT, flags, mentions, threads, stalls.
2. **Manually triage before acting.** Do NOT post a RED alert or wake the operator
   because the banner says `URGENT=YES`. Inspect the matched content:

Genuine crisis (escalate)   | Routine noise (ignore, SILENT)
----------------------------|-------------------------------
Human-authored message      | `*-pulse` digest from an agent profile
@Chief / @CoS / @Aegis @mention needing reply | Automated "All work complete" / "digest appended"
Down/outage/blocker wording about a **service the operator depends on** | Keyword appears inside a recap/checklist body
A human question going unanswered 2h+ | Channel where only one agent posts on a fixed schedule
Cross-channel duplication of a real incident | Same routine pulse landing in its own channel

Common healthy-fleet output that still prints `URGENT=YES` (all routine):
- `#monitoring` → "Self-Healing Pulse", "the operator's Pulse", "Local Pulse"
- `#devops` → `qa-lead-pulse` ("All work complete")
- `#sports` → `sports-betting-pulse`
- `#engineering` → `dev-lead-pulse`
- `#skills` / `#docs` / `#integrations` → `skills-lead-pulse` / `docs-lead-pulse` / `integration-lead-pulse`

## Reliable signals that DO warrant a RED alert before the morning brief

- **Bridge hung**: PID alive but `logs/buzz_bridge.log` mtime stale >5 min with
  no heartbeat dots → real infra failure (agent @mention routing is dead). See
  `references/bridge-heartbeat-monitoring.md`. Check BOTH tasklist AND log mtime.
- **A @Chief/@CoS/@Aegis @mention** in a team channel (direct, actionable).
- **Human thread** started within the window that names a service/incident.
- **Cross-channel** duplication of the *same* real incident.

## Escalation format (when genuinely urgent, post to #admin)

```
🚨 Channel scan — {time}:
- {alert 1}
- {alert 2}
```
Keep to 3 lines max. If everything normal, SILENT (no "all clear" posts).