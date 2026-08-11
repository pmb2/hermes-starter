# Divergence Pulse Analysis — Case Study

A worked example from the Forge pulse check of Hermes Agent (Jul 28, 2026), showing how to assess rebase risk during a routine status check when upstream is in a performance sprint.

## Scenario

- Fork: 11 local commits ahead, 2274 behind origin/main
- Upstream: 305 commits in the last 24 hours (performance wave: token accounting rewrite, wire client reuse, dashboard optimization)
- Working tree: clean

## Step-by-Step

```bash
# 1. BEHIND / AHEAD
git rev-list --count HEAD..origin/main     # 2274
git rev-list --count origin/main..HEAD     # 11

# 2. AGGREGATE CONFLICT HEATMAP
# Compare local changes to upstream's recent wave
MY_FILES=$(git diff origin/main..HEAD --name-only | sort -u)
UPSTREAM_FILES=$(git log origin/main --name-only --since="24 hours ago" | \
  grep -v '^$' | grep -v '^commit\|^Author\|^Date\|^Merge\|^    ' | sort -u)

# Raw overlap count
comm -12 <(echo "$MY_FILES") <(echo "$UPSTREAM_FILES") | wc -l
# → 867 — critical level

# Core Python overlap only
comm -12 <(echo "$MY_FILES") <(echo "$UPSTREAM_FILES") | grep '\.py$' | wc -l
# → ~400+ Python files overlap

# 3. PER-FILE DELTA ON CRITICAL FILES
for f in tools/approval.py hermes_cli/web_server.py gateway/run.py \
         hermes_cli/model_switch.py gateway/slash_commands.py \
         agent/chat_completion_helpers.py hermes_state.py; do
  echo "--- $f ---"
  echo "Our diff: $(git diff origin/main..HEAD -- "$f" --stat | tail -1)"
  echo "Upstream: $(git log origin/main --oneline -- "$f" --since='48 hours ago' | wc -l) commits"
done

# 4. FUNCTION-LEVEL OVERLAP CHECK
# Check if our hunk ranges overlap with upstream's on the most risky file
git diff origin/main..HEAD -- tools/approval.py | grep '^@@' | head -10
git log origin/main -p -- tools/approval.py --since='48 hours ago' | grep '^@@' | head -10

# 5. DIVERGENCE VELOCITY
# Previous check (08:00 ET): 1978 behind
# Current check (16:00 ET): 2274 behind
# Delta: 296 in 8 hours = 37 commits/hour
echo "Velocity: ~37 commits/hour upstream — critical"

# 6. NEW CONFLICT ZONE DETECTION
# Check if files recently touched by local patches were also modified upstream
git log origin/main --oneline --since="48 hours ago" -- \
  hermes_cli/model_switch.py gateway/slash_commands.py
```

## Interpretation

1. **867 overlapping files** at critical level → upstream is actively rewriting areas we patched. The overlap includes CI, docs, infra — but Python-only overlap was also critical (~400+).

2. **Key conflict zones** (files with BOTH local patches AND upstream perf-wave changes):
   - `agent/chat_completion_helpers.py` — upstream: wire client reuse (+899 lines). Our: BackendIdentity refactor, Nous Portal removal
   - `hermes_state.py` — upstream: token accounting rewrite (+882 lines). No local changes → clean supersede
   - `tools/approval.py` — our local: lazy-init + Windows path fix (+510 lines). Upstream: docker daemon + rm detection
   - `gateway/slash_commands.py` — our local: OmniRoute lock (+15 lines). Upstream: removed `_handle_context_command` + delegation display
   - `hermes_cli/model_switch.py` — our local: OmniRoute bypass guard (+805 lines). Upstream: removed excluded_providers, Vertex auth, provider grouping

3. **New file conflicts** (not previously tracked): `model_switch.py` and `slash_commands.py` from the Sentry OmniRoute lock commit.

4. **Divergence velocity**: 37 commits/hour, compounding by ~300/day. Each day the rebase cost increases nonlinearly.

## Outcome

The correct action was: **do NOT rebase in this pulse session alone**. The rebase needs:
- Pre-extraction of the Hermes One model library from `web_server.py` (2,189-line conflict zone with zero upstream presence)
- Cherry-pick of the CDP startup fix (upstream commit 731aa0ccc9, not in local branch)
- Dedicated rebase session with a clear conflict map, not a drive-by attempt mid-pulse
