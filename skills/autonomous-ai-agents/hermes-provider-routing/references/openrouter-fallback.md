# OpenRouter Fallback Reference

**Base URL:** `https://openrouter.ai/api/v1`
**Auth:** `OPENROUTER_API_KEY`
**Docs:** https://openrouter.ai/docs

## Hermes Fallback Config

### Global Fallback

```bash
hermes config set fallback_providers '["openrouter"]'
hermes config set providers.openrouter.api_key_env OPENROUTER_API_KEY
hermes config set providers.openrouter.base_url https://openrouter.ai/api/v1
hermes config set fallback_model.provider openrouter
hermes config set fallback_model.model free
```

### Profile-Level Fallback

```yaml
fallback_model:
  provider: openrouter
  model: free
```

## How Fallback Routing Works

1. Primary provider (opencode-go) attempts request
2. If primary returns 4xx/5xx or connection failure, fallback activates
3. Fallback uses `fallback_model` config to pick provider + model
4. If `fallback_providers: ["openrouter"]` is set, the credential pool tries OpenRouter before failing

## "No models provided" Error

OpenRouter returns `{"error": {"message": "No models provided", "code": 400}}` when:
- The model name in the request doesn't match any model OpenRouter knows about
- The model name is empty or null
- Example of broken config: `model: deepseek/deepseek-chat` (this model no longer exists)

**Fix:** Switch to a valid model name or use OpenCode Go API as primary.

## Known Working Models (for fallback)

- `free` — auto-routes to cheapest available model
- `openrouter/free` — same as above, explicit namespace
- `meta-llama/llama-3.1-405b-instruct` — legacy large model
- `qwen/qwen-2.5-72b-instruct` — previously used for AI Scientist
