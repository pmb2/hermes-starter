# Verify Against Upstream — Distinguishing Pre-Existing Failures from Regressions

A concrete "Be a Scientist" pattern used when a test fails on your local branch and you need to know whether **your changes caused it** or it was **already broken upstream**.

## The Core Question

> "Did my change break this test, or was it already failing?"

Testing against your local branch tells you something is broken. Testing against `origin/main` tells you whether it was broken *before* you changed anything.

## The Technique

### 1. Identify the failing test

```bash
python -m pytest tests/path/to/test_file.py -q --no-header -x
```

Note the exact test name and the assertion that fails (line number + expected vs actual).

### 2. Check if the failure is a known pre-existing issue (fast path)

Look at the pulse log or recent session context for a list of pre-existing failures on your platform:
- Windows has well-known pre-existing failures: symlink detection, tempdir path mapping, CRLF bytes_written
- Some tests only fail under specific test-file combinations (combined ACP suites reveal flakiness that individual test runs mask)

### 3. Replace the source file with upstream's version and re-run

```bash
# Checkout the upstream version of the source file
git checkout origin/main -- tools/approval.py

# Re-run the exact same test
python -m pytest tests/path/to/test_file.py::TestClass::test_name -q --no-header -x
```

**Key insight**: You only need to swap the *source file*, not the test file. Tests should be kept local. The test running against upstream's implementation tells you whether the test was already designed to fail.

### 4. Interpret the result

| Local branch | Upstream source | Verdict |
|---|---|---|
| ❌ Fails | ❌ Also fails | **Pre-existing** — not a regression. Upstream baseline is broken too. |
| ✅ Passes | ❌ Fails | **Regression fixed** — your change actually improved the situation. |
| ❌ Fails | ✅ Passes | **Regression** — your change introduced the failure. Investigate. |
| ✅ Passes | ✅ Passes | No issue to begin with — the failure was environmental (stale cache, wrong Python version, missing fixture). |

### 5. Restore your local changes

```bash
git checkout HEAD -- tools/approval.py
```

## When to Use

- **After fixing a test suite**: you get N failures on your branch. Before chasing each one, check which are pre-existing so you don't waste time fixing upstream bugs.
- **Before labelling a fix "necessary"**: if you think your fix addresses a bug, verify it by confirming the failure doesn't exist on upstream. If it does, your fix has value beyond this session.
- **Before rebasing**: knowing which test failures were pre-existing on your branch means you won't attribute them to rebase conflicts.

## Anti-Patterns

- **Don't assume failures are regressions.** Every agent has an instinct to blame their own changes. Check upstream first.
- **Don't skip restoring.** `git checkout HEAD -- <file>` after testing. Leaving upstream's version in place breaks everything else.
- **Don't use `git stash` for this.** Stash affects the whole working tree. A targeted `git checkout origin/main -- <file>` only touches one file, which you can restore cleanly.
- **Don't run the full suite against upstream.** Run only the failing test(s) — you're proving a specific point, not re-certifying the entire suite.
- **Don't skip verifying the upstream theory.** If you *believe* a test is pre-existing but don't actually run it against upstream, you may miss a real regression and deploy broken code.

## Concrete Example (from Forge Pulse @ 2026-07-19)

**Symptom**: `test_symlinked_temp_dir_only_exempts_canonical_target` fails on local `main` (310/312 approval tests pass).

**Hypothesis**: This is a pre-existing Windows failure, not a regression from our local patches (Windows tempdir path fix, lazy-init).

**Experiment**:
```bash
# Run against upstream's approval.py
git checkout origin/main -- tools/approval.py
python -m pytest tests/tools/test_approval.py::TestDetectDangerousRm::test_symlinked_temp_dir_only_exempts_canonical_target -q --no-header -x
# ❌ Fails — same assertion error, same line

# Restore local changes
git checkout HEAD -- tools/approval.py
```

**Conclusion**: Pre-existing failure on upstream too. Not a regression. Confirmed the 2nd failure (`test_verification_cleanup_exemption_rejects_broader_deletions`) the same way.

**Result**: 310/312 tests pass locally, 2 are pre-existing Windows failures. Upstream has the same 2 failures. No regression.
