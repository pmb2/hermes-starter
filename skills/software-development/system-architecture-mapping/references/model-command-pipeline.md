# /model Command Pipeline — Hermes + OmniRoute

## Architecture Overview

```
Discord user types /model <name>
  │
  ▼
1. RelayAdapter (gateway/relay/adapter.py)
   └── Generic relay adapter, no dedicated Discord adapter in Python
   └── External connector process handles Discord WebSocket protocol
   └── Delivers MessageEvent to gateway event loop
  │
  ▼
2. Slash Dispatch (gateway/run.py)
   └── Routes "/model" → GatewaySlashCommandsMixin._handle_model_command()
  │
  ▼
3. Handler: _handle_model_command (gateway/slash_commands.py:1435)
   └── Reads current config: model.default / model.provider / model.base_url
   └── Parses flags: --provider, --global, --session, --once, --refresh
   └── OmniRoute lock guard: blocks --provider change when omniroute active
   └── No-arg path: interactive picker via list_picker_providers()
   └── Text-arg path: calls hermes_cli.model_switch.switch_model()
  │
  ▼
4. switch_model() (hermes_cli/model_switch.py:883)
   └── OmniRoute bypass guard (line 944-986):
       When provider = "omniroute" OR "custom" + base_url contains
       localhost/omniroute → LOCKED: success=True, raw model name passes
       through, provider/base_url/api_key stay unchanged.
       NO catalog validation against OmniRoute's /v1/models!
   └── With --provider: resolve_provider_full() → credentials → alias
   └── Without --provider: alias→catalog→detect_provider_for_model()
  │
  ▼
5. Config Persistence (slash_commands.py:1719-1757)
   └── Writes model.default = result.new_model to config.yaml
   └── Writes model.provider = result.target_provider
   └── Writes model.base_url = result.base_url or clears it
   └── save_config() → ~/AppData/Local/hermes/config.yaml
  │
  ▼
6. Session Override (slash_commands.py:1689-1714)
   └── _session_model_overrides[session_key] = {model, provider, ...}
   └── Persisted to session DB for restart survival
   └── Cached agent evicted → rebuilt from override on next turn
   └── In-place: cached_agent.switch_model() updates live agent if cached
  │
  ▼
7. Agent Build (agent/agent_init.py:401+)
   └── Reads model, provider, base_url, api_key as constructor args
   └── Auto-detects api_mode: omniroute (localhost:20128) → chat_completions
   └── OpenAI client built → target: http://localhost:20128/v1/
  │
  ▼
8. API Call → OmniRoute (port 20128)
   └── POST http://localhost:20128/v1/chat/completions
   └── Body: {"model": "oc/deepseek-v4-flash-free", ...}
   └── OmniRoute routes to backend (271 providers via 17 strategies)
```

## File Locations

| Component | File | Key Line |
|-----------|------|----------|
| Discord relay adapter | `hermes-agent/gateway/relay/adapter.py` | `class RelayAdapter(BasePlatformAdapter)` |
| Relay transport | `hermes-agent/gateway/relay/transport.py` | WebSocket to external connector |
| `/model` handler | `hermes-agent/gateway/slash_commands.py` | `_handle_model_command` @ line 1435 |
| Code skew guard | `hermes-agent/gateway/slash_commands.py` | `_model_switch_skew_guard()` @ line 59 |
| Slot availability check | `hermes-agent/gateway/run.py` | `_AGENT_PENDING_SENTINEL` handling |
| Model resolution helper | `hermes-agent/gateway/run.py` | `_resolve_gateway_model()` @ line 2614 |
| Model switch core | `hermes-agent/hermes_cli/model_switch.py` | `switch_model()` @ line 883 |
| Model aliases (built-in) | `hermes-agent/hermes_cli/model_switch.py` | `MODEL_ALIASES` @ line 223 |
| Flag parser | `hermes-agent/hermes_cli/model_switch.py` | `parse_model_flags_detailed()` @ line 414 |
| Persist behavior | `hermes-agent/hermes_cli/model_switch.py` | `resolve_persist_behavior()` @ line 500 |
| Picker provider listing | `hermes-agent/hermes_cli/model_switch.py` | `list_picker_providers()` @ line 2673 |
| Agent initialization | `hermes-agent/agent/agent_init.py` | `init_agent()` @ line 401 |
| Primary config file | `~/AppData/Local/hermes/config.yaml` | `model.default`, `model.provider` |
| OmniRoute server | `~/.omniroute/` | Next.js on port 20128 |
| OmniRoute model list | `http://localhost:20128/v1/models` | 140+ models |
| Gateway state | `~/AppData/Local/hermes/gateway_state.json` | Live platform status |

