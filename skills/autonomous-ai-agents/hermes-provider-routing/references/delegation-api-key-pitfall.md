# Delegation API Key Pitfall: Empty String vs Env Var Reference

## The Bug

`delegation.api_key: ''` (empty string) in `config.yaml` causes **silent sub-agent model fallback**. All `delegate_task` calls fall through to the free fallback model regardless of what `delegation.model` says.

## Root Cause

The delegation config has its own `api_key` field. When set to `''` (empty string), the auth system interprets this as "use this empty string as the key" — NOT "look up the key from env vars". Authentication fails, and the API call falls through to `fallback_model` → `fallback_providers`, which typically routes to a free OpenRouter model.

## Symptoms

- Sub-agent result summaries show `Model: qwen/qwen3-coder:free` (or whatever free model is configured) even though `delegation.model` is set to `deepseek-v4-flash`
- Sub-agent API calls succeed but use the wrong model — outputs are lower quality
- `delegation.provider: opencode-go` is correctly set but ignored because auth fails first
- `grep -A5 "delegation:" ~/AppData/Local/hermes/config.yaml` shows `api_key: ''`

## Fix

```bash
hermes config set delegation.api_key '${OPENCODE_GO_API_KEY}'
```

The `${...}` syntax tells the config system to resolve from the environment variable at runtime. DO NOT pass an empty string — `hermes config set delegation.api_key ''` explicitly writes `api_key: ''` into the YAML, which is worse than having no api_key line at all.

## Verification

```bash
grep -A8 "delegation:" ~/AppData/Local/hermes/config.yaml
# Expected output:
# delegation:
#   model: deepseek-v4-flash
#   provider: opencode-go
#   base_url: https://opencode.ai/zen/go/v1
#   api_key: ${OPENCODE_GO_API_KEY}    <-- must have ${...} not ''
```

After fixing, dispatch a test subagent and check the result header for the correct model name.

## How It Happens

The `hermes config set` command places values literally into config.yaml. Running:
```
hermes config set delegation.api_key ''
```
Writes `api_key: ''` — two single quotes around nothing. The YAML parser reads this as an empty string, NOT as "unset". Unlike `model.default: ''` which gracefully falls back to a hardcoded default, `delegation.api_key: ''` causes active failure because the auth system tries to use the empty string as a credential.

To safely clear a config key, use `hermes config set delegation.api_key '${REFERENCE}'` with a valid env var reference.
