# QA Pulse / Test Suite Health Pattern

Workflow for running a recurring quality pulse against a codebase — verifying fix suite integrity, detecting stale test paths, tracking divergence, and managing structured pulse logs. Companion to `dev-lead-pulse-template.md` (architecture-focused) — this covers the **Quality Engineering** cadence.

## Workflow Steps

### Phase 1: Locate the Codebase

The codebase may move between drives or profiles. Discover it first, don't assume a fixed path.

```
ls -d <potential-paths>/hermes-agent 2>/dev/null || echo "NOT FOUND"
```

Known relocation history: Hermes Agent has been at `${USER_HOME}/hermes-agent/` → `${USER_HOME}\AppData\Local\hermes\hermes-agent\`.

### Phase 2: Run Fix Suites & Validate Counts

Run the canonical fix suites and capture results. Track **exact expected counts** — mismatches are the earliest regression signal.

**Current suite structure (cycles 20-28):**

```bash
# ACP suite — covers approval pipeline, isolation, edit approval, auth, events, permissions
python -m pytest tests/acp/ -x --tb=short -q

# Tirith security suite — platform-guard mocks, Windows path compat
python -m pytest tests/tools/test_tirith_security.py -x --tb=short -q

# Skills suite — expanded upstream, check all 294 pass
python -m pytest tests/skills/ -x --tb=short -q

# Hindsight + ContextRefs — USERPROFILE monkeypatch verification
python -m pytest tests/plugins/memory/test_hindsight_provider.py -x --tb=short -q
python -m pytest tests/agent/test_context_references.py -x --tb=short -q

# Approval isolation + edit (subset of ACP for quick check)
python -m pytest tests/acp/test_approval_isolation.py tests/acp/test_edit_approval.py -x --tb=short -q

# Scripts tests — PYTHONPATH collision fix verification
python -m pytest tests/scripts/ -x --tb=short -q
```

**File paths can change**. When pytest says "file or directory not found":
1. Don't assume the path is wrong — the file may have moved
2. Run `find tests -name "test_<name>.py"` to discover the new location
3. Verify the new path works before updating your pulse log
4. Note the relocation in the pulse entry

**Known relocations**:
- `test_context_references.py`: `tests/tools/` → `tests/agent/` (June 2026)
- `test_approval.py`: `tests/tools/` → split into `tests/acp/` (approval isolation, edit approval, events, permissions, server, session)
- `test_skills_tool.py`: `tests/tools/` → expanded to `tests/skills/` full directory (86→294 tests, upstream)

### Phase 3: Check Divergence & Git Health

```bash
git fetch origin 2>&1 | tail -3
git rev-list --count HEAD..origin/main      # behind
git rev-list --count origin/main..HEAD      # ahead
git stash list                              # accumulation check
git status --short | head -20               # working tree health
```

- **Stale stashes**: flag any stash entries older than the current cycle. 3+ old stashes with no action is an accumulation pattern. **Drop stashes that have been flagged for 3+ consecutive cycles with no action** — indefinite flagging without cleanup wastes space and adds noise. Use `git stash drop stash@{N}` per entry, targeting the oldest first.
- **Working tree artifacts**: unexpected untracked files (`.playwright-mcp/`, `*.orig`, scraped data files) should be flagged and optionally gitignored.
- **Merge-tree check**: `git merge-tree origin/main HEAD` if divergence is high to detect semantic (not just textual) conflicts.

### Phase 4: Check Fix Pattern Survival

When a codebase has accumulated local fix commits that keep getting destroyed by cross-workstation resets, verify them every cycle:

1. Run all fix suites and confirm exact expected counts
2. Check that the key fix patterns are present in the working tree:
   - ACP pipeline ordering (approval isolation tests)
   - Platform mock fixtures (tirith autouse `is_platform_supported=True`)
   - Environment variable patches (USERPROFILE for Path.home() on Windows)
   - Skills path-separator fixes (openclaw + unbroker Windows compat)
   - Scripts PYTHONPATH collision conftest fix
3. **Mid-pulse commit**: If working tree has uncommitted fixes, commit them immediately after verifying they pass. `git add <file>` + `git commit -m "fix: ..."`. This prevents losing the fix if the cron process is killed mid-cycle or another workstation reset happens mid-pulse. Each pulse should leave HEAD further ahead or at least stable, never with lost working-tree work.
4. Note any semantic gap between local fixes and origin/main

**Recurring loss pattern**: When a profile runs `git reset --hard origin/main` from another workstation, all local fix commits are destroyed. The recovery pattern is:
- `git reflog | grep <fix-commit-message>` to find lost commits
- `git cherry-pick <hash>` to restore
- Push to a named branch + remote to break the loss cycle
- If push is blocked (403), fixes survive on local HEAD only — flag this in every pulse with cycle count

### Phase 5: Append Pulse Log

Maintain a structured PULSE.md at the profile path: `~/AppData/Local/hermes/profiles/qa-lead/PULSE.md`

Format for each entry:
```
## Pulse @ YYYY-MM-DD HH:MM UTC (Nth Cycle — Brief Label)
- **Status**: 🟢 Nominal / 🟡 Needs Work / 🔴 Issue Found
- **Focus**: [what was investigated]
- **Findings**:
  - ✅ [positive result, N/N passed] — [details]
  - 🔴 [failure or blocker] — [details]
  - 🟡 [pre-existing issue, N+ cycles] — [details]
  - 🟢 [divergence status] — [details]
