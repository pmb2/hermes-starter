# Provider-Specific Quirks

## DeepSeek API

### Auth Header Required on ALL Endpoints
Unlike OpenCode Go which exposed a public `/models` endpoint, DeepSeek requires
`Authorization: Bearer <key>` on every endpoint. Health checks that omit auth
will get HTTP 401.

**Always include auth, even on /models:**
```python
req = urllib.request.Request(
    f"{base_url}/models",
    headers={
        "User-Agent": "curl/7.68.0",
        "Authorization": f"Bearer {api_key}",
    },
)
```

### Available Models
- `deepseek-chat` — General chat, visible content. Use for health checks.
- `deepseek-reasoner` — Reasoning tasks. May return empty `content` with only `reasoning_content`.
- `deepseek-v4-flash` — Fast inference. Current default for the operator.

### Rate Limits
Returns HTTP 429 with `GoUsageLimitError` when limits hit. Weekly tier limits exist.

### Env Var
`DEEPSEEK_API_KEY` in `~/AppData/Local/hermes/.env`

---

## OpenCode Go API (deprecated)

### Key File
`~/.local/share/opencode/auth.json`:
```json
{
  "opencode-go": { "type": "api", "key": "sk-..." }
}
```

### Public /models Endpoint
Was public (no auth). Health checks that skipped auth on Tier-1 succeeded here
but fail on DeepSeek.

### User-Agent Required
Python's default urllib user-agent gets 403 error 1010. Always set:
```python
headers = {"User-Agent": "curl/7.68.0"}
```

### Reasoning Model Quirk
`deepseek-v4-flash` via OpenCode Go returned empty `content` with `reasoning_content`
when token budget was tight. Use `kimi-k2.5` or `kimi-k2.7-code` for health checks
that need visible output.
