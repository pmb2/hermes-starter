# Native Discord Adapter for Spacebar

Since Hermes Agent v2026.6.5 (commit `34c65d44c`), the Discord adapter has
native Spacebar support built in. No wrapper scripts needed.

## Architecture

```
Profile .env
  ├── DISCORD_BOT_TOKEN=<Spacebar JWT>
  └── SPACEBAR_API_BASE=https://<host>/api/v9
       │
       ▼
gateway/config.py → load_gateway_config()
  Reads env vars, injects into Discord platform config extra dict:
    extra.base_url = "https://gc.your-domain.example/api/v9"
    extra.api_version = 9
       │
       ▼
plugins/platforms/discord/adapter.py → DiscordAdapter
  __init__() reads extra.base_url / extra.api_version from PlatformConfig
  connect() → _apply_spacebar_patches() applies ALL 16 compatibility patches
    → ALL discord.py HTTP/WS traffic goes to Spacebar server
  _discord_api_url() helper replaces hardcoded Discord CDN URLs
    → standalone sends use Spacebar API
```

## All 16 Monkey-Patches (commit 538fb4496)

When `self._api_base_url` is set (Spacebar mode detected), the adapter
applies every patch the old `spacebar-gateway.py` wrapper used:

| # | Patch | What It Fixes |
|---|-------|--------------|
| 1 | `_set_api_version(9)` | Spacebar speaks v9 API, not Discord's v10 |
| 2 | `Route.BASE` override | All REST API calls go to Spacebar URL |
| 3 | `DEFAULT_GATEWAY` override | WebSocket connects to Spacebar WS URL |
| 4 | `from_client → compress=False` | Spacebar rejects zlib-stream compression |
| 5 | Custom IDENTIFY payload | Minimal intents (769), compress=False, forced presence |
| 6 | HTTPClient.request → raw auth | Spacebar JWT doesn't use `Bot ` prefix |
| 7 | Custom slash command sync | Spacebar's application command API differs from Discord |
| 8 | `Client.login` → raw bootstrap | Spacebar uses `/users/@me` HTTP, not WS gateway login |
| 9-11 | Raw*Event null `guild_id` | Spacebar sends `guild_id: null` in DMs (crashes `int(None)`) |
| 12 | `_fill_overwrites` null guard | Spacebar sends `permission_overwrites: null` |
| 13 | `Client.dispatch` _MissingSentinel | Race condition from Spacebar's faster-ready path |
| 14 | `received_message` null guild_id | Guards 40+ state.py handlers at dispatch level |
| 15 | `TextChannel._update` safe fields | Spacebar omits fields discord.py expects |
| 16 | Lock path → `gateway.lock.spacebar` | Avoids stale Windows lock on `gateway.lock` |

All patches are applied **conditionally** — only when `extra.base_url` is
set in the platform config (i.e., `SPACEBAR_API_BASE` env var is active).
When the adapter connects to real Discord, none of these patches run.

## Deployment

### Single Profile

```bash
hermes gateway run                     # active profile
hermes -p chief-of-staff gateway run   # specific profile
hermes -p dev-lead gateway run --replace  # kill existing + start
```

### Fleet (Multi-Profile)

```bash
# scripts/fleet-deploy.py
python scripts/fleet-deploy.py                # deploy all 43 profiles
python scripts/fleet-deploy.py --status       # show running
python scripts/fleet-deploy.py --stop         # stop all
python scripts/fleet-deploy.py --list         # list profiles
```

Each gateway is a detached Windows process (`DETACHED_PROCESS |
CREATE_NO_WINDOW`). Profiles with `SPACEBAR_API_BASE` in `.env`
are auto-detected; profiles `the operator` and `docs-lead-dev` are skipped
(real Discord tokens).

### Verification

```bash
# Spacebar server reachable?
curl -I https://gc.your-domain.example/api/v9/gateway

# Gateway startup logs
tail -50 ~/AppData/Local/hermes/gateway-startup.log
tail -50 ~/AppData/Local/hermes/logs/gateway.log

# Check lock location (Spacebar uses separate lock file)
ls ~/AppData/Local/hermes/gateway.lock.spacebar
```

## Key Files Changed

| File | Change |
|------|--------|
| `gateway/config.py` | Reads `SPACEBAR_API_BASE`/`DISCORD_API_BASE` from env, injects `extra.base_url` + `extra.api_version` |
| `plugins/platforms/discord/adapter.py` | `_apply_spacebar_patches()` with 16 patches; `_is_spacebar_mode()` helper; fixed `_standalone_send` raw auth |
| `gateway/SPACEBAR.md` | Native Spacebar deployment doc |
| `gateway/FLEET.md` | Fleet management doc |
| `scripts/fleet-deploy.py` | Fleet launcher for all profiles |

## Historical Context

Previously, Spacebar compatibility required a wrapper script at
`${MY_REPOS}/Documents/github/agent-fleet/scripts/spacebar-gateway.py`
with 496 lines of monkey-patches and a `fleet-core.py` watchdog that
managed per-profile gateway processes. The wrapper was prone to a "death
loop" where exit=15 signals from fleet-core cleanup kills (not actual
gateway crashes) created the illusion of 55s crashes.

The native adapter eliminates the wrapper entirely — all 16 patches
are applied automatically when the gateway starts with a Spacebar API
base configured.
