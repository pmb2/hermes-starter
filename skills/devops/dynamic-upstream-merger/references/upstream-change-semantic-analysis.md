# Upstream Change Semantic Analysis

Beyond counting commits and checking hunk overlap — understanding *what* upstream is doing and how it interacts with your local fixes semantically, not just textually.

## Why This Matters

A zero-textual-conflict rebase can still silently break your local fixes if upstream reorganized the same pipeline. Conversely, a large upstream delta in a file you touched may be perfectly safe if upstream's changes are in a different subsystem within that file. Commit-count and hunk-overlap analysis (see `rebase-delta-analysis.md`) tells you *how much* changed; this reference tells you *what* changed and whether it matters.

## Methodology

### Step 1: Identify Upstream Refactors in Your Files

When divergence is large (>100 behind), check if upstream made structural changes to your modified files:

```bash
# 1. Get the merge base
MERGE_BASE=$(git merge-base HEAD origin/main)

# 2. List upstream commits touching a file you modified, with stats
echo "=== Upstream changes to tools/approval.py ==="
git log --oneline $MERGE_BASE..origin/main -- tools/approval.py

# 3. Get per-commit line counts
for commit in $(git log --oneline --format="%h" $MERGE_BASE..origin/main -- tools/approval.py); do
  STAT=$(git show --stat $commit -- tools/approval.py 2>/dev/null | tail -1)
  DESC=$(git log --oneline -1 $commit)
  echo "$DESC | $STAT"
done
```

**Key signal:** A single commit with +500/-50 lines flags a *refactor*, not a routine change. A refactor means upstream restructured the subsystem — your local fixes need semantic review, not just conflict resolution.

### Step 2: Read the Upstream Refactor's Intent

Before assessing interaction with your local fixes, understand what the refactor does:

```bash
# Full diff of the refactor commit for your file
git show b90dbac1d6 -- tools/approval.py | head -100

# Commit message body for context
git log --format="%B" -1 b90dbac1d6
```

Ask these questions while reading:
1. **What functions were moved/added/renamed?** — If upstream extracted `_execution_flag_findings()` from inline regex, any local fix that touches the old regex patterns needs updating.
2. **Was a regex or pattern engine changed?** — Regex changes in approval/safety logic are high-risk semantic interactions. A change to `_CMDPOS` (command detection position regex) can change which strings are classified as shell commands — your local fix to `_is_verification_artifact_cleanup()` may break if the regex no longer captures the same positions.
3. **Was a pattern removed or moved to a different engine?** — Upstream removing `-e/-c flag` patterns from `DANGEROUS_PATTERNS` and moving them to a structural parser changes the entire detection pipeline. Your local fix that relied on those patterns being in `DANGEROUS_PATTERNS` is now dead code or miscalibrated.

### Step 3: Categorize Each Local Fix's Interaction

For each local fix in a file upstream refactored, assign an interaction category:

| Category | Meaning | Example from This Session |
|----------|---------|--------------------------|
| **Same-zone** | Local fix and upstream refactor touch overlapping functions/lines | Our `_is_verification_artifact_cleanup` (line ~1434) and upstream's `_CMDPOS` regex change (line ~363) — different functions, same file, low line proximity |
| **Adjacent-zone** | Changes in the same function or adjacent functions | Both editing `_check_sudo_stdin_guard` — medium risk |
| **Cross-zone** | Changes in completely different subsystems within the same file | Our lazy-init fix at line ~1497/1724 and upstream's `DANGEROUS_PATTERNS` changes at line ~632 — low risk (different subsystems) |
| **Pipeline-order-dependent** | One fix's behavior depends on the order another runs | Our pipeline ordering fix (hermes_home→user_home on line 835) — if upstream reorders that pipeline, our pre-rebase fix silently becomes ineffective even with 0 conflicts |
| **Dependency-change** | Upstream renamed/removed a function your local fix calls | If upstream renamed `_is_verification_artifact_cleanup()` and our fix references it by old name |

**Assessment heuristic:**
- All cross-zone → rebase is low risk (just line-number shifts)
- Any same-zone or adjacent-zone → manual review needed before rebase
- Pipeline-order-dependent → **critical** — the fix may survive the merge textually but be semantically dead

