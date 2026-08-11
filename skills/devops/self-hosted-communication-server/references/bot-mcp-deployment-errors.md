# Bot MCP Deployment — Error Reference

Captures the specific errors and fixes discovered during Team 7 Hermes Dev bot setup.

## 1. mempalace MCP: Wrong command name

**Error:** `Failed to connect to MCP server 'mempalace' (command=mempalace): Connection closed`
also: `Invalid JSON: expected value at line 1 column 3`

**Root cause:** `mempalace mcp` (with args `["mcp"]`) prints setup instructions to stdout instead of starting an MCP server:

```
MemPalace MCP quick setup:
  claude mcp add mempalace -- mempalace-mcp
  
Run the server directly:
  mempalace-mcp
```

**Fix:** Use `mempalace-mcp` as the command (no args needed):
```yaml
mempalace:
  command: mempalace-mcp
  timeout: 120
```

## 2. gbrain MCP: CancelledError blocks gateway startup

**Error:**
```
MCP server 'gbrain' initial connection failed (attempt 1/3), retrying in 1s: unhandled errors in a TaskGroup (1 sub-exception)
Failed to connect to MCP server 'gbrain' (command=gbrain): CancelledError
```

**Root cause:** `CancelledError` during MCP stdio handshake. gbrain's `serve` command starts a long-running server process but the MCP client's initial handshake (expecting JSON-RPC `initialize` response) gets cancelled, likely because gbrain's startup is slightly slower than the MCP client expects, or there's a race condition in the asyncio TaskGroup.

**Why it matters for gateways:** Each retry attempt has backoff (1s → 2s → 4s). 3 attempts = ~7+ seconds of blocking during gateway boot. While this retry loop runs, the Discord WebSocket connection attempt (which runs concurrently) gets starved and hits the 30s `_PLATFORM_CONNECT_TIMEOUT_SECS_DEFAULT`:

```
ERROR gateway.run: ✗ discord error: discord connect timed out after 30s
WARNING gateway.run: Gateway started with no connected platforms
```

**Fix:** Remove gbrain from bot profile MCP configs entirely. gbrain is useful in the main interactive Hermes session but should NOT be configured in bot gateway profiles.

## 3. Discord connection timeout with MCP servers

**Error:** `discord connect timed out after 30s`

**Root cause:** Gateway initializes MCP servers and connects to Discord concurrently. MCP server init (especially with retries) eats into the 30s default platform connect timeout.

**Fix:** Increase the timeout via env var in the profile's `.env`:
```
HERMES_GATEWAY_PLATFORM_CONNECT_TIMEOUT=90
```

This env var controls `_platform_connect_timeout_secs()` in `gateway/run.py`. Default is 30.0.

## 4. Fleet manager 429 rate-limit handling

**Error:** `Health check failed: HTTP Error 429: Too Many Requests` followed by `Health check FAILED — restarting`

**Root cause:** The fleet manager's `health_check()` method catches all exceptions with `except Exception` — including `urllib.error.HTTPError` for 429 rate limits. Since 429 is treated as a failure, the gateway gets restarted unnecessarily.

**Fix:** Add a specific `except HTTPError` handler before the generic handler that treats 429 as "healthy, skip restart":
```python
from urllib.error import HTTPError

except HTTPError as e:
    if e.code == 429:
        self.last_health_ok = time.time()
        log.info("[%s] Health check rate-limited (429) — bot healthy, skipping restart", self.name)
        return True
```

## 5. Fleet manager health check read timeout

**Error:** `Health check failed: The read operation timed out` → `Health check FAILED — restarting`

**Root cause:** Spacebar's `/users/@me` endpoint takes longer than the 10s timeout in `urllib.request.urlopen(req, timeout=10)`. With 39+ bots all polling this endpoint, the server gets overwhelmed.

**Fix options (in order of preference):**
1. Trim the `BOTS` list to only essential bots (reducing load on Spacebar)
2. Increase the health check timeout from 10s to 15-20s
3. Check for zombie fleet manager processes with `wmic` or `tasklist`

## 6. Profile config.yaml doesn't inherit MCP servers

**Important design constraint:** When a Hermes gateway runs under a profile (via `HERMES_HOME = ~/.hermes/profiles/<name>/`), `load_config()` reads the profile's own `config.yaml`. MCP servers defined in the main `~/.hermes/config.yaml` are NOT inherited. Each profile must have its own `mcp_servers` section.

This is different from most other config sections (model, agent, tools) which inherit defaults from the built-in `DEFAULT_CONFIG` and merge with profile overrides. The `mcp_servers` key doesn't exist in `DEFAULT_CONFIG`, so profiles without it get empty MCP server lists.

## 7. Path-dependent MCP server commands

Some MCP server commands need explicit PATH overrides because they're installed in non-standard locations:

| Server | Binary Location | PATH Fix |
|--------|----------------|----------|
| `gbrain` | `~/.bun/bin/gbrain.exe` | `PATH: ${USER_HOME}/.bun/bin;...;${PATH}` |
| `mempalace-mcp` | System Python Scripts | On PATH by default in Hermes venv |

The `${PATH}` in the env override is expanded at config load time via `_expand_env_vars()`, which reads `os.environ["PATH"]`, prepends the custom path, and passes the result as the subprocess environment variable.
