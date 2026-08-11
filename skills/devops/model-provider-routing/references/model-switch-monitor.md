# Model Switch Monitor — Real-Time Provider Change Notifications

When OmniRoute fallbacks between provider tiers, a daemon detects the switch
and sends a short Discord notification so the operator knows what model is handling
his requests.

## Architecture

```
OmniRoute Dev Log (.build/next/dev/logs/next-development.log)
       │
       ▼
model_switch_monitor.py (daemon — tails log file)
       │
       ▼
Discord notification (via Hermes gateway)
```

## Detection Patterns

The monitor parses each new log line for these patterns:

| Pattern | Trigger | Example |
|---------|---------|---------|
| `[COMBO] Routed to <model>` | Model switch | `[COMBO] Routing request to oc/deepseek-v4-flash-free` |
| `[AUTO] <model> matched no connected` | Provider exhausted | Tier exhaustion triggers fallback |
| Model name in JSON message | Any model reference | `"model":"deepseek-v4-flash"` |

Log lines are parsed as JSON first (extracting `message` field), then regex-matched.

## Tier Definitions

```python
MODEL_TIERS = {
    "oc/deepseek-v4-flash-free":  {"tier": 1, "name": "OpenCode Zen",  "quality": "DeepSeek V4 Flash"},
    "tllm/together_deepseek_v3":  {"tier": 2, "name": "Together AI",   "quality": "DeepSeek V3"},
    "auto/coding:free":           {"tier": 3, "name": "OmniRoute Auto-Free", "quality": "Best Free Coding"},
}
```

## Notification Format (Preferred — Short & Low-Key)

**On switch:**
```
↑ DeepSeek V4 Flash       ← better tier became available
↓ DeepSeek V3             ← fell back to lower tier
```

**On exhaustion:**
```
→ DeepSeek V4 Flash exhausted   ← current provider ran out
```

Arrow-only, no emoji, no "Model Switch:" prefix, no cost labeling, no full sentences.
Just the quality label. The arrow says everything:

| Arrow | Meaning |
|-------|---------|
| `↑` | Upgraded to better tier |
| `↓` | Downgraded to lower tier |
| `→` | Exhausted, falling back |

## Files

| File | Purpose |
|------|---------|
| `~/AppData/Local/hermes/scripts/model_switch_monitor.py` | Main daemon script |
| `~/OmniRoute/.build/next/dev/logs/next-development.log` | OmniRoute dev logs (tailed by monitor) |
| `~/AppData/Local/hermes/.model_switch_state.json` | Persists last active model across restarts |
| `~/AppData/Local/hermes/scripts/hermes-stack.sh` | Starts OmniRoute, Hermes-router, and the monitor |

## Running

```bash
# As daemon (background process):
python ~/AppData/Local/hermes/scripts/model_switch_monitor.py --daemon

# One-shot check:
python ~/AppData/Local/hermes/scripts/model_switch_monitor.py

# Via unified startup script (starts everything):
bash ~/AppData/Local/hermes/scripts/hermes-stack.sh
```
