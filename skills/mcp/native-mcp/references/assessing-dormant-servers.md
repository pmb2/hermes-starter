# Assessing Dormant / Complete-but-Unconfigured MCP Servers

Some MCP servers in your fleet are fully built, importable, and functional — but never wired into any `config.yaml`. They sit idle until assessed and onboarded. This reference covers the assessment pipeline for that category.

## When to Use This

You discover a complete MCP server project on disk at a known path (e.g. `git-mcp/services/firefox-remote-mcp/`) or hear about one that "just needs config" to go live. You need to confirm it's truly ready before adding it to `config.yaml` and restarting Hermes.

## Assessment Pipeline

### 1. Directory & Project Existence
Check the directory has the expected structure:
```bash
ls <project-dir>/    # should show pyproject.toml, app/, README, etc.
```

### 2. Import Test
Try importing the server module. For MCP SDK servers:
```python
cd <project-dir> && python -c "
import sys; sys.path.insert(0, '.')
from app.main import mcp
print(f'✅ Module: {type(mcp).__module__}')
"
```

### 3. SDK Fingerprinting 🔑
**This matters.** The two MCP SDKs expose tool listing differently:

- **`mcp.Server`** (older SDK, `from mcp.server import Server`):
  - No `list_tools()` method on the module at import time
  - Tools are registered internally via `server.tool()` decorator
  - To count tools without running the server, grep for schema constants:
    ```bash
    grep -c "SCHEMA" app/main.py
    ```
  - Full tool list requires starting a ClientSession

- **`fastmcp.FastMCP`** (newer SDK, `from mcp.server.fastmcp import FastMCP`):
  - Has an async `mcp.list_tools()` method
  - Can test with `asyncio.run(mcp.list_tools())` directly

Example fingerprinting:
```python
import sys; sys.path.insert(0, '.')
from app.main import mcp
# Check which class
print(type(mcp).__name__)  # 'Server' or 'FastMCP'
```

### 4. Dependency Check
Read `pyproject.toml` and confirm:
- `mcp>=1.0.0` or similar SDK dependency present
- Pydantic versions compatible (pin `pydantic>=2.10,<2.14` if needed)
- Any SDK-specific tools (websockets, httpx) declared
- Known-compatible version combos:
  - `fastmcp>=0.4,<1.0` + `mcp>=1.0,<1.2` (stable)
  - `fastmcp>=1.0` + `mcp>=1.27` (newer, may have issues)

### 5. External Binary / Service Dependency
Check what the server needs to actually *connect to* (not just import):
```bash
# Firefox Remote Debugging
which firefox 2>/dev/null || ls "/c/Program Files/Mozilla Firefox/firefox.exe"

# Headless browser (Playwright-based)
which chromium-browser 2>/dev/null

# Database (SQLite check)
ls data/*.db 2>/dev/null

# API-dependent (needs .env with tokens)
cat .env.example 2>/dev/null
```

### 6. Tool Definition Count
For `mcp.Server` (older SDK), count static tool schemas:
```bash
grep -c "_SCHEMA" app/main.py
```
For `fastmcp.FastMCP`, this IS the real tool count. For `mcp.Server`, it's a lower-bound estimate (may miss tools registered dynamically).

### 7. Config Readiness Assessment
Based on the server type and dependencies, determine the correct config.yaml entry shape:

| Server Type | Transport | Command Pattern |
|-------------|-----------|-----------------|
| `mcp.Server` (stdio) | stdio | `python -m app.main` |
| `fastmcp.FastMCP` | stdio | `uv run python -m app.main` (via uv) |
| HTTP-based | url | `url: "http://localhost:PORT/mcp"` |

Also check:
- Does the server need environment variables (entry in `env:`)?
- Does it need a specific `os.chdir()` on startup? (No Hermes `workdir` support)
- Does the server already `os.chdir()` in its own entry point?

## Common Findings

- **SDK mismatch confusion**: Trying `asyncio.run(mcp.list_tools())` on an `mcp.Server` instance fails with `AttributeError`: `module 'mcp' has no attribute 'list_tools'`. The real `list_tools()` is on the `ClientSession`, not the server module. Always fingerprint first.
- **Dormant but complete**: Some servers are 100% ready but sit unconfigured because nobody prioritized the config entry. These are the highest-value targets.
- **Firefox-remote-mcp pattern**: A fully built server with 23+ tool definitions (tabs, scripts, screenshots, forms, click, scroll, history) that imports cleanly, has proper pyproject.toml, and Firefox at standard path — just needs `config.yaml` entry and `firefox --remote-debugging-port 9222` launch.
