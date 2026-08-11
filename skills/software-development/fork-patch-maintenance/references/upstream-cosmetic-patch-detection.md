# Upstream Cosmetic Patch Detection — Case Study

> Case study from the Hermes Agent Forge pulse (@ 2026-07-27, 1881 behind).
> Demonstrates how upstream can appear to adopt a fork's patch via a comment-only change.

## Background

The Hermes Agent fork (10 ahead, 1881 behind origin/main) carries a critical patch in `tools/approval.py`: lazy-init for `load_permanent_allowlist()` with a `_permanent_allowlist_loaded` flag. This patch defers config file reading from module-import time to first access, preventing test pollution when `HERMES_HOME` is set after import.

## The Trap

At some point between the fork point and the 1881-behind mark, upstream changed the comment at the bottom of `tools/approval.py` from:

```python
# Load permanent allowlist from config on module import
load_permanent_allowlist()
```

to:

```python
# Permanent allowlist loaded lazily — first access triggers load_permanent_allowlist()
# so config is read after HERMES_HOME isolation, not at import time.
load_permanent_allowlist()
```

The comment now describes lazy-init behavior — but the function is **still called unconditionally at module scope**. The comment is aspirational; the code is unchanged.

## Detection Technique

```bash
# Step 1: Check if upstream has our actual marker
git show origin/main:tools/approval.py | grep -c "_permanent_allowlist_loaded"
# Result: 0 — upstream doesn't have the guard flag at all

# Step 2: Check if upstream still calls the function at import
git show origin/main:tools/approval.py | grep -c "load_permanent_allowlist()"
# Result: 2 — the function is still called at module scope (both a test ref + actual call)

# Step 3: Compare module-bottom lines
git show origin/main:tools/approval.py | tail -5
# Result shows the comment change but load_permanent_allowlist() still at module bottom

# Step 4: Confirm our actual lazy-init still exists locally
grep -n "_permanent_allowlist_loaded" tools/approval.py
# 4 refs: flag definition + guard in load_permanent_allowlist + 2 guard calls
```

## Why This Matters

1. **False sense of safety**: On rebase, seeing "loaded lazily" in the upstream comment could tempt you to skip re-applying the lazy-init patch.
2. **Silent regression**: The original test pollution bug would return — `load_permanent_allowlist()` reads config at import time, which happens before test fixtures can set `HERMES_HOME`.
3. **Detection is straightforward**: The three-step grep chain above takes 30 seconds and gives definitive answer.

## Lesson

Always verify upstream changes at the **behavioral level**, not the textual level. A comment change is not a code change. The three-step detection technique — check your flag, check the old function call, compare the bottom lines — is the minimum bar for confirming an upstream mirror-fix is real.

## Key Numbers

| Metric | Value |
|--------|-------|
| Fork point | ~1881 commits behind origin/main |
| Our lazy-init flag refs | 4 (`_permanent_allowlist_loaded`) |
| Upstream has our flag | No (0 matches) |
| Upstream still calls at import | Yes (2 matches) |
| Upstream comment change | Cosmetic only |
