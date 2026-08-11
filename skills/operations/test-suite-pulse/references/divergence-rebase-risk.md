# Divergence Measurement & Rebase-Risk at High Behind-Counts

Session-verified lessons for pulse cycles tracking a fork against a fast-moving upstream (Aug 2026, hermes-agent at 500+ behind).

## 1. Fetch BEFORE you count divergence

A remote-tracking ref goes stale between cycles. Counting `git rev-list --left-right --count HEAD...origin/main` without fetching reproduces the prior cycle's number, which is wrong the moment it's printed.

Verified Aug 8 2026: the 01:45 UTC pulse reported **448 behind** from the ref as last fetched; a fresh `git fetch origin main -q` revealed the true count was **573 behind** (+125 upstream commits in ~8h, ~10.7/h — an upstream security/redaction wave). The stale number had been carried as fact for two+ cycles.

```bash
git fetch origin main -q
git rev-list --left-right --count HEAD...origin/main   # fresh ahead/behind
```

Only fetch-then-count numbers belong in the report. Also note the delta since last pulse (`+125 in ~8h`) — rate acceleration is itself a signal (rebase window narrowing).

## 2. `git merge-tree` = 0 conflicts ≠ semantically clean

`git merge-tree HEAD origin/main | grep -c "^+<<<<<<<"` returning 0 means the hunks don't overlap **verbatim**. It does NOT mean the merge is safe when upstream churn is heavy in files that carry local fix hunks.

Verified Aug 8 2026: 573 behind, merge-tree = **0 conflicts**, yet the dev-lead lane flagged `tools/terminal_tool.py` as the hottest conflict zone — upstream redaction commits (`530d37820`/`72eda946b`/`f0a3ef8bd`) landed inside `terminal_tool()` at :2561-2568, ~20 lines from our NUL-byte guard hunks (`78eb3542b`). Textual-clean; the merge still needs hunk-level adaptation and re-verification of local fix behavior.

**The real risk signal is the PAIR:**
- (a) `git diff --stat HEAD...origin/main -- <fix-file>` shows heavy upstream insertions (hundreds of lines) in a file that carries local fixes
- (b) those upstream hunks land near the local fix lines

```bash
# Quantify upstream churn in your fix files
git diff --stat HEAD...origin/main -- cron/scheduler.py tools/terminal_tool.py hermes_cli/model_switch.py
```

**Cross-check sibling lanes' pulse digests** — dev-lead/docs-lead usually flag the same conflict zones first (the dev-lead 09:34 pulse named `terminal_tool.py` before this pulse's own audit). Read the same-day digest before finalizing the conflict-zone assessment.

**Action when the pair fires:** pre-stage resolution notes for the rebase (which local hunks are at risk, what upstream changed nearby), coordinate the rebase window with the dev-lead lane, and do NOT report the 0-conflict merge-tree as the all-clear.
