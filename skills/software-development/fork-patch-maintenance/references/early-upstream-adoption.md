# Early Upstream Adoption — worked example (Aug 7 2026)

Adopting upstream commit `fb435aae9` (`perf(model): disk-cache custom-provider /v1/models probes`) onto a fork 448 commits behind, then routing a local-only probe through the new upstream API. Result: the `model_switch.py` cache zone became byte-identical to `origin/main`, the flagged rebase conflict collapsed to context-shift grade, and a per-`/model` 5s HTTP probe was eliminated.

## Context

- Fork: Hermes Agent, 448 behind / 13 ahead at start.
- Upstream commit `fb435aae9` added `cached_fetch_api_models()` to `hermes_cli/models.py` (+95 lines: TTL disk cache keyed `custom:<base_url>`, fingerprinted on api_key/api_mode/headers, stale-beats-nothing fallback) and swapped 3 call sites in `model_switch.py` from raw `fetch_api_models()` to the cached wrapper.
- Our local OmniRoute lock patch (restored earlier as `3d7da42b2`) contained a 4th probe — the picker row raw `urllib.request` call (5s timeout on every `/model` open), the LAST uncached custom-endpoint probe in the file.
- Previous pulse had flagged: "rebase-time adaptation: swap the urllib block for `cached_fetch_api_models()`". This session executed it NOW instead of at rebase.

## Steps that worked

### 1. Dependency check before applying

The new function relies on `_load_provider_models_cache` / `_save_provider_models_cache` / `_PROVIDER_MODELS_CACHE_TTL` (already in our tree, used by `cached_provider_model_ids`). Verified with:

```bash
grep -n "_PROVIDER_MODELS_CACHE_TTL\|def _load_provider_models_cache\|def _save_provider_models_cache" hermes_cli/models.py
```

All present → the upstream models.py hunk would apply standalone (no hidden dependency chain).

### 2. 3-way apply of the upstream diff

```bash
git show fb435aae9 -- hermes_cli/models.py | git apply --3way      # clean
git show fb435aae9 -- hermes_cli/model_switch.py | git apply --3way # clean
```

Both applied cleanly despite 448-commit divergence — `--3way` merges against the working tree using the blob IDs in the diff index lines. (Plain `git apply` would have failed on context mismatch; `git cherry-pick` would have been wrong because we wanted the file change, not the commit.)

### 3. Test files extracted from the object DB

```bash
git show fb435aae9:tests/hermes_cli/test_cached_fetch_api_models.py > tests/hermes_cli/test_cached_fetch_api_models.py
git show fb435aae9 -- tests/hermes_cli/test_picker_prewarm.py | git apply --3way
```

(207-line cache-contract test file + 2 new prewarm e2e tests.)

### 4. Local path adaptation — the wire-shape matching decision

The OmniRoute picker row (local-only, `localhost:20128`) replaced raw urllib with:

```python
_live_models = cached_fetch_api_models(
    "",
    _omniroute_base,
    timeout=1.5 if for_picker else 5.0,  # picker: fail fast on a slow router endpoint
)
```

Two deliberate choices:
- **No `headers` arg** — the upstream prewarm call site (`probe_current_custom_provider` block) also passes none. Headers are part of the cache fingerprint (`_custom_endpoint_fingerprint` hashes `headers or {}`); passing `{"Accept": "application/json"}` (what the old urllib code sent) would produce a DIFFERENT fingerprint than the prewarm entry → cache miss → the whole perf fix silently no-ops for the picker. The old urllib code's headers existed only because raw urllib needed them; `probe_api_models` (behind `fetch_api_models`) adds its own wire headers.
- **`timeout=1.5 if for_picker else 5.0`** — mirrors the upstream fail-fast convention (the other call sites use it), better than the old hardcoded 5s for picker opens.

### 5. Verification

```bash
# New + surrounding suites
py -3.11 -m pytest tests/hermes_cli/test_cached_fetch_api_models.py tests/hermes_cli/test_picker_prewarm.py -q   # 15 passed
py -3.11 -m pytest tests/hermes_cli/test_model_switch_custom_providers.py tests/hermes_cli/test_list_picker_providers.py \
  tests/hermes_cli/test_model_picker_excluded_providers.py tests/hermes_cli/test_model_switch_configured_provider_routing.py \
  tests/hermes_cli/test_custom_provider_model_switch.py tests/gateway/test_model_command_custom_providers.py -q   # 55 passed
py -3.11 -m pytest tests/hermes_cli/test_inventory.py tests/hermes_cli/test_aux_picker_inventory.py tests/hermes_cli/test_model_switch_persist_default.py -q   # 21 passed
```

Functional monkeypatch check proving the picker row routes through the cache with the expected kwargs:

```python
from unittest.mock import patch
import hermes_cli.models as M
import hermes_cli.model_switch as MS
calls = []
def fake_cached(api_key, base_url, **kw):
    calls.append((api_key, base_url, kw))
    return ['m-route-1', 'm-route-2']
with patch.object(M, 'cached_fetch_api_models', fake_cached):
    res = MS.list_authenticated_providers(
        current_provider='omniroute', current_base_url='http://localhost:20128/v1',
        current_model='gpt-x', probe_current_custom_provider=True, for_picker=True)
# assert: exactly 1 omniroute row, source=='router', models[0]=='gpt-x',
#         len(calls)==1, api_key=='', base_url=='http://localhost:20128/v1',
#         kw['timeout']==1.5, kw.get('headers') is None
```

Note: the function-local `from hermes_cli.models import cached_fetch_api_models` resolves at call time, so `patch.object(M, ...)` intercepts it.

### 6. Commit

```bash
git commit -m 'perf(model): adopt upstream cached_fetch_api_models (fb435aae9) + route OmniRoute picker row through it
...'
```

Commit message recorded the upstream SHA and the adaptation rationale. Landed as `3bc78f53d` (#26, 4 files, +411/-27).

## Why this beats waiting for the rebase

- **Conflict-surface reduction**: the adopted regions (models.py function + 3 call sites) are now byte-identical to `origin/main`; `git diff origin/main -- <file>` is empty there. The pending rebase only re-introduces genuinely-local rows (OmniRoute lock + picker row), which are context-shift grade.
- **Perf win now**: every `/model` open previously live-probed the router's `/v1/models` with a 5s timeout; now it reads the TTL disk cache that boot prewarm populates.
- **Risk contained**: upstream's own tests (extracted from the commit) run on OUR tree, so behavioral incompatibility with local patches surfaces immediately.

## Environment gotchas hit this session

1. **MSYS path vs Windows-native Python**: `py -3.11 ${MY_REPOS}/.../append-digest.py` fails (`can't open file 'C:\e\yourdata\...'`). Windows-native interpreters need `${MY_REPOS}/...`.
2. **Nested command substitution blocked**: `sed -n "$(grep -n 'def x' f | head -1 | cut -d: -f1),+12p" f` was rejected by the terminal hardline blocklist. Use `search_files`/`read_file` instead of subshell one-liners.
3. **Repo-local venv lacks pytest** — `venv/Scripts/python.exe -m pytest` → "No module named pytest". Use the system interpreter that has it (`py -3.11 -m pytest`). (Environment-specific — re-check per machine.)
