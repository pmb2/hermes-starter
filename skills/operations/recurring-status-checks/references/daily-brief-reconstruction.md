# Daily Brief Manual Reconstruction

When `daily_brief.py` fails (script not found, wrong path, OR produces template stubs with `{{placeholder}}` values), reconstruct the brief from these offline sources.

## Phase 0: Script Re-invocation with Prompt Data

Before falling back to full manual reconstruction, try re-running the script with explicit data flags derived from the user's cron prompt:

```bash
cd ${MY_REPOS}/_project && python scripts/daily_brief.py \
  --priority-1 "User's Priority 1 text" \
  --priority-2 "User's Priority 2 text" \
  --priority-3 "User's Priority 3 text" \
  --open-loop-1 "OL-NNN: description" \
  --open-loop-1-deadline "YYYY-MM-DD" \
  --open-loop-1-status "⏳" \
  --dry-run
```

Use `--dry-run` to preview before writing. The script's template is simple string replacement — it produces a markdown file but doesn't pull live data from any external source. Even with flags, most sections (revenue, expenses, pipeline, risks, agent tasks, decisions) will remain as `{{placeholder}}` values. **Use the flag-based output as the structural spine, then fill the remaining sections manually from the sources below.**

## Data Sources (Priority Order)

### 0. MCP Tools (fastest, live data)
Check available MCP servers first — they bypass broken scripts entirely:
- **BizDev dashboard** — `bizdev_dashboard()` for pipeline stats (total targets, contacts, decision makers, active contracts, pipeline value min/max, contracts won/lost, pending followups)
- **BizDev targets** — `bizdev_list_targets()` with filters for contacted/identified by sector/technology
- **BizDev followups** — `bizdev_followups()` for pending outreach items (note: may return empty `[]` even when dashboard shows non-zero — cross-reference with dashboard `pending_followups` count)
- **Postgres MCP** — if a CRM database is configured, query directly for contact counts, opportunity stages, lot records
- **gbrain** — `get_recent_salience()` for recently-active pages, `query()` for land-sales or CRM related pages

### 1. Open Loops
```bash
cd ${MY_REPOS}/_project && python scripts/open_loops.py list
```

### 2. Weekly Council Report (most recent)
Path: `_project/06-reports/weekly-council/YYYY-MM-DD-weekly-council.md`
Read for structural context, lead status, blocker list, escalation tracker. Extract the Open Loops Register table as the authoritative open-loops baseline.

### 3. Today's Daily Digest
Path: `_project/daily-digest/YYYY-MM-DD.md`
Read for same-day pulse data from all agents (Sentry, Forge, Scribe, Weaver, Skillmate). If today's doesn't exist, read the most recent.

### 4. Git Activity Scan
```bash
find ${MY_REPOS} -maxdepth 2 -name .git -type d -print0 | xargs -0 -P4 -I{} bash -c 'd=$(dirname "{}"); repo=$(basename "$d"); count=$(git -C "$d" log --oneline --since="48 hours ago" 2>/dev/null | wc -l); [ "$count" -gt 0 ] && printf "[%d] %s\n" "$count" "$repo"; git -C "$d" log --oneline --since="48 hours ago" 2>/dev/null | head -3'
```
Also check working tree: `git -C /primary/repo status --short && git -C /primary/repo diff --stat`

### 5. Council Lead Memory Files
- `growth-lead/memory.md` — MES/Solumina targets, C2C pipeline, land sales CRM
- `growth-lead/README.md` — directory index for quick context
- `income/` directory — c2c outreach plans, pitch samples

### 6. Infrastructure State
Read from Weaver pulse entries in daily digest: container counts, gateway status, brain.md health, MCP server status.

### 7. Cron Prompt Itself
The user's cron prompt often contains authoritative context: explicit top-3 priorities, open loop references with IDs/deadlines, and **exclusion rules** ("do NOT mention X, Y, Z"). Treat exclusion rules as hard constraints — omit those sections entirely from the report.

## Report Structure

```
🔵 **DAILY COMMAND BRIEF** | Day, Date · HH:MM AM/PM ET

━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ SCRIPT ERROR
`script_path` — failure description. Brief compiled manually.

━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 SYSTEM STATUS | table of components
🎯 PRIORITY N | context, count, action needed
⏳ OPEN LOOP | table of unresolved items
⚠️ CRON PATH ISSUES | specific fix recommendation

━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 Checked: Day, Date · HH:MM AM/PM ET
```

## Known Pitfalls
- `daily_brief.py` exists at `_project/scripts/` but cron config often references a double-nested path. Always verify the actual script path before concluding it's missing.
- Even when `daily_brief.py` runs successfully, it may output a template with `{{placeholder}}` values — no real data. Always verify output.
- No repos may show commits. Cross-check working tree (`git status --short`) before concluding no activity.
- If today's digest doesn't exist, use the most recent. The digest pipeline may lag the daily brief cron.
