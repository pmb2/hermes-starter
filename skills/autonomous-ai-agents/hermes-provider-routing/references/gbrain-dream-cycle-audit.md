# gbrain Dream-Cycle Audit & Migration

## Dream-Cycle Audit Log

The dream-cycle logs budget and model usage per phase to `~/.gbrain/audit/dream-budget-YYYY-Www.jsonl`.

Each entry records:
- `phase`: which dream sub-phase (`propose_takes`, `synthesize`, `patterns`, etc.)
- `model`: the model actually used (e.g. `claude-sonnet-4-6`)
- `estimated_cost_usd`: per-call estimate
- `cumulative_cost_usd`: running total within the cycle
- `budget_usd`: configured budget cap

### Check dream-cycle usage

```bash
cat ~/.gbrain/audit/dream-budget-*.jsonl | python -c "
import sys,json
for line in sys.stdin:
    e=json.loads(line)
    print(f\"{e['phase']:30s} {e['model']:20s} \${e['estimated_cost_usd']:.3f} cumul=\${e['cumulative_cost_usd']:.3f}\")
"
```

### Detect if dream-cycle is using wrong provider

If the model column shows `claude-*` or `gpt-*` models when you configured opencode-go, it means:
1. Per-task overrides are still pointing to the old model (check via `gbrain models`) 
2. Or the per-task override wasn't cleared and inherited from the wrong tier

## Migration: Anthropic → opencode-go (Complete Recipe)

### Step 1: Set model default
```bash
gbrain config set models.default "openai:deepseek-v4-flash"
```

### Step 2: Set tier defaults (optional — inherit from models.default)
```bash
gbrain config set models.tier.utility "openai:deepseek-v4-flash"
gbrain config set models.tier.reasoning "openai:deepseek-v4-flash"
gbrain config set models.tier.deep "openai:deepseek-v4-flash"
gbrain config set models.tier.subagent "openai:deepseek-v4-flash"
```

### Step 3: Set provider base URL (openai → opencode-go)
```bash
gbrain config set provider_base_urls.openai "https://opencode.ai/zen/go/v1"
```

### Step 4: Add MCP env vars in Hermes config.yaml
```yaml
mcp_servers:
  gbrain:
    args: [serve]
    command: gbrain
    env:
      PATH: ${USER_HOME}/.bun/bin;${USER_HOME}/AppData/Roaming/npm;${PATH}
      OPENAI_API_KEY: ${OPENCODE_GO_API_KEY}
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
    timeout: 300
```

### Step 5: Verify routing
```bash
gbrain models
```
Confirm all tasks resolve to `openai:deepseek-v4-flash` (not `anthropic:claude-*`).

### Step 6: Reload MCP
`/reload-mcp` in Hermes, or restart the gateway.
