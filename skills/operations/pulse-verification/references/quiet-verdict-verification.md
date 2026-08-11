# Verify Quiet / Empty Verdicts in Recurring Data Streams

"0 new emails", "no change", "nothing new" are negative verdicts — verify them the same way as feature negatives (see main SKILL.md Core Rule) before staying `[SILENT]`. Two patterns confirmed Aug 3, 2026 (Daily Cash-Flow Briefing run).

## Pattern 1: "0 recruiter emails in 48h" can mask a dead connector

A zero-count email query is only meaningful if the connector is alive. Check per-source freshness:

```bash
sqlite3 "${MY_REPOS}/Documents/github/git-mcp/services/personal-intelligence-mcp/pim.db" \
  "SELECT source_type, MAX(ingested_at) FROM saved_items GROUP BY source_type;"
```

**Interpretation:**
- Email `MAX(ingested_at)` 7+ days older than the freshest other source (grok, bookmarks, youtube) → the IMAP email connector specifically is broken (token rotated / app-password expired / Gmail security event) while the rest of the pipeline runs fine. Verdict: "email connector dead — N days of recruiter emails sitting unread in Gmail", NOT "quiet period". Flag the exact stale date and pair with the restart + verify-IMAP-auth-on-both-Gmail-accounts action.
- All sources stale together → full pipeline stall (check `hermes cron list` for the PIM job's last-run error).
- Email fresh but others stale → the known "only email shows activity" partial stall (Firefox-dependent connectors down).

Observed Aug 3: email stale since Jul 24 while grok ingested Jul 29 — connector-specific failure, not a quiet market.

## Pattern 2: "Already surfaced by the C2C Hunter" — check whether the digest actually captured it

The C2C Hunter delivers its own reports to Discord, but the daily digest only captures a subset of pulses. Before a briefing concludes "no change, already reported", grep today's digest:

```bash
grep -i -A3 "C2C\|DiBell\|PamTen\|hunter" "${MY_REPOS}/_project/daily-digest/$(date +%Y-%m-%d).md"
```

**Interpretation:**
- Digest contains the hunter's lead names / quiet-period break → already consolidated → stay silent.
- Digest exists but has NO hunter content (even though the hunter delivered to Discord) → the current briefing IS the first consolidated read → deliver the leads.

"No change = [SILENT]" applies only to streams already surfaced in a consolidated form; overnight finds that never reached the digest are change.

Observed Aug 3: digest held Forge/Skillmate/Scribe entries but NOT the C2C Hunter's 2:40 AM quiet-period-breaking leads (DiBell Group, PamTen) — the 7:01 AM Morning Brief never saw them, so the cash-flow briefing was the first consolidation and delivered.
