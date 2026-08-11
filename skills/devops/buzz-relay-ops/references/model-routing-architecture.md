# Buzz Agent Fleet — Model Routing Architecture

> Reference for `buzz-relay-ops` — how to route LLM calls for the Buzz agent fleet through OmniRoute combos.

## Cost-Optimized Model Hierarchy (the operator's Spec)

### Agent Workhorse Combo (`agent-workhorse-combo`)

**"Free first, then subscription, only use paid when necessary."**

```
Priority 1: oc/deepseek-v4-flash-free      FREE — OpenCode Zen (no auth needed)
Priority 2: opencode-go/deepseek-v4-flash   PAID — OpenCode Go subscription
Priority 3: yunwu/deepseek-v4-flash         PAID — YunWu (last resort)
Priority 4: openrouter/google/gemma         FREE — emergency only
```

Applied to all non-CoS agents by default. Free tier handles 90%+ of volume (status checks, channel replies, simple lookups). Go subscription catches overflow. YunWu paid only fires when both free + subscription fail.

### Chief of Staff Smart Combo (`cos-smart-combo`)

**"Routine queries use DeepSeek. Tough queries use GPT 5.6 SOL."**

```
Priority 1: yunwu/deepseek-v4-flash        Smart/cheap for routine queries (~80%)
Priority 2: yunwu/gpt-5.6-sol              Reasoning, analysis, planning (~20%)
Priority 3: yunwu/gpt-5.6-sol-max          Extreme complexity (rare)
```

OmniRoute combos handle fallback naturally: if Priority 1 returns an error/timeout/rate limit, Priority 2 auto-kicks in. No query classifier needed. CoS can also explicitly route to the higher model for complex tasks via model override.

## Verified Model Availability (2026-08-10)

| Model ID | Route | Status |
|----------|-------|--------|
| `oc/deepseek-v4-flash-free` | OpenCode Zen → OmniRoute | Available, FREE |
| `opencode-go/deepseek-v4-flash` | OpenCode Go sub → OmniRoute | Available, paid |
| `yunwu/deepseek-v4-flash` | YunWu → OmniRoute | ✅ HTTP 200 verified |
| `yunwu/deepseek-v4-pro` | YunWu → OmniRoute | Available |
| `yunwu/gpt-5.6-sol` | YunWu → OmniRoute | Available |
| `yunwu/gpt-5.6-sol-max` | YunWu → OmniRoute | Available |

## Mixed vs. Uniform Model Policy

**Capability, not constraint.** The system supports both modes:

### Uniform Mode (default)
All non-CoS agents use the same `agent-workhorse-combo`. Applied via batch config script. Benefits: predictable costs, consistent quality, simple maintenance.

### Mixed Mode (selective overrides)
A YAML manifest (`config/agent-model-overrides.yaml`) defines per-agent exceptions:

```yaml
overrides:
  dev-lead:
    model: yunwu/deepseek-v4-pro    # Code generation needs depth
  nova:
    model: yunwu/deepseek-v4-pro    # Deep research
  history-lead:
    model: oc/deepseek-v4-flash-free  # Documentation is simple, stay free
```

Agents not listed get the default uniform config. Adding an override is one line.

## OmniRoute Combo + Mapping Setup

Combos are created in OmniRoute SQLite, then durable mappings route model names to combos:

```python
# Combos (created via rewire_omniroute_mappings.py)
COMBO_TARGETS = {
    "agent-workhorse-combo": {
        "targets": [
            "oc/deepseek-v4-flash-free",
            "opencode-go/deepseek-v4-flash",
            "yunwu/deepseek-v4-flash",
        ],
        "strategy": "sequential",
    },
    "cos-smart-combo": {
        "targets": [
            "yunwu/deepseek-v4-flash",
            "yunwu/gpt-5.6-sol",
            "yunwu/gpt-5.6-sol-max",
        ],
        "strategy": "sequential",
    },
}

# Mappings (model name → combo)
MAPPINGS = [
    ("map-hermes-workhorse", "hermes/workhorse", "agent-workhorse-combo", 100),
    ("map-hermes-cos", "hermes/cos", "cos-smart-combo", 100),
]
```

## CoS Profile Config

```yaml
model:
  api_mode: chat_completions
  base_url: http://localhost:20128/v1
  api_key: <REAL_OMNIROUTE_SK_KEY>
  default: deepseek-v4-flash    # Routes through cos-smart-combo
  provider: custom:omniroute
fallback_providers:
  - model: gpt-5.6-sol
    provider: custom:omniroute
```

## Agent Profile Config (Uniform Default)

```yaml
model:
  api_mode: chat_completions
  base_url: http://localhost:20128/v1
  api_key: <REAL_OMNIROUTE_SK_KEY>
  default: deepseek-v4-flash    # Routes through agent-workhorse-combo
  provider: custom:omniroute
```

## Cost Projection

| Agent Group | Model | Monthly Est. |
|-------------|-------|--------------|
| CoS (routine, ~80 turns/day) | yunwu/deepseek-v4-flash | ~$3.00 |
| CoS (tough, ~20 turns/day) | yunwu/gpt-5.6-sol | ~$1.50 |
| 45 agents (free tier) | oc/deepseek-v4-flash-free | $0.00 |
| 45 agents (overflow) | opencode-go sub | Included |
| 45 agents (last resort) | yunwu/deepseek-v4-flash | ~$0.60 |
| **TOTAL** | | **~$5.10/mo** |

## Pitfalls

- **OmniRoute encrypted credential DB can be stale.** Direct API probes may succeed while the OmniRoute connection store reports `noauth`/`credits_exhausted`. Always verify with live probes before concluding a provider is down.
- **Free tier endpoint model name sensitivity.** `oc/deepseek-v4-flash-free` works through OmniRoute but direct HTTP calls to opencode.ai/zen may 401. Route through OmniRoute, not direct.
- **Combo cache at startup.** OmniRoute caches combos at boot. After creating/updating combos, restart the OmniRoute listener.
- **Durable mappings survive sync.** Use alias-based `map-hermes-*` mappings. Bare model→combo rows can be wiped by OmniRoute's startup sync.