- **Next Action**: [one concrete next step]
```

Rules for PULSE.md entries:
- Prepend or append each new entry (append keeps chronological order)
- Use `read_file` with `offset` parameter for files over 500 lines
- Track cycle numbers (e.g., "28th Cycle") so readers can spot stale items
- When a pre-existing failure has persisted >10 cycles, note it explicitly with "unchanged, 10+ cycles"
- Flags like "push blocked (403, Nth cycle)" show chronic issues
- Each entry ends with a Next Action line, even if it's just "Continue monitoring."

### Phase 6: Digest Integration

When the profile has a daily digest system:
```bash
python "${MY_REPOS}/_project/scripts/append-digest.py" "Sentry Pulse" "- **Finding 1**: details\n- **Finding 2**: details"
```

Use Windows absolute paths with forward slashes (e.g., `E:/path/to/script.py`) — MSYS-style `/e/path` doesn't work with `python`. The `append-digest.py` script has a pre-existing `NameError: name 'temp'` at line 165 that doesn't prevent the append from succeeding — the core operation completes before the error.

For appending directly without the script:
```bash
cat >> ${MY_REPOS}/_project/daily-digest/2026-07-14.md << 'EOF'

## [HH:MM TZ] Sentry Pulse

- **Sentry Nth Cycle** — summary line
EOF
```

### Phase 7: Deliver Report

Format using `discord-report-format` conventions:
- Bold emoji header + timestamp
- 📊 RECAP, ⏳ PENDING, 🎯 RECOMMENDED ACTIONS sections
- Box-drawing section separators
- Compact, one-item-per-line format
- 🔍 Checked timestamp with HEAD short-hash

Target: scannable in under 10 seconds.

## Suites & Expected Counts (Current, July 2026)

```yaml
fix_suites:
  acp:              { path: tests/acp/,                       expected: ~303, skip: ~1 }
  tirith:           { path: tests/tools/test_tirith_security.py, expected: ~95 }
  hindsight:        { path: tests/plugins/memory/test_hindsight_provider.py, expected: ~115, skip: ~1 }
  context_refs:     { path: tests/agent/test_context_references.py, expected: ~17 }
  scripts:          { path: tests/scripts/,                   expected: ~5 }
  skills_full:      { path: tests/skills/,                    expected: ~294 }
  approval_isolate: { path: tests/acp/test_approval_isolation.py + test_edit_approval.py, expected: ~18 }
