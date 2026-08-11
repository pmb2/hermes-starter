# Weekly Intelligence Digest (Sunday)

A human-written, reflective weekly summary synthesizing the past 7 days into a curated brief. Distinct from all other pulse variants — this is **not** a data dump or a live scan. It's the week's story, framed for the operator's attention.

**When to run:** Sunday delivery (Weekly Intelligence Digest cron job). Also usable on-demand when the operator asks "what happened this week."

**Data Gathering Sequence (critical order — don't skip steps):**

1. **Git log scan of relevant repos for past 7 days** — `hermes-agent`, `hermes-config`, `ai-sharp`, `website-landlord`, and any discovered repos with activity:
   ```
   cd ${HERMES_HOME}/hermes-agent && git log --since="7 days ago" --oneline
   cd ${USER_HOME}/Documents/github/hermes-config && git log --since="7 days ago" --oneline
   cd ${USER_HOME}/ai-sharp && git log --since="7 days ago" --oneline
   ```
2. **Session search for pulse outputs from the past week** — query for qa-lead-pulse, dev-lead-pulse, cash-flow briefing, dev-lead-pulse, self-healing pulse, daily command brief. These contain the week's operational signals.
3. **Cross-reference daily cash-flow briefings** — read the most recent one for current state; skim earlier ones for this week's findings (ExampleVendor LLC, Adbakx LLC, etc.)
4. **Check nightly reports** — `nightly-reports/` dir for watchdog status
5. **Check cron output dirs** — `cron/output/`, `cron/gap-reports/` for any errors
6. **Synthesize** — group findings into the required sections, derive a theme that connects them

**Section structure (fixed order):**

```
🔵 WEEKLY INTELLIGENCE DIGEST | Sun Jul DD · HH:MM PM ET

*This week's theme: [one-line theme connecting the week's events]*

---

[EMOJI] **SECTION** (e.g. 🏗️ LAND SALES CRM (P0))
• [compact bullet items]
• ...

[EMOJI] **SECTION** (e.g. 💰 C2C REVENUE)
• ...

[EMOJI] **SECTION** (e.g. 🔧 INFRASTRUCTURE CHANGES)
• ...

[EMOJI] **SECTION** (e.g. 🧠 INTELLIGENCE TRENDS)
• ...

---

🎯 **RECOMMENDED ACTIONS**
[Numbered, concrete next steps — 2-4 items max]

---

*Next week's focus: [one-line forward-looking statement]*

🔍 **Checked:** Sun Jul DD · HH:MM UTC | [repo] HEAD `[commit]`
```

**Section rules:**
- **Land Sales CRM always goes first** (P0 priority). If there's nothing to report, say it plainly: "Status: Stalled." or "No progress this week." — don't omit it.
- **C2C Revenue second** — actual cash-generation signals: new finds, outreach sent, responses received, contracts. "Pipeline is discovery-rich but conversion-data poor" is a valid truthful summary.
- **Infrastructure Changes third** — notable commits, upgrades, cron changes. Split into ✅ (good fixes), 🟡 (degraded/warning), 🔴 (critical). Keep technical detail compact.
- **Intelligence Trends fourth** — pulse consolidation status, MCP server health, PIM stats, notable dedup wins. Pattern-level observations.
- **Recommended Actions** — concrete numbered steps, not platitudes. Include specific repo names, file paths, or commands where helpful.
- **Next week's focus** — one line, forward-looking, sets expectation for the coming week.

**Tone:**
- Reflective and forward-looking — not a firehose, not a data dump. the operator reads this on Sunday to orient for the week ahead.
- Curated — pick what actually mattered. A full week fits in under 3000 chars.
- Honest about gaps — "Stalled" is preferred over "No updates." Call the stalled state what it is.
- No filler phrases, no "nothing new" sections — omit or name the stall explicitly.
- Start with a theme statement that connects the disparate events. This is the week's thesis.

**User context that shapes section content:**
- the operator's primary focus is **Land Sales CRM** — land wholesaling, Lehigh Acres FL spec builders
- **C2C MES consulting** is secondary — Solumina contracts, small integrators (50-500), remote roles $100-200/hr
- **Everything else is noise** — infrastructure, Hermes dev, pulses exist to serve the above two

**Pitfalls:**
- Do NOT start with browse-mode session_search in cron context — it returns only cron sessions in cron runs. Use git logs as the primary activity signal.
- Do NOT report "no commits" for repos you didn't check. Always run the full dynamic scan before concluding anything.
- Do NOT fabricate status for repos you couldn't find (e.g., if `ghl` repo location is unknown, say it plainly).
- The "outreach drafts ready but none sent" pattern is a recurring signal for Land Sales CRM — if you see it in the data, flag it as the bottleneck it is.
- When every infrastructure bullet would be "no change," omit the section rather than padding it.
- Keep "Next week's focus" action-oriented and concrete — not a platitude like "Keep pushing forward."
