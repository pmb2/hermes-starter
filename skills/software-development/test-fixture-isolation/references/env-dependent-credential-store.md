# Worked Example — qwen-oauth Fallthrough Test (Hermes Agent, 2026-08-08)

Commit `a163743ad` — test-only hermeticity fix. This is the full diagnostic
for the "real credential store short-circuits the code path under test"
pattern (see SKILL.md → Ambient-State Variant).

## Symptom

- New-commit scope validation run (commit `3bc78f53d`, 206-test scope): 1 failure
  — `tests/hermes_cli/test_runtime_provider_resolution.py::test_qwen_oauth_auto_fallthrough_on_auth_failure`
- Fails deterministically in isolation.
- Assertion: `assert resolved["provider"] != "qwen-oauth"` — got exactly `"qwen-oauth"`.
- Test intent: with `requested="auto"` and Qwen OAuth creds raising
  `AuthError(code="qwen_auth_missing")`, `resolve_runtime_provider` should fall
  through to OpenRouter.

## The twist that exposed it

The test monkeypatches `resolve_provider` → `"qwen-oauth"` and
`resolve_qwen_runtime_credentials` → raise AuthError. A diagnostic run with a
print-instrumented mock showed the mock was **never called**, yet the function
returned `provider="qwen-oauth", source="qwen-cli"`.

## Root cause

`resolve_runtime_provider` (hermes_cli/runtime_provider.py) checks the
credential POOL before the OAuth fallthrough block:

1. `pool = load_pool(provider)` (~line 1852) — provider is `"qwen-oauth"`
2. `if pool and pool.has_credentials():` → **TRUE on this host** (real
   `hermes auth add` qwen-oauth entries exist, `source="qwen-cli"`)
3. Returns `_resolve_runtime_from_pool_entry(...)` with valid creds — BEFORE the
   `if provider == "qwen-oauth":` AuthError fallthrough block (~line 1981)
4. The pool-entry return uses `source = getattr(entry, "source", "pool")` — the
   entry's `source="qwen-cli"` was the distinctive value that identified the path.

The fallthrough logic itself is **correct**: with `load_pool` mocked to an empty
pool (`SimpleNamespace(has_credentials=lambda: False)`), the OAuth block ran,
the AuthError was caught, and resolution fell through to
`openrouter | env/config`.

## Not a regression

- Commit `3bc78f53d` only touched `model_switch.py`, `models.py`, and 2 new test
  files — not this path.
- `git diff HEAD origin/main -- hermes_cli/runtime_provider.py | grep qwen` → 0
  diffs; upstream has the identical unfixed test
  (`git show origin/main:tests/... | grep -c load_pool` = 23, same as local).
  The test is latent-broken on any host with real qwen-oauth pool creds; clean
  CI never trips it.

## Fix (commit a163743ad)

Make the test hermetic — an empty-pool mock forces the OAuth resolution path:

```python
monkeypatch.setattr(
    rp, "load_pool", lambda _provider: SimpleNamespace(has_credentials=lambda: False)
)
```

`SimpleNamespace` was already imported at the top of the test file. Result:
file 54/54 → 55/55; owning commit scope 206/206. Fix is to the TEST, not
production.

## Reusable diagnostics (condensed)

1. Isolation run → deterministic (not order-dependent).
2. Print-instrument the mock → never fires = a different code path returned.
3. Grep the returned dict's distinctive value (`source="qwen-cli"`) → locates
   the actual returning block.
4. Empty-store repro (mock `load_pool` empty) → proves the code under test is
   correct and isolates the failure to test-environment coupling.
5. `git show origin/main:<file>` comparison → rules out local regression.
