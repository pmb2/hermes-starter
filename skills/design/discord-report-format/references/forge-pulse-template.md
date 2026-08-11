# Forge Pulse / Codebase Health Report

Concrete Discord-formatted template for codebase health monitoring reports (Forge Pulse, repo audits, software project health scans). All follow the `discord-report-format` conventions.

## Template

```
🔵 **FORGE PULSE** | Mon DD, HH:MM AM/PM ET
━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **RECAP**
✅ Suite | result N/N
✅ Suite | result N/N
✅ Key pattern | status confirmation
🏗️ New feature landed | brief architectural note

━━━━━━━━━━━━━━━━━━━━━━━━━━

🏗️ **FEATURE / ARCHITECTURE REVIEW**
**Feature name** (commit short-hash, author): 1-2 line description.
Architecture quality note (well-architected / concerns / key pattern).
**Feature name** (commit short-hash, author): description.
Same pattern for each major upstream or local addition.

━━━━━━━━━━━━━━━━━━━━━━━━━━

🗂️ **GOD-FILE WATCH**
`path/to/file.py` = N lines (+delta since last check, ~defs/classes) — status note
`path/to/file2.py` = N lines — status note

━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 **RECOMMENDED ACTIONS**
**Action 1** | concrete step, user/agent to act
**Action 2** | specific follow-up based on scan findings
**Action 3** | scope or priority callout

━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 Checked: Mon DD, HH:MM AM/PM ET · branch `abc1234` · N local commits
```

## Section Guide

| Section | Emoji | Content |
|---------|-------|---------|
| Header | 🔵 | Title + timestamp on first line |
| Recap | 📊 | Divergence (N behind/ahead), test suite results, key pattern status |
| Feature/Architecture | 🏗️ | Upstream additions worth noting, architectural review, techniques discovered |
| God-file Watch | 🗂️ | Files growing beyond healthy size, line counts tracked over time, extraction candidates |
| Recommended Actions | 🎯 | Concrete next steps for the responsible agent or user |
| Checked | 🔍 | Verification timestamp, branch, local commit count |

## Usage Notes

- **Divergence tracking**: Use `git rev-list --left-right --count origin/main...HEAD` for ahead/behind counts.
- **God-file tracking**: Record absolute line counts at each pulse, compare deltas. `wc -l` per file. Flag files growing >500 lines/week.
- **Test suites**: Run targeted suites based on what changed. Don't run everything every cycle — test the risk.
- **Upstream scanning**: `git log origin/main ^HEAD --oneline` for behind-count then domain-scan for dev-lead-relevant commits. Use `git show --stat` to assess scope.
- **Pipeline integrity**: Check critical path ordering (e.g., approval.py path rewrite before backslash strip) if those patterns exist in the codebase.
- **Working-tree check (PRIMARY)**: Always run `git status --short` and `git diff --stat` on the target repo as a primary check, not a fallback. Developers frequently start fixes, get interrupted, and leave them half-done in the working tree. A pulse that only checks commits and divergence will miss these entirely. When you find an uncommitted change: review its diff, assess whether it's correct and complete, then either commit it (if ready) or note it as at-risk in the report.
- **Section omission**: Omit any section with nothing to report. Do NOT write "nothing new."

## Anti-Patterns

- Don't list every upstream commit — domain-filter to dev-lead-relevant changes only
- Don't run the full test suite if only docs changed — target the risk
- Don't use absolute path assertions in line-count tracking — use relative repo root paths
- Don't report "no changes" — omit the section instead
- Don't rely solely on `git log` for change detection — working-tree sprawl is how uncommitted changes get silently lost before a rebase. Run `git status --short` every cycle as a primary action, even when the commit scan returns results.
