# Diagnosing "Model Provider Failed After Retries" Errors

## Why This Error is Misleading

The agent reports "The model provider failed after retries" whenever the LLM API returns a non-retryable error after exhausting its 3 retry attempts. This is often **NOT** a provider outage — it can be a message formatting issue that the provider correctly rejects.

## Root Cause Analysis Workflow

When a user reports this error from a Discord/Spacebar agent:

### 1. Identify the failing session

Check the gateway log for the error message and extract the session ID:

```bash
grep "model provider failed\|provider failed after retries" ~/AppData/Local/hermes/logs/gateway.log
```

The agent log contains the detailed error with session ID:

```bash
grep "Non-retryable client error\|API call failed" ~/AppData/Local/hermes/logs/agent.log | tail -10
```

### 2. Determine the error type

From the agent log, look for the actual error message:

- **HTTP 400 "Invalid 'messages[N].tool_calls': empty array"** — DeepSeek-specific. The message history has an assistant message with `tool_calls: []`. See *Empty tool_calls: [] Fix* below.
- **HTTP 400 "An assistant message with tool_calls must be followed by tool messages"** — Role alternation violation. Consecutive assistant messages that should have been merged.
- **HTTP 401/403** — API key expired, revoked, or wrong provider. Check `.env`.
- **HTTP 429 / RateLimitError** — Rate limited. Check usage dashboard.
- **ConnectionError / Timeout** — Network issue or provider outage.

### 3. Trace to the profile and config

Which profile serves the Discord channel where the error occurred:

1. Check `config.yaml` → `discord.channel_prompts` for channel ID → persona mapping
2. Check profile configs (`profiles/<name>/config.yaml`) → `discord.allowed_channels` for channel ID membership
3. Check `profiles/<name>/channel_directory.json` for channel name → ID mapping
4. Verify the profile's `model.default` and `model.provider` values
5. Check the profile's `.env` for the API key (the global `.env` is at `~/AppData/Local/hermes/.env`)

### 4. Check the gateway

```bash
# Is the right gateway running?
cat ~/AppData/Local/hermes/profiles/<profile>/gateway_state.json

# Recent gateway log entries
tail -50 ~/AppData/Local/hermes/logs/gateway.log

# Errors log (detailed tool failures)
tail -50 ~/AppData/Local/hermes/logs/errors.log
```

### 5. Check the API key

```bash
grep -v "^#" ~/AppData/Local/hermes/.env | grep API_KEY
```

If the key is commented out or missing, the provider can't authenticate.

---

## DeepSeek Empty `tool_calls: []` Fix

### Symptom

```
HTTP 400: Invalid 'messages[18].tool_calls': empty array.
Expected an array with minimum length 1, but got an empty array instead.
```

### Cause

When an old session is **resumed** (loaded from the session DB), `repair_message_sequence` merges consecutive assistant messages. If one of them has `tool_calls: []` (empty array), the merged result can retain the empty array. DeepSeek's API validation rejects empty arrays — they want either a populated list or no `tool_calls` key at all.

Common trigger: The user sends a message in a thread where the bot's previous session expired. The session loads, the repair logic merges turns, and a `[]` survives into the API payload.

### Fix (code-level)

Two-layer fix applied in `run_agent.py` and `agent/conversation_loop.py`:

**Layer 1 (`_sanitize_tool_calls_for_strict_api`):** After stripping Codex-specific keys from `tool_calls`, check if the result is empty. If so, remove the `tool_calls` key entirely instead of setting it to `[]`.

```python
sanitized = [
    {k: v for k, v in tc.items() if k not in _STRIP_KEYS}
    if isinstance(tc, dict) else tc
    for tc in tool_calls
]
if not sanitized:
    api_msg.pop("tool_calls", None)
else:
    api_msg["tool_calls"] = sanitized
```

**Layer 2 (final safety net):** After all sanitization and JSON normalization, scan `api_messages` for any remaining assistant message with empty `tool_calls` and strip the key. This catches edge cases from session resume + `repair_message_sequence`.

```python
for am in api_messages:
    if (
        isinstance(am, dict)
        and am.get("role") == "assistant"
        and "tool_calls" in am
        and not (isinstance(am["tool_calls"], list) and am["tool_calls"])
    ):
        am.pop("tool_calls", None)
```

### Provider Documentation

This is an OpenAI Chat Completions schema validation. The spec says `tool_calls` must be an array with minimum length 1. An empty array `[]` is invalid. Other providers (OpenRouter, Anthropic) may silently tolerate it, but DeepSeek v4 strictly validates.

### Session Repair Note

If the corrupt session persists after the fix, instruct the user to use `/new` in the affected thread. The corrupt history is persisted in the session DB and the sanitizer only runs on the per-call API copy — a fresh session avoids the corrupted turns entirely.

---

## Common Provider Errors in Discord Agents

| User-Facing Error | Actual Error | Cause |
|---|---|---|
| "model provider failed" | HTTP 400 `tool_calls`: empty array | Session resume produces corrupt message |
| "model provider failed" | HTTP 400 consecutive assistant | Role alternation violation after merge |
| "model provider failed" | HTTP 429 rate limit | Quota exhausted, retry later |
| "model provider failed" | HTTP 401 unauthorized | API key missing or wrong |
| "gateway restarted" | Gateway process crashed | MCP server connection failures (STATUS_ACCESS_VIOLATION), config corruption, or stale state files |
| silent failure | Connection timeout to `gc.your-domain.example` | Spacebar server unreachable (DNS or network) |
