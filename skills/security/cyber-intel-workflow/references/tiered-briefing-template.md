# Tiered Briefing Template — Cyber Morning Briefing

Use this template when the pipeline includes the cyber-intel-scanner + auto_action_handler. It separates auto-implemented actions from items needing manual review.

## Required Context Recovery

Before writing the briefing, gather these data points:

1. **Night research session** — `session_search(query="Cyber Night Research", sort="newest", limit=1)`
2. **Scanner output** — `session_search(query="cyber-intel-scanner", sort="newest", limit=1)`
3. **Current scored findings** — `cat <monitoring>/findings/cyber_intel_findings.json` (parse with Python for tier breakdown)
4. **Action log** — `cat <monitoring>/findings/cyber_actions_log.jsonl | tail -20` — what the handler actually did
5. **Dedup state** — `cat <monitoring>/findings/auto_action_state.json` — what's been processed
6. **Self-healer state** — `cat <monitoring>/findings/self_healer_state.json` — detect handler failures
7. **Hardening notes** — `cat <research>/cyber_hardening_notes.md | tail -20`
8. **Intel log** — `cat <research>/cyber_intel_log.md | tail -20`

Paths:
- `<monitoring>` = `${USER_HOME}/trumpian-accounting-kb/monitoring/` (Windows) or equivalent
- `<research>` = `${MY_REPOS}/Documents/research/` (Windows) or equivalent

## Freshness Sweep

Run after context recovery. Try in order:

1. **CISA KEV JSON feed**: `curl -sL -H "User-Agent: Mozilla/5.0" "https://cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"` -> filter by `dateAdded` (last 3 days)
2. **GitHub PoC search**: `curl -sL "https://api.github.com/search/repositories?q=CVE+2026+poc+exploit&sort=updated&per_page=10"`
3. **Google News RSS**: `curl -sL "https://news.google.com/rss/search?q=cybersecurity+zero+day+exploit+2026&hl=en-US&gl=US&ceid=US:en"`
4. **NVD API** for specific CVEs found: `curl -sL "https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=<CVE-ID>"`
5. If browser tools available: check BleepingComputer, CISA advisories, The Hacker News

## Separation Logic

### Auto-Implemented (from action log)
Read `cyber_actions_log.jsonl` for entries with these `action_type` values:
- `hardening_note` -> appended to `cyber_hardening_notes.md`
- `intel_logged` -> appended to `cyber_intel_log.md`
- `enhance_config` -> config change noted (needs manual review)
- `clone_success` / `paper_downloaded` -> files on disk

Report each as: `✓ [Action]: [what was done] — [result file/path]`

### Already Actioned (from state, not new today)
Fingerprints in `actioned_fps` that also appear in today's findings. These are recurring signals the handler already processed. Flag them with a note: "Recurring since [date]. Needs escalation decision."

### New Unprocessed Tier 1 (not in state)
Fingerprints in today's findings NOT in `actioned_fps`. Report as pending review.

### Handler Failures
If `self_healer_state.json` shows `cron_failures:auto_action_handler`, include a system issue warning.

## Example Output

```
🔵 CYBER BRIEFING | Tue Jul 14 · 7:00 AM ET

**TL;DR** Auto-action handler has been failing (self-healer detects
cron_failures:auto_action_handler). Last successful cyber action run was
Jul 10 at 11:25 PM ET. Freshness sweep found PoCs for CVE-2026-2441
(Chrome UAF) and CVE-2026-41940 (cPanel auth bypass).

━━━━━━━━━━━━━━━━━━━━━━

🔴 TIER 1 — AUTO-IMPLEMENTED

From last successful handler run (Jul 10 23:25 ET):

✓ Hardening note: Breached credentials sweep (24 DW hits, score 0.62) ->
  cyber_hardening_notes.md
✓ Intel logged: Breached credentials sweep -> cyber_intel_log.md
✓ Intel logged: Gateway crash watchdog.log (63 occ, score 0.6) ->
  cyber_intel_log.md
✓ Intel logged: Auth failures gw-diag.log (11 occ, score 0.36) ->
  cyber_intel_log.md

⚠️ Auto-action handler is down. Self-healer detected
cron_failures:auto_action_handler. Last action run Jul 13 08:36 ET.

━━━━━━━━━━━━━━━━━━━━━━

🔴 TIER 1 — REMAINING / OVERNIGHT

Recommendation: Run haveibeenpwned check on primary accounts. The
recurring breached credentials signal (score 0.62) has been appearing
daily since Jul 10 without escalation.

Recommendation: Review watchdog.log crash stack traces. Gateway
crash pattern (63 occurrences, score 0.6) persists.

Recommendation: Cross-reference gui.log crash timestamps with
watchdog.log. New crash pattern detected Jul 12 (28 occurrences).

━━━━━━━━━━━━━━━━━━━━━━

🟡 TIER 2 — RECOMMENDED ACTIONS

Recommendation: Review gw-diag.log auth failure patterns (11 occ).
Could indicate credential rotation needed or unauthorized access.

Recommendation: Check CVE-2026-2441 (Chrome UAF, PoC published).
Affects Chromium-based browser tools in pipeline.

Recommendation: Check CVE-2026-41940 (cPanel auth bypass, PoC
published). Relevant if any servers use cPanel.

━━━━━━━━━━━━━━━━━━━━━━

🔵 TIER 3 — WATCH LIST

CISA KEV: CVE-2008-4128 (Cisco IOS CSRF) added Jul 13, due Jul 16
CVE-2026-31802 (npm path traversal, PoC published)
Security news: Microsoft patched RoguePlanet Defender zero-day

━━━━━━━━━━━━━━━━━━━━━━

🎯 SUMMARY

✓ Auto-implemented: 5 actions (Jul 10 run)
🔄 Pending review: 5 items (3x T1 + 2x T2 + PoCs)
👁️ Monitoring: 3 items (CISA KEV + news)
⚠️ System issue: auto_action_handler cron failing

🔍 Checked: 7:00 AM ET | Sources: CISA KEV, GitHub PoC, news RSS
```

## Discord Formatting Rules

- No em dashes — use commas or periods
- Compact one-line-per-item format
- **Bold** for CVE IDs, company names, project names
- `Backticks` for filenames, commands, paths
- Box-drawing separators: `━━━━━━━━━━━━━━━━━━━━━━`
- No blank lines between items in a section
- No HTML or markdown headings
- Timestamps in ET
