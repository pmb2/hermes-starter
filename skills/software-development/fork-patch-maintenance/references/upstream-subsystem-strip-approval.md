# Case Study: Upstream Subsystem Stripping — approval.py

> Hermes Agent fork, Jul 29 2026. Upstream commit `eff3b11eb2` by teknium1
> stripped multiple subsystems from `tools/approval.py` while our 3 local
> patches sat in different functions. A pure "file rearranged but intent
> preserved" situation — one of the cleanest subsystem strip examples.

## What Upstream Did

Upstream's `eff3b11eb2` ("complete approval mode/timeout resolution migration
to tools/approval.py core (TUI + codex surfaces)") made these changes to
`approval.py`:

**Removed (all deletion-only, no replacement):**
- Entire consecutive-denial circuit breaker (~80 lines):
  - `_denial_tally` dict with its 256-session LRU eviction
  - `_get_denial_breaker_threshold()` config reader
  - `_record_denial(session_key)` incrementer
  - `_reset_denials(session_key)` clearer
  - `_denial_breaker_addendum(session_key)` hard-stop text builder
- `_get_smart_policy()` function and its operator-policy injection into
  `_smart_approve()`'s system prompt (~30 lines)
- `allow_session` key from all `approval_data` payloads (3 call sites)
- `has_permanent_capable` logic replaced with simpler `not has_tirith` check
- Docker/podman patterns simplified (from 9 complex regexes to 2 simple ones)
- Flags-after-operands `rm` pattern removed (6-line regex comment block)
- All `_reset_denials()` and `_record_denial()` call sites removed (~12 sites)

**Changed:**
- Default timeout: 300s → 60s in `_get_approval_timeout()`
- Module-bottom: `load_permanent_allowlist()` → lazy-init guard comment
- `sleep` interval in `_await_gateway_decision` comment updated

**Our unchanged code affected by the rearrangement:**
- `_is_verification_artifact_cleanup()` — the Windows path normalization and
  `shlex.split(posix=...)` fix. Function body unchanged but surrounding
  functions were removed, shifting it ~80 lines up in the file.
- `check_all_command_guards()` — the entry point for all gate checks. Upstream
  removed `_reset_denials()`, `_denial_breaker_addendum`, and `allow_session`
  from the approval_data dict inside this function, but the `approve`/`deny`
  logic flow is preserved.
- `load_permanent_allowlist()` — our lazy-init guard was structurally
  upstream-compatible (same flag, same guard pattern) but the upstream version
  has subtle differences in function signature.

## Detection Commands

```bash
# 1. Net-negative check — approval.py is a deletion-heavy file
git diff origin/main -- tools/approval.py --stat
# → shows -100+ lines net (upstream removed 250+ lines of denial breaker + policy)

# 2. Upstream commit intro
git log --oneline origin/main -- tools/approval.py | head -5
git show eff3b11eb2 -- tools/approval.py --stat

# 3. Our patch zone check — do our changes touch the stripped subsystem?
git diff origin/main..HEAD -- tools/approval.py | grep -i "denial\|breaker\|_tally\|reset_denial\|smart_policy"
# → Empty! Our 3 patches never touched the stripped code.

# 4. Function position before/after (key functions shifted up by ~80 lines)
grep -n "^def _is_verification" tools/approval.py      # Our hack — check line number
grep -n "^def check_all_command" tools/approval.py     # Entry point
git show origin/main:tools/approval.py | grep -n "^def _is_verification"   # Same func, different position
git show origin/main:tools/approval.py | grep -n "^def check_all_command"
```

## Rebase Strategy Applied

1. **Accept upstream deletions** — the denial breaker and smart policy are gone
   upstream and should not be restored. Our fork never used them (the OmniRoute
   lock in `model_switch.py` is a different mechanism entirely).

2. **Re-apply our patches at shifted positions** — `_is_verification_artifact_cleanup`
   and `check_all_command_guards` still exist upstream with the same signatures,
   but the functions around them are gone. Our patches (`shlex.split`,
   path normalization, `rm ~/` pattern) apply cleanly at the upstream function
   positions.

3. **Remove stale references** — our approval tests don't test denial tally or
   smart policy, so no test changes needed. The `allow_session` removal means
   approval_data payloads from our branch will need the `allow_session` key
   dropped on rebase.

4. **Evaluate behavioral change** — the 300s→60s timeout default. Our fork
   didn't override this, so we should verify 60s is sufficient for our gateway
   approval flow (Telegram push notifications may take 10-20s, 60s was
   historically too tight based on upstream's own commit message).

## Key Takeaways

- **Stripped subsystems are stealth conflicts** — they show as net-negative
  diffs (-300/+50), which look *lower* risk than balanced refactors, but they
  shift every remaining function's line position
- **Check `git diff origin/main..HEAD | grep -i "stripped_name"`** — if empty,
  your patches are safe in intent but need positional re-application
- **Do NOT restore stripped subsystems** — trying to keep them on rebase
  introduces an unnecessary diff against upstream and future maintainability
- **Check dependent UI/data contracts** — `allow_session` removal collapsed
  a 2-tier permission model to 1 tier in the gateway adapter; any fork code
  that built on the 2-tier model needs updating
- **Test assertion drift** — changed defaults (300s→60s timeout) silently
  break tests that hardcode the old value. Use `git diff origin/main -- <file>
  | grep -E "default=|timeout=\d+"` to find these before rebase
