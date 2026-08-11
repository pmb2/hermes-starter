# Dual Gateway Architecture: Discord + Spacebar Simultaneously

## Problem

Hermes needs to connect to BOTH the live Discord API AND a self-hosted Spacebar server simultaneously. The Discord adapter (plugins/platforms/discord/adapter.py) has Spacebar monkey-patches built in, but the patch modifies global `discord.py` module state — one adapter instance can't coexist with another.

## Constraint Analysis

| Constraint | Detail | 
|---|---|
| YAML dict key uniqueness | `platforms:` in config.yaml is a dict — only one `discord:` block allowed |
| Platform enum singleton | `GatewayConfig.platforms` is `Dict[Platform, BasePlatformAdapter]` — `Platform.DISCORD` maps to exactly one adapter |
| Global discord.py state | Spacebar patches modify `discord.http.Route.BASE`, `DiscordWebSocket.DEFAULT_GATEWAY`, `HTTPClient.request`, `Client.login` — module-level globals shared by ALL instances |
| No save/restore | `_apply_spacebar_patches()` (adapter.py:667) NEVER restores originals — not on disconnect, not on error |

## Recommended Approach: Option B — Register "spacebar" as a Separate Plugin Platform

### What You Need

1. **Create `plugins/platforms/spacebar/` with its own `plugin.yaml` and `__init__.py`**

   ```
   plugins/platforms/spacebar/
   ├── __init__.py        # exports register(ctx)
   ├── plugin.yaml        # name: spacebar-platform, requires SPACEBAR_BOT_TOKEN
   └── adapter.py         # wraps DiscordAdapter with Spacebar-specific config
   ```

   `plugin.yaml`:
   ```yaml
   name: spacebar-platform
   version: 1.0.0
   description: Spacebar (self-hosted Discord clone) platform adapter
   platform: true
   required_env:
     - SPACEBAR_BOT_TOKEN
   optional_env:
     - SPACEBAR_API_BASE
     - SPACEBAR_GUILD_ID
   ```

2. **Add `_unapply_spacebar_patches()` in DiscordAdapter**

   In `plugins/platforms/discord/adapter.py`, save the originals before patching, restore on disconnect:

   ```python
   def _save_originals(self):
       import discord.http, discord.gateway
       self._saved = {
           'route_base': discord.http.Route.BASE,
           'default_gateway': discord.gateway.DiscordWebSocket.DEFAULT_GATEWAY,
           'http_client_request': ...,
           'client_login': ...,
       }
   
   def _unapply_spacebar_patches(self):
       import discord.http, discord.gateway
       discord.http.Route.BASE = self._saved['route_base']
       discord.gateway.DiscordWebSocket.DEFAULT_GATEWAY = self._saved['default_gateway']
       # ... restore other globals
   ```

3. **Wire both in config.yaml**

   ```yaml
   platforms:
     discord:
       enabled: true
       bot_token: ${DISCORD_BOT_TOKEN}
     spacebar:
       enabled: true
       bot_token: ${SPACEBAR_BOT_TOKEN}
       extra:
         base_url: http://localhost:3100/api/v9
         ws_url: ws://localhost:3100/
   ```

4. **Apply Yaml config in spacebar adapter's register()**

   The `apply_yaml_config_fn` translates `spacebar:` config keys into env vars, same pattern as the Discord adapter.

## Alternative: Option A — Separate Gateway Subprocess (Simpler But More Resource-Heavy)

Instead of modifying the adapter, run a second gateway instance:

```bash
# Create a Spacebar-specific profile
hermes profile create spacebar-bridge --copy-from default

# Configure it with Spacebar API base
# Set DISCORD_BOT_TOKEN, SPACEBAR_API_BASE=http://localhost:3100/api/v9
# Then run as a second gateway:
hermes -p spacebar-bridge gateway run --replace
```

This avoids ALL adapter changes. The subprocess approach is simpler but uses ~100MB RAM per additional gateway.

## Verification

- Both platform adapters connect independently (check `gateway_state.json` per profile)
- Messages sent to Discord appear via the Discord adapter
- Bot can send messages to Spacebar channels via the Spacebar adapter
- Channel directory in config.json lists both platforms
- Cron deliveries can target either platform
