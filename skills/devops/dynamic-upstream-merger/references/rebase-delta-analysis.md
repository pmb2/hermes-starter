# Rebase Divergence Delta Analysis

Quantitative techniques for assessing how much upstream has changed in files you also modified — and whether a rebase is low-risk or will need careful reconciliation.

## Why This Matters

A commit-count-only divergence check (e.g. "9 ahead, 199 behind") tells you nothing about **file-level risk**. Upstream could have 200 commits that only touch files you never modified (clean rebase), or 3 commits that rewrite the same functions you patched (painful rebase). Quantitative delta analysis gives you the second number.

## Setup

```bash
# Find your merge base — the last commit you share with upstream
MERGE_BASE=$(git merge-base HEAD origin/main)
echo "Merge base: $MERGE_BASE"

# Your local changes since branching
echo "Your files changed:"
git diff --name-only $MERGE_BASE..HEAD | sort
```

## Step 1: Per-File Upstream Delta Size

For each file you modified locally, measure how much upstream changed it:

```bash
# My files
LOCAL_FILES=$(git diff --name-only $MERGE_BASE..HEAD)

for f in $LOCAL_FILES; do
  STAT=$(git diff --stat $MERGE_BASE..origin/main -- "$f" 2>/dev/null | tail -1)
  if [ -n "$STAT" ]; then
    echo "⚠ Both sides: $f — $STAT"
  fi
done
```

**Interpretation:**
- `Both sides: tools/approval.py — 1 file changed, 45 insertions(+), 12 deletions(-)` — upstream made modest changes. Low risk unless they touched the same lines.
- `Both sides: hermes_cli/web_server.py — 1 file changed, 250 insertions(+), 6 deletions(-)` — upstream heavily modified. **High risk** — check function-level overlap (Step 2).
- (no output for a file) — upstream hasn't touched this file since the merge base. **Zero risk** — rebase auto-wins for this file.

## Step 2: Function-Level Overlap Detection

When Step 1 flags a file with significant upstream delta, find out whether upstream touched the same functions you changed:

```bash
# 1. What did we change? (function-level context)
git diff $MERGE_BASE..HEAD -- hermes_cli/web_server.py | grep "^@@" | head -10

# 2. What did upstream change?
git diff $MERGE_BASE..origin/main -- hermes_cli/web_server.py | grep "^@@" | head -10
```

Compare the hunk headers. If they reference different line ranges and function names, you're likely fine. If they overlap, read both diffs:

```bash
# Show upstream diffs for a file
git log --oneline $MERGE_BASE..origin/main -- hermes_cli/web_server.py

# Show what each upstream commit actually changed
for commit in $(git log --oneline --format="%h" $MERGE_BASE..origin/main -- hermes_cli/web_server.py); do
  echo "=== $commit ==="
  git show --stat $commit -- hermes_cli/web_server.py
  git show $commit -- hermes_cli/web_server.py | head -30
done
```

**Safety guideline:** If zero hunk ranges overlap, the rebase is expected clean for that file (barring transitive dependencies — see Pitfalls).

## Step 3: WIP Syntax Pre-Check

Before any rebase with uncommitted changes, verify the working tree compiles/syntax-checks:

```bash
find hermes_cli -name "*.py" | xargs python -c "
import ast, sys
for path in sys.argv[1:]:
    try:
        ast.parse(open(path).read())
    except SyntaxError as e:
        print(f'SYNTAX ERROR: {path}: {e}')
        sys.exit(1)
print('ALL SYNTAX OK')
"
```

For Python repos where only specific files changed, be more targeted:

```bash
python -c "import ast; ast.parse(open('hermes_cli/web_server.py').read()); print('SYNTAX OK')"
```

If the WIP changes are large (100+ lines), also check imports resolve:

```bash
python -c "import hermes_cli.web_server" 2>&1 | head -10
```

## Step 4: Decision Matrix for Per-File Risk

| Upstream Delta in My File | Hunk Overlap? | Recommended Action |
|---------------------------|---------------|-------------------|
| 0 lines (untouched upstream) | N/A | Safe — rebase without concern |
| <50 lines | No | Low risk — rebase with post-verify |
| <50 lines | Yes | Review upstream change. Likely one-branch-accountable (both fixing same area). Need manual resolution. |
| 50-200 lines | No | Moderate risk — rebase, run post-rebase validation |
| 50-200 lines | Yes | High risk — read both diffs before rebasing |
| >200 lines | Any | **Defer or prepare for manual merge** — heavy upstream rewrite in file you changed. Expect non-trivial reconciliation. |

## Step 5: Post-Rebase File-Level Validation

After rebase, validate every file you modified survived:

```bash
# List files changed in the last commit after rebase
git diff --name-only HEAD~1

# For each file you modified pre-rebase
for f in $(echo "$LOCAL_FILES"); do
  if git diff HEAD~1 -- "$f" | grep -q .; then
    echo "✅ $f changed in last commit (fix applied)"
  else
    echo "⚠ $f NOT in last commit — may have been lost"
  fi
done
```

## Quick One-Liner Summary

```bash
MERGE_BASE=$(git merge-base HEAD origin/main)
echo "Divergence: $(git rev-list --count HEAD..origin/main) behind, $(git rev-list --count origin/main..HEAD) ahead"
echo "Files both sides touched:"
for f in $(git diff --name-only $MERGE_BASE..HEAD); do
  git diff --stat $MERGE_BASE..origin/main -- "$f" 2>/dev/null | tail -1
done | sort -t'|' -k2 -rn
```

## Pitfalls

- **--stat counts lines, not semantic impact.** An upstream 250-line change may be 248 lines of test refactoring and 2 lines of production code. Always check hunk ranges (Step 2) before concluding risk level.
- **Hunk ranges can mismatch and still conflict.** If upstream added a function before your function, git's three-way merge handles it fine in most cases. Only overlapping hunk ranges (both editing the same 20-line function) guarantee a conflict.
- **--name-only vs --name-status.** `--name-only` lists filenames; `--name-status` also shows the type of change (M=modified, A=added, D=deleted). Use `--name-status` when you need to know if upstream deleted a file you modified (modify/delete conflict).
- **Python syntax check is not an import check.** `ast.parse` confirms the file parses as valid Python, but doesn't catch missing imports. For that, run `python -c "import X.Y"` (which actually loads the module — so only safe when you're not in the middle of a working tree you haven't yet rebuilt).
- **Rebase with staged-but-uncommitted WIP.** `git stash` the WIP before rebasing, then `git stash pop` after. Rebasing with a dirty working tree is risky and git warns against it. Use the syntax pre-check before stashing to catch issues first.
- **Windows CRLF→LF line-ending diffs inflate delta counts.** If upstream uses LF and your working tree writes CRLF, `git diff --stat` may show every line as changed. Normalize with `git config core.autocrlf input` before running delta analysis.