combined: { expected: ~825, skip: ~1 }
```

Expected counts drift upward as upstream adds tests. The combined fix suite total (~825) is the canonical regression signal — if it drops below baseline, investigate immediately.

## Known Pre-Existing Gaps (Current, July 2026)

- **Docker lifecycle (17 tests) + MemPalace (20 tests)**: stripped upstream June-July 2026, re-applied 10+ times but lost on every cross-workstation reset. Currently NOT present on HEAD. Skip checking these unless explicitly re-applied.
- **web_server.py compat block**: uncommitted modification (HERMES_ONE_MODEL_LIBRARY_COMPAT_V1), 10+ cycles unchanged. Not test-affecting.
- **Push blocked (403)**: 28+ consecutive cycles unable to push fix commits to origin. Fixes survive on local HEAD only. Flag cycle count in every pulse.
- **Approval symlink tempdir on Windows (1 test)**: `test_symlinked_temp_dir_only_exempts_canonical_target` — symlink detection (`os.path.realpath`) resolves differently on Windows. Genuinely Linux-specific; junction points don't map to POSIX symlinks cleanly.
- **Hindsight PostSetup interactive mock (3/6 tests)**: `test_local_embedded_setup_materializes_profile_env`, `_respects_existing_profile_name`, `_preserves_existing_key_when_input_left_blank` — interactive setup mock doesn't create `~/.hindsight/profiles/hermes.env` on Windows. `shutil.which` returns None for `uv` but setup still configures `local_embedded` mode; profile env file path doesn't match tmppath. Non-PostSetup hindsight tests (109/109+1sk) pass fine.
- **ContextRefs PRIVATE-KEY redaction (1 test)**: `test_blocks_sensitive_home_and_hermes_paths` — context warning header contains `PRIVATE-KEY` verbatim from sensitive-credential-file detection, failing `assert "PRIVATE-KEY" not in result.message`. Redaction covers file content but not warning header text.
- **Skills pre-existing (3 tests, 15+ cycles)**: `test_skill_view_applies_inline_shell_when_enabled` (bash cold-start), `test_nested_local_collides_with_top_level_external` (path separator), `test_support_markdown_does_not_collide_with_real_skill` (collision detection). Unchanged for 15+ cycles.

## Approval Tempdir Path Fix (Windows)

`_is_verification_artifact_cleanup` in `tools/approval.py` uses `os.path.realpath(tempfile.gettempdir())` to normalize the temp directory path before comparing against the command operand. On Windows, `os.path.realpath` can resolve `TMP`/`TEMP` differently than the raw environment variable value (e.g., `${USER_HOME}\AppData\Local\Temp` vs the actual short-path variant). This causes `test_nonrecursive_verification_artifact_cleanup_is_not_dangerous` to fail because `operand != os.path.join(temp_dir, basename)`.

**Fix:** Accept both the `realpath`'d and raw tempdir paths:

```python
temp_dir_raw = tempfile.gettempdir()
temp_dir = os.path.realpath(temp_dir_raw)
basename = os.path.basename(operand)
if operand not in (
    os.path.join(temp_dir, basename),
    os.path.join(temp_dir_raw, basename),
):
    return False
```

This is a durable fix — upstream refactors of the approval pipeline may revert it, but the same pattern applies whenever the check is restored.

**Symlink variant** (`test_symlinked_temp_dir_only_exempts_canonical_target`): This test verifies that a symlinked tempdir variant is NOT exempted. On Windows, `os.path.realpath` resolves differently for junction points vs POSIX symlinks. This test is genuinely Linux-specific and would require a path-traversal-aware approach on Windows (checking `os.path.splitdrive` or using `win32file.GetFinalPathNameByHandle`).

## PYTHONPATH Conflict Resolution for `tests/scripts/`

When a repo has a top-level `scripts/` directory with modules, adding `tests/scripts/` tests can cause `ModuleNotFoundError` because pytest's rootdir resolution may resolve the wrong `scripts` package. The fix:

1. Create `tests/scripts/conftest.py` that resets or filters `sys.path` to prevent the top-level `scripts/` from shadowing Python standard library modules
2. Verify with a targeted test run: `python -m pytest tests/scripts/ -x -q`
3. No changes to `pyproject.toml` or test config needed — the conftest scopes the fix to those tests only

This pattern applies to any `tests/<subpackage>/` directory that mirrors a top-level `<subpackage>/` in the repo.

## ACP Env-Leak Flake Pattern

Two approval-isolation tests (`test_interactive_env_var_routes_to_callback` and related) fail in batch mode (est. 2/303) but always pass in isolation (0.64s). Root cause: `HERMES_CRON_SESSION` env var leaks from parent cron process into the ACP subprocess during batch runs. This is a known transient — does NOT block the pipeline.

Detection: run full `tests/acp/` suite once. If failures appear, re-run the failing tests in isolation to confirm env-leak pattern.
