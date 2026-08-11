# Pulse Cron Prompt Template

**Problem this solves:** Pulse cron prompts that say "check git activity" fail because the agent defaults to 3 repos it happens to know about. Agents follow their prompt literally — vague instructions produce shallow results. Every pulse prompt must contain **exact executable commands**, not high-level descriptions.

This template encodes the canonical structure: **work context FIRST, intelligence SECOND**. It was developed from the June 17, 2026 fix that rewrote 5 pulse cron prompts that were only checking blogwatcher/PIM and missing real git/session work.

## When to Use

- Creating a NEW pulse cron job
- Auditing an existing pulse prompt that produces shallow or intelligence-only output
- Any cron job whose purpose includes "what did the user do today"

## Template

```
You are the [Pulse Name] — [time/schedule and purpose].

## CRITICAL: Work context FIRST, intelligence SECOND

Old behavior (broken): described what to check without saying HOW — agent defaulted
to minimal checks. New behavior: EXACT commands inline for every scan.

## PHASE 1: Work Summary (DO THIS FIRST)

### 1A: Dynamic Git Scan — ALL repos

Use the DISCOVERY LOOP, NOT a hardcoded list. New repos appear without warning:

**Primary approach (fast — parallel scan of all repos):**
```bash
find ${MY_REPOS} -maxdepth 2 -name .git -type d -print0 2>/dev/null | \
  xargs -0 -P4 -I{} bash -c '
    d="$(dirname "{}")"
    repo=$(basename "$d")
    count=$(git -C "$d" log --oneline --since="[WINDOW]" 2>/dev/null | wc -l)
    if [ "$count" -gt 0 ]; then
      printf "[%d] %s\n" "$count" "$repo"
      git -C "$d" log --oneline --since="[WINDOW]" 2>/dev/null | head -5
    fi
  '
```

**Fallback (serial — for no_agent scripts or when find unavailable):**
```bash
for d in ${MY_REPOS}/*/; do
  repo=$(basename "$d")
  if cd "$d" 2>/dev/null; then
    commits=$(git log --oneline --since="[WINDOW]" 2>/dev/null | wc -l)
    if [ "$commits" -gt "0" ]; then
      latest=$(git log --oneline -1 --format="%as %an: %s" 2>/dev/null)
      echo "  $commits commit(s) in $repo: $latest"
    fi
    cd - >/dev/null
  fi
done
```

[WINDOW] = "24 hours ago" for daily, "4 hours ago" for 4h pulse, "7 days ago" for weekly.

**⚠️ Performance edge case:** On this host (~126 repos), a serial `for d in .../` loop iterating all repos one-by-one can exceed `terminal()`'s timeout and get killed (exit 15/SIGTERM). The parallel `find + xargs -P4` approach is preferred — it completes in under 5s. When only a serial loop is feasible, cap the search with `find ... -mtime -7` or restrict to P0/P1 repos.

**⚠️ Use `cd "$d" && git`, NOT `git -C "$d"`.** On MSYS/Windows, `git -C` emits exit 128 and silently produces no output when a repo contains a `.git.broken.*` directory alongside its `.git` dir (known git-for-windows edge case after failed migration attempts). The `ghl` repo at `ghl/.git.broken.2026-04-19` is confirmed. The `cd "$d"` approach works every time.

### 1B: Cross-Pulse Digest

Read the daily digest for outputs from OTHER pulses that ran alongside:

```bash
grep -i -A3 "Self-Healing\|dev-lead\|qa-lead\|integration-lead\|docs-lead\|skills-lead\|[other-pulse-names]" \
  "${MY_REPOS}/_project/daily-digest/$(TZ='America/New_York' date +%Y-%m-%d).md" 2>/dev/null
```

### 1C: Session Check

```bash
# Use session_search browse mode — shows source labels (discord vs cron)
session_search()
# Look for source="discord" or source="cli" — those are user sessions
```

## PHASE 2: Intelligence Brief (SECONDARY — run AFTER work summary)

[Blogwatcher, PIM, YouTube checks — see Phase 1 of intelligence-pulse skill]

## FRESHNESS RULE

Use session_search to check your last output. If genuinely nothing changed, stay
SILENT — no "nothing new to report" messages. Only deliver when there's actual news.

## DELIVERY FORMAT

Under [char limit] chars. Structure:

```
📡 [Pulse Name] — [Date]

## Day's Work
| Project | Activity |
|---------|----------|
| [repo 1] | [commits + summary] |

## Intelligence Brief
[Top N items max — flag what matters, skip noise]

## Focus
[ONE specific action]
```
```

## Implementation Rules

1. **ALWAYS inline the exact bash for-loop.** Never write "check recent commits" without the loop — the agent cannot be trusted to discover repos on its own.
2. **Time windows must match the pulse cadence:** 4h pulse = "4 hours ago", daily = "24 hours ago", weekly = "7 days ago".
3. **Cross-pulse grep must name the specific other pulses to check.** Vague "check other pulses" = nothing checked.
4. **Work summary comes BEFORE intelligence.** If both are present, work comes first.
5. **Freshness check via session_search** before delivering — prevents duplicate reports.

## Verification

After updating a pulse prompt, verify by:
1. Letting the cron job fire once (or running it manually via `cronjob action='run'`)
2. Checking the output contains repos with commits (not just blog articles and PIM stats)
3. Checking that cross-pulse findings appear if other pulses ran