## Config.yaml Structure

```yaml
model:
  default: oc/deepseek-v4-flash-free    # active model ID
  provider: custom:omniroute             # provider prefix + name
  base_url: http://localhost:20128/v1    # OmniRoute endpoint
  context_length: 1000000                # optional override
  persist_switch_by_default: true        # /model without --session persists

custom_providers:
  - name: omniroute                       # resolved from custom:omniroute
    base_url: http://localhost:20128/v1
    api_key: omniroute-local
    api_mode: chat_completions
```

The `provider:` value `custom:omniroute` means:
- `custom` prefix → look in `custom_providers[]` for matching base_url
- `omniroute` → the display label in the UI
- The `custom:` prefix triggers `resolve_provider_full()` which finds the `custom_providers` entry

## OmniRoute Lock (Critical Design Detail)

When the active provider is `omniroute` (or `custom` pointing to `localhost`/port 20128):

1. **CLI/gateway guard**: `_handle_model_command()` (line 1533-1546) rejects any `--provider` change
2. **switch_model() guard** (line 944-986): Short-circuits EVERYTHING — returns `success=True` with the raw model name unchanged. No alias resolution, no catalog lookup, no provider resolution.
3. **Net effect**: You can set ANY string as the model name via `/model some-garbage`. It writes to config.yaml and returns success. Validation only happens when OmniRoute's `/v1/chat/completions` returns a 404.

**Consequence of setting an unsupported model:**
1. Config.yaml writes the bad model name
2. Agent builds OK (no validation during init)
3. First API call → OmniRoute returns 404/400
4. Agent retries (api_max_retries: 3 from config)
5. Session override stores the broken model (if --session was used)
6. On next message, the agent rebuilds with the broken model from the override
7. User stuck until `/model <valid-name>` or `/reset` clears the override

**Safe path**: The interactive picker (no-args `/model`) only shows models from OmniRoute's `/v1/models` endpoint, so picker-based switches are safe.

## Interactive Picker Flow

When `/model` is typed with no arguments:

1. `adapter.send_model_picker()` checked on the adapter (RelayAdapter supports it?)
2. `list_picker_providers()` called off the event loop (blocking I/O via `asyncio.to_thread`)
3. Builds provider model lists from:
   - Current provider's known models
   - `custom_providers[].models` from config
   - Models.dev catalog lookup
   - Capped at `max_models=50` (except OpenCode Zen/Go which are uncapped)
4. Picker sends a callback-based model list to the user
5. On selection: `_on_model_selected_scoped()` runs the switch via `switch_model()`
6. For OmniRoute: the lock guard in `switch_model()` makes the picker effectively list models from OmniRoute, and selection just changes the model name

## Resilience / What-If Scenarios

| Scenario | Outcome | Recovery |
|----------|---------|----------|
| `/model nonexistent` with OmniRoute | Writes to config, API fails at call time | `/model oc/deepseek-v4-flash-free` to fix |
| `/model nonexistent --session` | Override stored, next message fails | `/model <valid> --session` replaces override |
| OmniRoute process dies | HTTP connection error on API call | Restart OmniRoute, `/reset` clears state |
| Config.yaml corrupt | `_load_gateway_config()` returns empty dict | `hermes doctor` or manual config fix |
| Gateway code drift (git pull while running) | `_model_switch_skew_guard()` blocks the switch | `hermes gateway restart` |
