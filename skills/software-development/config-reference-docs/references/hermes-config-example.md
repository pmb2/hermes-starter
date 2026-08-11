# Config Reference Example

## Session: Scribe Pulse — Jul 14 2026

The `config.yaml` for hermes-config had:
- 840 lines, 0 inline comments
- 73 top-level sections
- Grown 46% (from 575 lines) since the directory README was created
- The largest sections were `display` (39 keys), `mcp_servers` (24 servers), `terminal` (24 keys), `agent` (19 keys)

### Commands Used

```python
import yaml
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Show structure
def show_structure(data, depth=0):
    if not isinstance(data, dict): return
    for k, v in data.items():
        prefix = "  " * depth
        if isinstance(v, dict):
            print(f"{prefix}{k}: [{len(v)} sub-keys]")
            show_structure(v, depth+1)
        elif isinstance(v, list):
            print(f"{prefix}{k}: [{len(v)} items]")
        else:
            print(f"{prefix}{k}: {str(v)[:50]}")
```

### Key Defaults Extraction

Target sections with most impact on daily operation:
- **agent**: max_turns (140), reasoning_effort (medium), clarify_timeout (600)
- **delegation**: max_concurrent_children (3), max_spawn_depth (1), child_timeout_seconds (600)
- **compression**: target_ratio (0.2), threshold (0.66), protect_first_n (3)
- **security**: redact_secrets (false), tirith_enabled (true)
- **terminal**: backend (local), timeout (180), docker_image (nikolaik/python-nodejs:python3.11-nodejs20)

### Result

`config/CONFIG_REFERENCE.md` — 9.1KB, ~170 lines, covering 73 sections grouped into 10 domains, with MCP server catalog (24 servers across 6 categories) and common tuning table (8 patterns).
