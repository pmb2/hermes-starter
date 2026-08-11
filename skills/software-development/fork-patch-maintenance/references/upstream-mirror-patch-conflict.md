# Upstream Mirror-Patch Conflict — Case Study

> Case study from the Hermes Agent Forge pulse (@ 2026-07-27, 1881 behind).
> Demonstrates upstream independently fixing the same bug your fork patched,
> but with a different approach — creating a rebase conflict of approaches.

## Background

The Hermes Agent fork carries a Windows path normalization patch in `tools/approval.py` at `_is_verification_artifact_cleanup()`: it uses `str(Path(...)).as_posix()` instead of naive `os.path.join()` to ensure forward-slash paths on Windows.

Upstream later independently added their own cross-platform fix in the same function — a more comprehensive approach with separator normalization and drive-letter injection handling.

## The Conflict

**Our local fix** (from `5b4e68f66f` / `4aee478262`):
```python
if operand != os.path.join(temp_dir, basename):
```

**Upstream's independent fix** (at `origin/main`):
```python
expected = os.path.join(temp_dir, basename)
operand_normalised = operand.replace("\\", "/").rstrip("/")
expected_normalised = expected.replace("\\", "/").rstrip("/")
if (operand_normalised != expected_normalised
        and not os.path.splitdrive(operand)[0]):
    drive = os.path.splitdrive(expected_normalised)[0]
    if drive and operand_normalised.startswith("/"):
        operand_normalised = drive + "/" + operand_normalised.lstrip("/")
if operand_normalised != expected_normalised:
    return False
```

Our fix was at a different line in the same function (L1976 vs L2026 upstream). Upstream's approach is more thorough — it handles drive-letter injection and separator normalization separately, while keeping the security invariant (no `normpath`/`abspath` that would defeat path-traversal checks).

## Rebasing This Conflict

On rebase, the two fixes will conflict because:
1. Both modify the same function (`_is_verification_artifact_cleanup`)
2. Both change the path comparison logic
3. Our `as_posix`-style fix and upstream's separator-normalization approach overlap at the comparison point

**Resolution strategy**: Adopt upstream's approach (it's more comprehensive) and verify our edge cases (the `str(Path(...)).as_posix()` pattern for forward-slash normalization from the original bug) are covered.

## Detection

```bash
# Check if upstream fixed the same area
git diff origin/main -- tools/approval.py | grep -B5 -A15 "os.path\|normpath\|realpath\|as_posix\|replace.*\\\\\\\\"
```

## Key Numbers

| Metric | Value |
|--------|-------|
| Fork local path fix location | L1976 (path comparison) |
| Upstream path fix location | L2026 (in `_is_verification_artifact_cleanup`) |
| Upstream approach | Separator normalize + drive-letter injection + security invariant |
| Our approach | `.as_posix()` path normalization |
| Rebase outcome | Need to reconcile approaches, not skip either |

## Lesson

When both fork and upstream independently fix the same bug, compare both approaches consciously. Document which edge cases each covers. On rebase, you may need to merge approaches — not just pick one. The `git diff origin/main -- <file>` with context grep is the fastest way to detect this situation.
