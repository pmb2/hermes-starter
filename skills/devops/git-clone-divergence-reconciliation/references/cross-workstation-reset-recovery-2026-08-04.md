# Cross-Workstation Reset Recovery (worked example: 2026-08-04)

## When to Use
A pulse, watchdog, or agent session discovers that local-only commits (fixes, tests, whole features) silently vanished from a shared repo. Classic signature: `git reflog -8` shows `HEAD@{0}: reset: moving to origin/main` — a workstation synced to upstream and `git reset --hard origin/main` discarded every commit that was never merged upstream. Recurring in the Hermes Agent repo (5th+ occurrence, Jun–Aug 2026). The Aug 4 2026 reset wiped, in one stroke: the `/godmode` feature (handler + dispatch + 11 tests), approval.py Windows cleanup fixes, `scripts/__init__.py`, the cron foreign-venv filter, honcho memo `st_size` key, and cgroup/busy-ack/ACP test fixes.

## Detection (30 seconds)
```bash
git reflog -8 --oneline        # look for "reset: moving to origin/main"
git merge-base --is-ancestor <known-fix-sha> HEAD && echo PRESENT || echo DROPPED
```
- A fix you committed last week that is "not in the tree anymore" → check ancestry, not just `git log` (the commit may exist but be unreachable).
- Regression tests that PASSED last pulse now fail at collection/import → prime suspect.

## Discovery — dangling commits still exist
`git reset --hard` does NOT delete objects (until gc). Recover everything:
```bash
git fsck --no-reflogs --unreachable | grep commit

# Find dangling commits touching a specific file (slow on big repos — time-box or background it):
for c in $(git fsck --no-reflogs --unreachable | awk '/commit/ {print $3}'); do
  git show --stat "$c" 2>/dev/null | grep -q "tools/approval.py" && \
    echo "$(git show -s --format='%h %ad %s' --date=short "$c")"
done | sort

# Exact file content / per-file diff:
git show <sha>:<path>
git show <sha> -- <path>
```

## Restoration
- **Clean cherry-pick**: `git cherry-pick -x <sha>` works even from dangling commits; `-x` records provenance so the source survives the NEXT reset.
- **Test-only recovery**: if the code fix is already upstream but its regression tests were dropped, extract just the test diff (`git show <sha> -- tests/...`) and re-apply. If the test file was restructured upstream (context drift), apply the class manually at the file end — the tests are the spec.
- **Multiple fix iterations**: when several dangling commits touch the same function, read the NEWEST dangling version first for intended structure, then re-implement from the failing tests (TDD — tests ARE the spec) rather than pure archaeology.
- **Commit immediately after verification** — the next reset will wipe it again, but the window shrinks. Run the combined regression before committing; `git log --oneline origin/main..HEAD` afterward shows exactly what you restored.
- **Only commit YOUR restored files** via explicit `git add <paths>`. The working tree may carry ANOTHER lane's active fix (modified files + untracked test) — leave it untouched, flag it in the report.

## Pitfalls
1. **Staged-cherry-pick false positive (bit us Aug 4 2026).** After `git cherry-pick` reports a conflict, the working tree contains the STAGED portion of the cherry-pick. `sed`/`grep`/`read_file` on the working tree then shows the fix as present — you can wrongly conclude "already upstream, abort" and lose it again. ALWAYS check `git status` for staged/unmerged state or `git diff HEAD -- <file>` before concluding a fix already exists. The Aug 4 session produced a wrong "already present" verdict this way; only re-running the failing test corrected it.
2. **`merge-base --is-ancestor` vs dangling tips.** A commit can be an ancestor of a dangling local tip but NOT of HEAD after the reset. Check against reflog tips, not just HEAD.
3. **Namespace-hijack recurrence (Hermes Agent).** Base Python has editable installs (`finance-team`, `deal-finder`, etc.) that inject foreign `src/` dirs into `sys.path` ahead of the repo. A namespace package (no `__init__.py`) is shadowed by ANY regular package (with `__init__.py`) later in the path scan. If `scripts/__init__.py` vanishes (it was a local-only commit!), `import scripts` resolves to the foreign package → `tests/scripts/` collection errors. Diagnostic: `python -c "import sys; [print(i,p) for i,p in enumerate(sys.path)]"` — look for `__editable__...finder` hooks. Fix: restore the `__init__.py`.
4. **Time-box cherry-pick batches.** Run each `git cherry-pick -x` one at a time; on conflict `git cherry-pick --abort` and handle manually. Don't let one conflict block the rest.
5. **A "restored" fix can still be missing pieces.** The venv-filter code was recovered but its regression tests were never upstream — verify code AND tests both exist post-restore.

## Verification Checklist
- [ ] RED reproduced (failing test before restore)
- [ ] Each restored fix group has a passing targeted suite
- [ ] Combined regression green (approval + scripts + hermes_state + feature areas)
- [ ] `git log --oneline origin/main..HEAD` lists exactly the restored commits
- [ ] Other lanes' in-flight work untouched (`git status` diff vs pre-session)
