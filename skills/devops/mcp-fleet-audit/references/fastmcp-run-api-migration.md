# FastMCP.run() API Migration (fastmcp 3.x)

## The Breakage

**fastmcp <=0.4** accepted `host` and `port` keyword arguments in `mcp.run()`:
```python
mcp.run(transport="sse", host="localhost", port=8030)
```

**fastmcp 3.x** removed `host` and `port` from `run()`. Only `transport` and `mount_path` are accepted:
```python
# Signature in fastmcp 3.4.2:
def run(self, transport="stdio", mount_path=None) -> None
```

## Error When Hit

```
TypeError: FastMCP.run() got an unexpected keyword argument 'host'
# or
TypeError: FastMCP.run() got an unexpected keyword argument 'port'
```

## Fixes

### For Hermes stdio integration (preferred):
Replace with:
```python
mcp.run(transport="stdio")
```
Then wire as a stdio subprocess in Hermes `config.yaml` — the agent spawns it directly.

### For standalone SSE hosting:
Use uvicorn with `mcp.sse_app()`:
```python
import uvicorn
app = mcp.sse_app()
uvicorn.run(app, host="localhost", port=8030)
```

### For StreamableHTTP:
```python
mcp.run(transport="streamable-http", mount_path="/mcp")
```
Note: `mount_path` may or may not be accepted depending on exact fastmcp version.

## Checking the Installed Version

```bash
python -c "import fastmcp; print(fastmcp.__version__)"
```

fastmcp 3.4.2 is the version that triggered this failure. The transition happened between fastmcp 1.0 and 3.0.

## Example: AI Scientist MCP Server

The `hermes_mcp_server.py` at `${MY_REPOS}\Documents\github\AI-Scientist\` had this code:
```python
# Before (broken on fastmcp 3.4.2):
print("Starting AI Scientist MCP server on http://localhost:8030/sse")
mcp.run(transport="sse", host="localhost", port=8030)

# After (working on fastmcp 3.4.2):
mcp.run(transport="stdio")
```

The `--stdio` flag branch (`if args.stdio:`) was already correct — only the default branch needed the fix.