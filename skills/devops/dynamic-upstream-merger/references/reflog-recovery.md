# Systematic Reflog Recovery After `git reset --hard`

> **Trigger**: `git reset --hard origin/main` (or any destructive reset) orphaned your local commits.
> **Use when**: A defensive branch wasn't available and you need to recover from git reflog.

## Overview

After `git reset --hard origin/main`, your local commits still exist in the **reflog** — they're not garbage collected until the reflog entries expire (default 90 days) or `git gc` runs. This document covers the systematic recovery workflow.

## Phase 1: Find Orphaned Commits

```bash
# 1. List all reflog entries with commit hashes and messages
git reflog --date=iso --format="%H %gd %gs" | head -50

# The output shows every HEAD movement. Look for "commit:" entries
# that happened before the destructive reset.
```

Key patterns in the reflog:
- `reset: moving to origin/main` — the destructive event
- `commit: fix(approval): ...` — your lost commits
- `commit: refactor(web): ...` — more lost commits
- `rebase (start): checkout origin/main` — previous rebase attempts

## Phase 2: Identify Which Commits to Recover

Not every orphaned commit is worth recovering. Classify each:

```bash
# 1. Check what files each commit touched (to assess risk/relevance)
git show <sha> --stat

# 2. Read the commit message and diff
git show <sha> --no-stat

# 3. Categorize:
#    CRITICAL — functional fix (lazy-init, test compat, platform fix)
#    USEFUL   — refactor, new feature, documentation
#    STALE    — merge-artifact cleanup, superseded by upstream, rebase artifact
```

**Typical recovery priorities:**
| Priority | Type | Example |
|----------|------|---------|
| 1st | Lazy-init / module-level side-effect fixes | `fix(approval): lazy-init load_permanent_allowlist` |
| 2nd | Test compat / platform fixes | `fix(dev-lead): ACP CRLF bytes_written` |
| 3rd | Non-conflicting feature commits | `refactor(web): Hermes One model library CRUD` |
| 4th | Low-risk UX/feature adds | `feat: reaction re-prompt` |
| Skip | Merge artifact cleanup | `fix(web): remove merge conflict artifact` (artifact gone in new HEAD) |
| Skip | Already-covered-by-working-tree | qa-lead recovery (working tree already has the changes) |

## Phase 3: Check Working Tree First

Before cherry-picking, check if the working tree already has uncommitted recovery work:

```bash
git status --short
git diff --stat
```

**Rule**: If the working tree already has the changes from some orphaned commits, **commit the working tree first**, then cherry-pick the remaining commits on top. This avoids duplicating work and simplifies cherry-pick ordering.

```bash
git add <files>
git commit -m "recover(dev-lead): summary of working-tree recovery"
```

## Phase 4: Cherry-Pick in Order

Cherry-pick commits from oldest to newest (chronological order, not reverse reflog order):

```bash
# Cherry-pick one at a time (not batch)
git cherry-pick <oldest-sha>
git cherry-pick <second-sha>
git cherry-pick <third-sha>
```

**Why one at a time:** Batch cherry-picks (`git cherry-pick A..D`) stop at the first conflict, and you have to abort/recover the entire batch. Individual cherry-picks let you handle each commit independently.

## Phase 5: Handle Conflicts

When a cherry-pick conflicts:

```bash
# 1. Inspect the conflict
git diff --name-only --diff-filter=U
git diff              # view conflict markers

# 2. Decide: skip or resolve?

# A commit is skippable if:
# - It fixes something that no longer exists (merge artifact gone)
# - It's superseded by a newer upstream change
# - The same fix is already in the working tree commit
git cherry-pick --skip

# A commit is worth resolving if:
# - It's a CRITICAL fix (lazy-init, platform compat)
# - The fix code doesn't exist in upstream
git mergetool          # or manually resolve
git add <resolved-files>
git cherry-pick --continue
```

**Common skippable patterns:**
- Merge artifact cleanup — the artifact was specific to an old rebase state
- `.gitignore` additions that upstream already has
- `package-lock.json` changes (upstream lockfile is newer)
- Stale qa-lead branch recovery (was already obsolete)

## Phase 6: Verify Recovered Code

After all cherry-picks:

```bash
# 1. Check commit chain
git log --oneline -10

# 2. Verify the fix code is active (critical fix only)
grep -n "<fix-pattern>" <fix-file>

# 3. Run the relevant test suite
python -m pytest tests/path/to/test.py -x -q --no-header

# 4. Count ahead/behind
git rev-list --count HEAD..origin/main
git rev-list --count origin/main..HEAD
```

## Phase 7: Push (if applicable)

```bash
git push origin main
```

**Caution:** Only push after testing. The recovered commits run against the NEW upstream codebase, which may have changed around them. Test failures are expected if upstream refactored the same area.

## Pitfalls

- **Reflog IS ephemeral** — `git gc`, `git reflog expire`, or 90 days of inactivity will delete reflog entries. Recover within the same session or the same day after the reset.
- **`git reset --hard origin/main` at 05:15, recovery at 09:00** — reflog entries are typically still available for days. But if another `reset` or `checkout` happened in between, the reflog gets pushed down. The oldest entries may be lost.
- **Dependency ordering matters** — if commit A adds a helper function and commit B uses it, cherry-pick A first. If you cherry-pick B first, you get a "symbol not found" error (though typically at runtime, not during cherry-pick itself).
- **Cherry-pick conflicts may hide semantic issues** — a clean cherry-pick doesn't mean the fix still works. Upstream may have changed the code path the fix targets. Run the test suite.
- **Simultaneous working tree + reflog recovery** — if someone started manually recreating fixes in the working tree (adding back the same code from memory), you may have duplicate effort. Check the working tree diff against the orphaned commit's diff to detect overlap.
- **`os.path.realpath('/tmp')` on Windows** — After a reset, if you're on Windows, the upstream code may have regressed Windows path handling that your orphaned fix addressed. See `karpathy-principles/references/windows-realpath-path-trap.md` (Approach D) for the reorder-checks fix pattern.
