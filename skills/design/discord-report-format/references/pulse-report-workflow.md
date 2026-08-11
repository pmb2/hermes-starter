# Pulse Report Workflow Reference

Companion to `discord-report-format` for heartbeat / 4-hour pulse reports. This is a concrete recipe, not upstream documentation.

## Goal

Surface what **changed** in the last pulse window. Work context first, intelligence second.

## Phase 1: Dynamic Git Scan

Enumerate every git repo under the user's projects root. On Windows/MSYS:

```bash
for d in ${MY_REPOS}/*/; do
  if [ -d "$d/.git" ]; then
    repo=$(basename "$d")
    commits=$(git -C "$d" log --oneline --since="4 hours ago" 2>/dev/null | head -5)
    [ -n "$commits" ] && echo "=== $repo ===" && echo "$commits"
  fi
done
```

Adapt the path and `--since` to the pulse interval. Do not hard-code a short repo list.

## Phase 2: Cross-Reference Other Pulses

Read the daily digest for the current day (if it exists) and pull findings from sibling pulses:

```bash
cat "${MY_REPOS}/_project/daily-digest/$(date +%Y-%m-%d).md" 2>/dev/null
```

Look for mentions of dev-lead, qa-lead, integration-lead, docs-lead, skills-lead, Self-Healing, or other named pulses. Surface their outcomes so the current pulse isn't duplicative but is complete.

## Phase 3: Cron / System State

Check `hermes cron list` for the named pulses. Note:
- Last run status (`ok` or `error`)
- Rate-limit / HTTP 429 errors with reset time
- Next scheduled run
- Any job that missed its last window

## Phase 4: Intel Scan (only if time permits)

- `blogwatcher` articles since the pulse window
- Recent PIM items
- News / threat feeds

## Report Structure

1. **Header** — `🔵 TITLE | timestamp`
2. **Git Activity** — repos with commits, one line per repo, latest commit message
3. **Cross-Pulse Digest** — sibling pulse findings in the same window
4. **Cron State** — notable job errors / upcoming runs
5. **Intel** — only if new
6. **Recommended Actions** — concrete next steps
7. **🔍 Checked:** timestamp + sources

## Freshness Rule

Before reporting, use `session_search` to inspect the last pulse output. If nothing has changed since then, respond with `[SILENT]` (agent cron) or empty output (no_agent script).

## QA / CI Pulse Variation

For test-focused agents (Sentry, quality gatekeepers) running a regular sweep, adapt the pulse to focus on **test suite health + divergence tracking** rather than git commits.

### Phase 1: Divergence Check

```bash
cd /path/to/repo
echo "HEAD: $(git rev-parse --short HEAD)"
echo "$(git rev-list --count HEAD..origin/main) behind"
echo "$(git rev-list --count origin/main..HEAD) ahead"
git status --short
```

Log three metrics every cycle: commits behind, ahead, and working tree state. Divergence trending is as important as the absolute number.

### Phase 2: Suite-by-Suite Test Run

Run the core test suite(s) with `-q --tb=short` for compact output. Capture per-suite pass/fail counts and timing. Run suites individually so a failure in one suite doesn't block the others.

**Flaky test protocol:** When a test fails in batch but passes in isolation (`pytest <test_file>` alone), flag it as a transient flake, not a hard regression. Record the pattern across cycles to distinguish persistent vs. one-off flakes.

**Root cause to suspect first — env var leakage.** Tests that fail in batch but pass in isolation are often caused by environment variables from the parent cron process (e.g., `HERMES_CRON_SESSION`, `HERMES_HOME`) leaking into child-test scopes. The cron process sets these vars before spawning pytest, and some test fixtures clean / don't clean them before asserting env-isolated behavior. To confirm: run `pytest <specific_test_file> -v` in a clean terminal — if it passes, the batch-run env is the culprit. Mitigate by adding explicit `monkeypatch.delenv("VAR_NAME", raising=False)` in the test's fixture or by running tests with `env -u HERMES_CRON_SESSION pytest ...` in the cron script. Document any env-leak flakes with the variable name so future pulses recognize the pattern instantly rather than rediscovering it each cycle.

### Phase 3: Test File Relocation Awareness

Check whether test files have moved between directories (e.g., `tests/` → `tests/tools/`). Use `fd` or `find` to locate expected test files, not hard-coded paths. Update sweep paths when upstream reorganizes.

### Phase 4: Coverage Baseline (weekly)

When coverage infrastructure exists (pytest-cov), re-run with `--cov` and compare totals. Report significant drops (>5% in any module) as findings.

### Banded Severity Logic

| Combined Status | Pass Rate      | Divergence  | Next Action                             |
|-----------------|----------------|-------------|-----------------------------------------|
| 🟢 All clear    | >=98%          | <100 behind | Monitor next cycle                      |
| 🟡 Needs work   | >=95% or <200  | 100-200     | Schedule rebase, fix pre-existing gaps  |
| 🔴 Issue found  | <95%           | 200+        | Investigate regressions, rebase urgently|

Use the **most severe** band across both dimensions — high pass rate + high divergence = 🟡, not 🟢. When pass rate drops AND divergence spikes simultaneously, escalate to 🔴 even if neither alone crosses the threshold.

### Pulse Report Structure (QA variant)

1. **Header** — `🔵 SENTRY PULSE (Nth Cycle)` | timestamp
2. **📊 RECAP** — per-suite results with pass counts and timing
3. **🎯 FINDINGS** — new regressions, flaky tests, divergence changes, working tree state
4. **🎯 RECOMMENDED ACTIONS** — concrete next steps (rebase, fix regression, chase push access)
5. **🔍 Checked:** — timestamp + HEAD commit

### Example

```
🔵 **SENTRY PULSE (20th Cycle)** | Sun Jul 12 · 12:00 PM ET
━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 RECAP
✅ Approval 298/298 + deny 10/10 + heartbeat 8/8 — pipeline ordering holding
✅ Tirith 95/95 — autouse platform fixture intact, 20th cycle verified
✅ Hindsight+ContextRefs 132/1s — USERPROFILE monkeypatch holding

🎯 FINDINGS
Divergence: 6 ahead, 67 behind (was 0 at cycle 19 — upstream +67 commits)
Push blocked (403) — 20 consecutive cycles of same pattern
Flaky ACP isolation: test_interactive fails batch (2/11), passes isolation (8/8)

🎯 RECOMMENDED ACTIONS
Rebase to collapse 67-behind divergence
Resolve push access to break 20-cycle loss pattern

━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Checked: Sun Jul 12 · 16:00 UTC | HEAD `5479a317ac`
```

## Example

```
🔵 **the operator's 4h Pulse** | Sun Jul 12 · 6:56 AM ET
━━━━━━━━━━━━━━━━━━━━━━━━
📊 Git Activity (last 4h)
No commits across 105 tracked repos.

📊 Cross-Pulse Digest
Forge Pulse (03:44 EST): committed `5479a317a` — LSP USERPROFILE fix
Scribe Pulse (06:53 EST): created `growth-lead/README.md` (960 lines)

🎯 Cron State
dev-lead-pulse next 7:44 AM · qa-lead-pulse last run error HTTP 429, resets ~8:44 AM

🎯 RECOMMENDED ACTIONS
Monitor qa-lead-pulse after 8:44 AM for 429 recovery
```
