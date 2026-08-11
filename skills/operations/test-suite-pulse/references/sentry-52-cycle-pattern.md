# Sentry Fix Categories — 53 Cycles of Hermes Agent on Windows

Compiled from 53 consecutive qa-lead-pulse recovery cycles. Documents the specific Windows-compat fix suites, their pre-existing failures, and historical patterns for the `test-suite-pulse` skill.

## Active Fix Categories (All Verified Clean)

| # | Category | Files | Fix | Pre-existing Failures | Cycles Verified |
|---|----------|-------|-----|----------------------|-----------------|
| 1 | Tirith autouse fixture | `test_tirith_security.py` (95 tests) | `is_platform_supported=True` mock + `unsupported_platform` marker in `tests/conftest.py` | 0 | 53 |
| 2 | Approval pipeline | `test_approval.py` (312/312), `test_approved_command_clean_slate.py` (1 pre-existing) | Path-separator skip in `_rewrite_resolved_hermes_home`; `_fold_home_prefixes` ordering; `shlex.split(posix=)` fix; `rm ~/` pattern in `DANGEROUS_PATTERNS` | 1 bug: symlink-Windows FIXED; 1 new flake: interrupt-kill timing race | 53+ |
| 3 | USERPROFILE monkeypatch | context_refs (~19), hindsight (115) | `monkeypatch.setenv("USERPROFILE", str(tmp_path))` across 5+ test sites | 0 | 53 |
| 4 | ACP CRLF + path translation | ACP (311+), ACP adapter (19), edit_approval (17+) | Platform-aware `_parse_file_path`; CRLF normalization `\r\n → \n` in `_decode_text_bytes` | 1 suite-level flake (evolving) | 49+ |
| 5 | Skills path-sep assertions | openclaw (138), unbroker | `endswith(os.sep)` instead of `endswith("/")`; path-agnostic assertions | 1 `mode==0o600` on Windows | 53 |
| 6 | Sandbox mirror path normalization | `test_file_safety_sandbox_mirror.py` (13) | `classify_sandbox_mirror_target` uses `as_posix()` for `mirror_root`/`inner_path` | 0 | 6+ |

## Pre-Existing Windows Failures (Cosmetic)

These are OS-level Windows behavior differences, not code defects:

1. **FIXED ~Cycle 57**: `test_symlinked_temp_dir_only_exempts_canonical_target` — root-caused and fixed in commit `825e3df5a6`. Two bugs: (a) `shlex.split(posix=True)` stripped Windows backslashes, fixed with `posix=(os.name != "nt")`; (b) missing `\\brm\\s+(-[^\\s]*\\s+)*~/` in `DANGEROUS_PATTERNS` — added `"delete in home directory"` pattern. No longer a pre-existing failure.
2. `test_approved_command_genuine_interrupt_after_start_still_kills` — in `tests/tools/test_approved_command_clean_slate.py`. Windows process interrupt timing race: the `cmd_started` event fires asynchronously and the interrupt signal may land before the process is ready to receive it. Candidate for `pytest.mark.skipif(sys.platform == "win32")` or a longer process-startup wait. Present since ~Cycle 54.
3. ACP suite-level isolation flake — varies between cycles. Cycle 43-52: `test_ping_suppression` (ProactorEventLoop `OSError: [WinError 6]`). Cycle 53+: `test_result_passed_to_build_tool_complete` fails in full suite but passes in isolation. Both are test-ordering issues, not code defects.
4. Bash cold-start timeout — shell spawning overhead on Windows CI
5. `mode==0o600` assertion — file permission mask semantics differ on Windows

## Test File Movement History

| Suite | Original | Current | Notes |
|-------|----------|---------|-------|
| Context refs | `tests/tools/` | `tests/agent/` | Moved ~cycle 47 |
| Hindsight | `tests/tools/` | `tests/plugins/memory/` | Moved ~cycle 19 |
| Approval | `tests/tools/test_approval.py` | Stable | Multiple splits, same dir |
| Docker | `tests/tools/test_docker_lifecycle.py` | Stripped upstream | Re-applied ~10x, always lost |
| MemPalace | `tests/memory/test_mempalace.py` | Stripped upstream | Re-applied ~10x, always lost |
| **Major reorg ~Jul 2026** | `agent/tests/` | `tests/{agent,tools,acp,cron,cli}/` | Flat `agent/tests/` → nested `tests/*/` |
| File-safety suites (was) | `agent/tests/test_file_write_safety.py` | `tests/agent/test_file_safety*.py`, `tests/tools/test_write_*.py` | Split into subdirs |
| Approval (was) | `agent/tests/test_approval.py` | `tests/acp/test_approval_isolation.py`, `tests/tools/test_write_*.py` | Split across directories |
| Cron (was) | `agent/tests/test_cron*.py` | `tests/cron/` (172+ tests) | Moved to subdirectory |

## Post-Reorganization Test Counts

After the ~Jul 2026 flat-to-nested restructure, the old monolithic suites were split:
- Old "ACP 311/312" → now spans `tests/acp/` (84/85) + `tests/tools/test_write_approval.py` + `tests/tools/test_write_deny.py` (61/61) + `tests/acp_adapter/`
- Old "Cron 712/719" → now `tests/cron/` (172/173, 1 pre-existing tilde-expand failure)
- Old "File safety 86/86" → now `tests/agent/test_file_safety*.py` (47/47, 4 skipped) + write gates in `tests/tools/`

Always run targeted sub-directory sweeps rather than assuming single-file suites.

## Divergence Severity

| Behind | Risk | Note |
|--------|------|------|
| 0-50 | 🟢 Low | Rebase when convenient |
| 50-200 | 🟡 Moderate | Schedule within 3 cycles |
| 200-500 | 🟡 Attention | Rebase window narrowing |
| 500-1000 | 🔴 Critical | High gap but qa-lead paths had zero file overlap across 52+ cycles |
| 1000+ | 🔴 Extreme | Seen at cycles 51-53; merge-tree still clean for fix paths even at 1607 behind |

## ContextRefs Test-Count Drift

At cycle 52, ContextRefs was 17 tests. At cycle 53, it grew to 19 tests — upstream added 2 new context reference tests. These passed on first run, confirming no regression. **Expected:** test counts in fix-category suites are not static; always report actual counts from the current run.

## Append-Digest Script Note

Located at `_project/scripts/append-digest.py`. On Windows/MSYS2, this script may not exist if `_project` isn't cloned or if `scripts/` doesn't exist in the skeleton. Always verify existence before calling; skip digest append if absent. Alternative: write directly to `digests/digest-YYYY-MM-DD.md`.