### Step 4: Check for Semantic Regression Vectors

Semantic regressions are changes that survive rebase textually (0 merge conflicts) but no longer work correctly:

**Upstream reordered a pipeline your fix depends on:**
```bash
# Before rebase: verify what order your fix expects
grep -n "hermes_home\|user_home\|backslash" tools/approval.py | head -10

# After rebase: check the same pipeline is still in your order
grep -n "hermes_home\|user_home\|backslash" tools/approval.py | head -10
```

**Upstream changed a regex your fix interacts with:**
```bash
# Before rebase: note the regex pattern
grep -n "_CMDPOS\|_WRITE_TARGET_BOUNDARY" tools/approval.py

# After rebase: the pattern may have changed semantics even if the variable name is the same
```

**Test coverage shift:**
```bash
# Upstream may have added/removed tests. Compare test counts.
git checkout origin/main -- tools/approval.py tests/tools/test_approval.py
python -m pytest tests/tools/test_approval.py --collect-only 2>/dev/null | grep "selected"
# Restore your working tree
git checkout HEAD -- tools/approval.py
```

### Step 5: Make the Rebase Decision

| Finding | Action |
|---------|--------|
| All local fixes are cross-zone to upstream changes | Rebase now — low risk despite large upstream delta |
| Any local fix is same-zone or adjacent-zone | Read the upstream diff carefully. Try trial rebase on throwaway branch. Prepare for manual conflict resolution. |
| Pipeline-order-dependent fix detected | **Must validate post-rebase** even with 0 textual conflicts. Test suite + git diff against pre-rebase version required. |
| Upstream removed a function/capability you rely on | Rebase will likely fail at compile/test time. May need to re-implement your fix on the new upstream architecture before rebasing. |
| Upstream's refactor duplicates your local fix's purpose | Your fix may be upstream's exact behavior now. Test first, then consider dropping the local fix. |

## Case Study: This Session's Approval.py Refactor

```bash
# Upstream commit b90dbac1d6: +574/-26 lines
# Changes:
#   1. _CMDPOS regex: removed `;&|` from start-position pattern
#      (quote-aware _mark_command_starts pass now handles this)
#   2. DANGEROUS_PATTERNS: removed interpreter -e/-c and heredoc patterns
#      (moved to structural _execution_flag_findings())
#   3. Added _REMOVED_PATTERN_KEY_ALIASES for stored-approval backward compat

# Local fixes in the same file:
#   A. lazy-init guard at line ~1497/1724 — cross-zone (different subsystem)
#   B. _is_verification_artifact_cleanup Windows path fix at line ~1434 — 
#      adjacent-zone to _CMDPOS regex (same general detection pipeline, 
#      but different functions so low probability of direct conflict)
#   C. Pipeline ordering (hermes_home→user_home~line 883) — 
#      pipeline-order-dependent, different subsystem from refactor

# Assessment: Cross-zone for A and C. Adjacent-zone for B (low risk).
# Line-number shift expected (~500+ lines added above line 1434).
# Post-rebase validation: verify pipeline ordering and test results.
```

## Pitfalls

- **Don't treat line-number proximity as conflict likelihood.** A +574-line insertion may push every subsequent line number up by ~574, but the functions themselves are untouched. The conflict comes from function overlap, not line proximity.
- **Don't skip reading the commit message.** The message body (especially co-authored-with references) often explains WHY the refactor happened, which determines whether it interacts with your fix.
- **Semantic regression ≠ test failure.** A pipeline-order-dependent fix that silently becomes ineffective won't necessarily cause test failures if the test suite doesn't exercise the ordering. Always run `git diff HEAD~N -- <fix-file>` post-rebase to confirm the fix's actual logic is intact.
- **Regex changes in safety-critical code are high-risk.** Upstream changing `_CMDPOS` or `_WRITE_TARGET_BOUNDARY` can change which commands pass through the safety filter. Your local `_is_verification_artifact_cleanup` may work with the old regex but not the new one — and vice versa. Always re-test the exact edge cases your fix addresses.
