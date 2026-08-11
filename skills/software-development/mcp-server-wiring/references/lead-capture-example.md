# Lead-Capture MCP Server — Wiring Example

Session reference: the operator's website-landlord project lead-capture module wired as
5 MCP tools consumed by Hermes Agent.

## Source module: `src/landlord/lead_capture/mcp_server.py`

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("lead-capture")

@mcp.tool()
def lead_capture_health():
    """Check connectivity of all configured data sources and the publisher."""
    ...

@mcp.tool()
def lead_capture_new_businesses(states: str = "DE,WY,NV", days_back: int = 1) -> str:
    """Check Secretary of State registries for newly formed businesses."""
    ...

# Tools with many params use Pydantic input models:
@mcp.tool()
def lead_capture_generate_leads(
    niche: str,
    location: str,
    radius: int = 15,
    max_leads: int = 50,
    source: str = "google_maps",
    min_rating: float = 4.0,
    max_domain_price: float = 60.0,
    search_only: bool = False,
) -> str:
    """Find businesses matching a niche in an area, suggest domains, generate websites."""
    ...
```

## Pitfalls encountered

- **FastMCP constructor does not accept `description=`** on older `mcp` library
  versions. Omit it — use the docstring on each `@mcp.tool()` instead.
- **MCP server importerror at startup**: test with
  `python -c "from your_module import mcp"` before wiring to Hermes. If a
  dependency is missing, the server silently fails.
- **Env vars must be listed explicitly** under `env:` in the config. Shell
  environment is NOT inherited by the MCP subprocess.
- **Absolute paths for workdir and PYTHONPATH** on Windows prevent ambiguity
  when Hermes spawns the subprocess from a different working directory.

## Registration: `.mcp.json` + `~/.hermes/config.yaml`

```json
{
  "mcpServers": {
    "website-landlord-lead-capture": {
      "command": "python",
      "args": ["-m", "landlord.lead_capture.mcp_server"],
      "env": { "PYTHONPATH": "src" }
    }
  }
}
```

For user-level: add an `mcp_servers.` entry in `~/.hermes/config.yaml` with
full `workdir`, `timeout`, `env` (explicit API key passthrough).

## Verification

```
$ python -c "from landlord.lead_capture.mcp_server import mcp; tools = mcp._tool_manager.list_tools()"
5 tools: lead_capture_health, lead_capture_new_businesses, lead_capture_generate_leads, lead_capture_check_domain, lead_capture_workflow_status
```
