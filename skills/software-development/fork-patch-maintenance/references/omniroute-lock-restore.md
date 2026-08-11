# OmniRoute Lock Restore — Stale-Heuristic Collision (Aug 7 2026)

Worked example for section 4i (Object-DB Patch Restoration): re-applying the
last lost Aug-4-reset patch — the OmniRoute router lock (`72c19a87de`,
originally authored Jul 28 by Sentry) — onto a `model_switch.py` /
`slash_commands.py` that upstream had rewritten in the intervening 346 commits.

## The Patch (3 layers)

1. `switch_model()` — when current provider is omniroute (or a custom endpoint
   whose base_url matches), block `--provider` changes and short-circuit the
   switch to stay on the router.
2. `list_authenticated_providers()` — when omniroute is active, skip ALL
   built-in provider scanning, probe the router's `/v1/models` endpoint, and
   return only the OmniRoute Router row (prevents the /model picker showing
   20+ direct providers).
3. `_handle_model_command()` (gateway) — reject `--provider` at the Discord
   level with a clear error before it reaches `switch_model()`.

## Conflict-Review Sequence (what worked)

Before touching the tree, verify every anchor the old diff expects actually
exists in the rewritten file:

- `grep -n "def switch_model"` → present at :1207 with an IDENTICAL signature
  (`current_provider`, `current_base_url`, `current_api_key`, `is_global`,
  `explicit_provider`, ...) — the old hunk context (`target_provider =
  current_provider` / `resolved_moa_preset = False`) matched exactly.
- `grep -n "class ModelSwitchResult"` → field contract (`success`,
  `new_model`, `target_provider`, `provider_label`, `api_key`, `base_url`,
  `api_mode`, `is_global`, `resolved_via_alias`) still matches the guard's
  early-return construction — no missing-field crash.
- `list_authenticated_providers` at :1919 still computes
  `_current_provider_norm` / `_current_base_url_norm` locals the guard reads.
- Gateway: `t` imported (`from agent.i18n import t`), `explicit_provider` /
  `current_provider` in scope at the insertion point, `gateway.model.error_prefix`
  key already used elsewhere in the file.

Result: manual `patch` application hunk-by-hunk, one `patch` call per hunk,
lint OK after each — no cherry-pick (it would have conflicted on the rewritten
file).

## The Collision

The first test run of `tests/hermes_cli/test_model_switch_custom_providers.py`
failed:

```
test_list_authenticated_providers_bare_custom_slug_recovers
assert group["slug"] == "custom:ollama"  # got 'omniroute'
```

Root cause: the old guard's `_is_omniroute_router` check included
`or "localhost" in _current_base_url_norm`. When the patch was written
(Jul 28), a localhost custom endpoint meant OmniRoute. Since then upstream
added local Ollama support (`http://localhost:11434/v1`), and the test
exercises exactly that: `current_provider="custom"`,
`current_base_url="http://localhost:11434/v1"`. The bare-hostname heuristic
classified Ollama as the OmniRoute router — the picker would show only the
router row and block `--provider` for every local Ollama user.

## The Fix

Port-scoped detection at BOTH guard sites (switch_model + picker):

```python
"omniroute" in _current_base_url_norm
or "localhost:20128" in _current_base_url_norm   # was: "localhost" in ...
```

`:20128` is the router's canonical port (also the guard's own default fallback
`http://localhost:20128/v1`). General rule: scope detection heuristics to the
narrowest stable discriminator — port, exact host, or a feature-only string —
never a bare common hostname.

## Verification (the full matrix)

53 tests across 4 files passed:
`test_model_switch_custom_providers.py`,
`test_model_switch_configured_provider_routing.py`,
`test_model_switch_persistence.py`,
`test_model_command_custom_providers.py`.

Plus a 5-case functional smoke check (direct `switch_model` /
`list_authenticated_providers` calls, no pytest needed):

1. omniroute + `--provider openai` → blocked with the lock error ✅
2. omniroute, no explicit provider → passthrough, `target_provider="omniroute"` ✅
3. `custom` + `localhost:20128` + `--provider openai` → blocked ✅
4. `custom` + `localhost:11434` (Ollama) → NOT locked, normal switch ✅
5. picker with omniroute active → exactly one row (`['omniroute']`) ✅

## Commit

`3d7da42b2` — `fix(dev-lead): restore OmniRoute router lock (72c19a87de, lost in
Aug 4 reset)`. Commit message records: the 3-layer restore, the heuristic
tightening + why (`localhost:20128`, Ollama collision), the 53-test pass, and
the 5 functional checks. Stack: 13 ahead / 346 behind, push still 403-blocked.

## Takeaways

- Old patch heuristics are snapshots of the upstream of their era — re-validate
  them against the CURRENT upstream surface, not just the patch's own tests.
- The upstream test suite is the best detector: run every test file that
  imports the touched functions, not only the tests the original commit named.
- Functional smoke checks (both the lock path AND the no-lock path) catch
  what unit tests with mocked env miss.
- A deferred "conflict-heavy restore" (per Restore ordering in section 4i) is
  the right call — when executed later with the full conflict review, it landed
  cleanly with only the one heuristic adaptation.
