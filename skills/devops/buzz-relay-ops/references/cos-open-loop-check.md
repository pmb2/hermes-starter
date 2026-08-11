# Open Loop Check — Cron Workflow (CoS)

Recurring cron task: cross-reference the open-loops register against live Buzz channel
activity, flag stale loops (48h+ no update), close loops the channels show done, and
surface the operator's decisions needing follow-up. Output goes to #admin (or the cron
destination) in discord-report-format; `[SILENT]` when nothing is stale.

## Canonical sources (in priority order)

1. **Open loops register (THE tracker):**
   `${MY_REPOS}\Documents\github\_project\04-shared-memory\playbooks\open-loops.json`
   — managed via `python scripts/open_loops.py` from the repo root:
   - `list` — active loops only; `list --all` includes closed
   - `check-deadlines` — overdue/approaching items (use this for the stale section)
   - `close OL-XXX` — mark completed; `add --desc ... --deadline ...`
   - The daily-command-brief cron embeds this list in its prompt, so the register is
     the single source of truth for the brief's "Open Loops" table.

2. **Daily Command Brief archive (live):**
   `~/AppData/Local/hermes/cron/output/5241b21f51cb/YYYY-MM-DD_HH-MM-SS.md`
   (job id `5241b21f51cb`, schedule `0 11 * * *`). Each file's `## Response` section
   is the delivered brief — contains Open Loop table, Recommended Actions, and
   "OL-020"-style script-failure flags. Cross-reference the last 2 briefs for what was
   already recommended (avoid re-recommending the same thing 3x without noting it).

3. **Daily digest (pulse cross-reference):**
   `${MY_REPOS}\Documents\github\_project\daily-digest\YYYY-MM-DD.md` — all
   agent pulses append here; grep it for dev-lead/qa-lead/integration-lead/docs-lead/skills-lead status.

4. **Channel activity (last 48h):** `buzz_scan_channels.py` only scans 4h — for the
   open-loop check, use a 48h window query (kinds 9/1/7, `since = now - 172800`) with
   the CoS operator key, grouped by channel. 58 channels of pulse traffic is normal —
   filter out `📡`-prefixed automated pulse posts; only the operator's messages and agent
   replies matter for loop status.

## 🚨 Path trap: C: yourdata is a STUB — the real repo is on E:

`${USER_HOME}\Documents\github\_project` exists but is nearly EMPTY
(just `digests/` + `docs/`, no `scripts/`, no `06-reports/`). The live repo with
`scripts/open_loops.py`, `04-shared-memory/`, `06-reports/`, `daily-digest/` is at
**`${MY_REPOS}\Documents\github\_project`** (`${MY_REPOS}/...` in git-bash).
Running open_loops.py from the C: stub fails or returns nothing. Always use the E:
path. (Same trap applies to the daily-brief write target — `daily_brief.py` writes to
`${MY_REPOS}\...\06-reports\daily-briefs\`.)

## 🚨 MemPalace is NOT the decision log

The `mempalace|decisions` room holds only the old "MemPalace is the New Memory
Backend" migration doc — not an active decision register. Don't burn turns mining the
palace for open loops; the JSON register in _project is the tracker. MemPalace
direct SQLite queries need `cd ~/.mempalace/palace && sqlite3 chroma.sqlite3` (the
absolute-path form fails to open the DB from git-bash).

## Stale-detection rules

- **48h+ no update** (no new brief mention, no channel activity, no digest entry) →
  flag in **Stale** section with last-update date, owner, and concrete next action.
- **Closed in channels but open in register** → run `open_loops.py close OL-XXX`,
  report under **Completed (not closed)**.
- **Decisions needing follow-up** — scan the last 2 daily briefs' Recommended Actions
  plus recent non-cron Discord sessions (`source != 'cron'` in state.db) for the operator's
  approvals that lack a committed deliverable. Example found Aug 2026: marketing v2
  strategy delivered in-session but never committed to the repo; cron cleanup plan
  approved but implementation incomplete.

## Bridge reply quality is part of the check

Before trusting channel silence, verify bridge replies are real: if the last few
exchanges show 1-2 word replies (`We`, `1`), the bridge LLM path is broken even though
healthz says ok (see buzz-relay-ops pitfall "healthz OK does NOT mean replies work").
Cron pulses deliver full reports through the per-profile gateway while the bridge's
direct HTTP path stays broken — so active pulses ≠ healthy bridge.
