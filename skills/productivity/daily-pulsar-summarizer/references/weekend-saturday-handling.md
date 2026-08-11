# Weekend / Quiet-Day PULSAR Handling

## Observed Pattern (Jun 20, 2026 — Saturday)

On June 20 (Saturday), no digest existed for the current day. The most recent digest was June 19 (Friday), written at 19:37 ET the evening before.

### Correct handling:
1. **Detect day-of-week first:** `TZ='America/New_York' date +%u` returns 6 (Sat) or 7 (Sun)
2. **Saturday: Friday's digest is the expected last digest** — don't flag "0 pulses fired today" as an infrastructure issue
3. **Compute freeze-age accurately:** Bookends/ConstructManage last commits June 5 → June 20 = 15 days frozen, not the default "N days" from P0 check
4. **Zero user git commits on Saturday = expected** — don't flag user absence unless it extends through Monday

### PULSAR framing for Saturday:
```
📊 **FRIDAY IN [N] PULSES**
Weaver · Scribe · Skillmate · Sentry · Forge — all fired, all clean
...
🟢 **Sat status**: [activity summary]. Zero user commits since Friday
```

### What NOT to do:
- ❌ Flag "0 pulses today — cron infrastructure may be down" (incorrect on weekends)
- ❌ Escalate user absence after 1 day on Saturday
- ❌ Report "No activity since Friday" as an alarm when Saturday is the expected gap

### Cross-repo freeze detection on weekends:
The pre-migration freeze pattern (many repos frozen on June 5) is especially visible on quiet weekend days when there are no new commits to distract from the signal. Use the cross_repo_freeze_check.py to detect:
- How many repos share the same last-commit date
- Whether the commit messages contain pre-migration language
- Which repos have progressed past the freeze date vs. those still stuck

This tells the user whether the migration was completed on some repos or abandoned entirely.
