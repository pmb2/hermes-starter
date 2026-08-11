# Discovering MCP Servers from Other Tools

When a user has MCP servers configured in another tool (OpenCode, Claude
Desktop, Cursor, VS Code, etc.) and wants to use them in Hermes, use this
discovery and porting process.

## Discovery Sources

### OpenCode (`~/.config/opencode/opencode.json`)

OpenCode config key is `mcp`. Each entry has:

```json
"GIT-STARS": {
  "type": "local",
  "command": ["python", "-m", "app.main"],
  "enabled": true,
  "cwd": "E:/.../project",
  "environment": {
    "GITHUB_TOKEN": "${GITHUB_TOKEN}",
    "DATABASE_URL": "sqlite+aiosqlite:///./gitmcp.db"
  }
}
```

Map to Hermes format:

| OpenCode field | Hermes mapping |
|---|---|
| `command[0]` | `command` |
| `command[1:]` | `args` |
| `environment` | `env` (keep `${VAR}` patterns) |
| `cwd` | `workdir` (Hermes-specific) |
| `type: "local"` | stdio transport (implicit) |

**Always wrap secrets as `${ENV_VAR}` references** to keep them out of
`config.yaml`:
```yaml
# ✅ CORRECT:
env:
  GITHUB_TOKEN: ${GITHUB_TOKEN}

# ❌ WRONG — secrets in plain text:
env:
  GITHUB_TOKEN: ghp_actual_token_here
```

### Claude Desktop (`~/.config/Claude/claude_desktop_config.json`)

Claude Desktop config key is `mcpServers` (note capital S). Each entry:

```json
"filesystem": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
}
```

Nearly identical to Hermes format — drop straight in. Claude Desktop does
NOT support `workdir`; the server inherits Claude's cwd.

### Cursor (`~/.cursor/mcp.json`)

Same format as Claude Desktop (`mcpServers` key). Drops in identically.

## Porting Checklist

For each discovered MCP server:

1. **Check if it's already in Hermes** — avoid duplicates
2. **Verify the project exists** at the `workdir` / `cwd` path
3. **Check for env var dependencies** — the server may need API keys, DB URLs, etc.
4. **Add to Hermes `mcp_servers`** in `config.yaml`
5. **Test in isolation** before restarting

## How to Test an MCP Server Before Wiring

Use the `mcp` Python SDK to test a server standalone (avoids the Hermes
restart cycle during development):

```python
import asyncio
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import ClientSession

async def test_server():
    params = StdioServerParameters(
        command="python",
        args=["-m", "app.main"],
        env={"OPENAI_API_KEY": "..."},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            result = await session.list_tools()
            print(f"Tools ({len(result.tools)}):")
            for t in result.tools:
                print(f"  {t.name}: {t.description[:80]}")

            # Call one tool
            health = await session.call_tool("health_check", {})
            print("Result:", health.content)

asyncio.run(test_server())
```

Key success signals:
- `list_tools()` returns tools without error
- `call_tool()` succeeds with expected data
- Process exits cleanly after the `async with` block closes

## Config Format Quick Reference

```yaml
mcp_servers:
  server_name:                    # snake_case, no spaces
    command: "python"             # executable
    args: ["-m", "app.main"]      # arguments (list)
    env:                          # env vars (uses Hermes's filtered env)
      SECRET_KEY: ${SECRET_KEY}   #   → use ${ENV_VAR} for secrets
      DB_URL: sqlite:///./db.db   #   → plain values are fine for config
    workdir: E:\path\to\project   # optional: working directory
    timeout: 120                  # optional: per-tool-call timeout (default: 120)
```

## Common Pitfalls

1. **`${VAR}` not expanded** — Hermes replaces `${VAR}` with the corresponding
   env var from the Hermes process's environment (read from `.env` and system).
   If the var isn't set, it passes literally as `${VAR}`. Don't use shell-style
   `${VAR:-default}` — Hermes doesn't support default values.

2. **Case sensitivity** — `${OPENROUTER_API_KEY}` and `${openrouter_api_key}`
   are different in the Hermes env reader. Match the exact case from `.env`.

3. **Filtered environment** — stdio MCP servers inherit a FILTERED env (only
   PATH, HOME, USER, LANG, LC_ALL, TERM, SHELL, TMPDIR + XDG_*). Any var your
   server needs MUST be listed explicitly in the `env:` block, even if it's
   already set in the Hermes process environment.

4. **Server startup order** — Hermes connects to all MCP servers at startup.
   If a server depends on a database that starts slower, it may fail the first
   connection attempt. Hermes retries up to 5 times with exponential backoff.

5. **No `workdir` → server runs in Hermes home** — If you don't specify
   `workdir`, the server's cwd is the Hermes home directory
   (`~/.hermes/` or `~/AppData/Local/hermes/`). Most servers that use
   relative paths (e.g. `./gitmcp.db`) will fail. Always set `workdir` for
   project-local servers.
