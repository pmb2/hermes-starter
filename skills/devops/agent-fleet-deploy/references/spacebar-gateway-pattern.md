# Spacebar Gateway Pattern — Hermes → Self-Hosted Discord

Bridge a Hermes agent session into a Spacebar (self-hosted Discord-compatible chat) channel via a custom discord.py gateway.

## Architecture

```
Hermes Agent (hermes session / gateway plugin disabled)
    └─ spacebar-gateway.py
         ├─ discord.py WebSocket → Spacebar API (:3001/api/v9)
         ├─ Registers slash commands on guild
         ├─ Routes messages → Hermes session process()
         └─ Forwards Hermes responses → Spacebar channel
```

## Required Fixes (Windows + Spacebar)

### 1. discord.py API v9 + Route.BASE Ordering ⚠️

Spacebar caps at API **v9**. The discord.py library defaults to v10+. Force v9:

```python
# ⚠️ CRITICAL: Call _set_api_version FIRST
# It internally sets Route.BASE = 'https://discord.com/api/v{value}'
# If you set Route.BASE before calling _set_api_version(9), it gets OVERWRITTEN
from discord.http import INTERNAL_API_VERSION
discord.http._set_api_version(9)

# THEN overwrite Route.BASE with the actual URL
discord.http.Route.BASE = "https://discy.your-domain.example/api/v9"
```

**Why order matters:** `_set_api_version(9)` calls `Route.BASE = 'https://discord.com/api/v9'` internally. If you set `Route.BASE = SPACEBAR_URL` before calling it, the Spacebar URL gets silently replaced with `https://discord.com/api/v9`. The gateway then sends auth requests to discord.com instead of Spacebar → 401 → hangs forever.

**Symptom when broken:** Gateway shows `Connecting to discord...` and `Registered /` in its log, then hangs indefinitely. Never shows `✓ discord connected`.

### 2. msvcrt.locking — Windows Lock File

Python's `msvcrt.locking()` is used by gateway.lock and throws in MSYS/git-bash on Windows. Patch before any code touches the lock:

```python
import msvcrt
msvcrt.locking = lambda fd, op, nbytes: None  # noop
```

Place this at the **very top** of `spacebar-gateway.py`, before any Hermes or discord imports.

### 3. PYTHONPATH

Python needs to find the Hermes Agent source. Set before running:

```bash
export PYTHONPATH=${MY_REPOS}/hermes-agent/src
# or inline:
PYTHONPATH=${MY_REPOS}/hermes-agent/src python scripts/spacebar-gateway.py ...
```

### 4. Bot Token from Profile .env

Each Hermes agent profile has a `.env` file at `~/.hermes/profiles/<name>/.env`. Source it or pass the token directly:

```bash
source ~/.hermes/profiles/<name>/.env
# Then use $SPACEBAR_BOT_TOKEN in the script
# OR:
python scripts/spacebar-gateway.py --token "$SPACEBAR_BOT_TOKEN" ...
```

## Gateway Script Structure

```
spacebar-gateway.py/
├── Monkey-patches (msvcrt.locking first)
├── Imports (hermes_tools, discord.py, aiohttp)
├── Config (token, guild_id, api_url, profile_name)
├── SpacebarClient(discord.Client)
│   ├── on_ready() — set guild/channel, register commands
│   ├── on_message() — route to Hermes process()
│   └── on_slash_command() — handle interactions
├── hermes_process() — call Hermes agent
└── main() — run client with token
```

### Key `on_ready` Implementation

```python
async def on_ready(self):
    print(f"Logged in as {self.user}")
    guild = self.get_guild(GUILD_ID)
    if not guild:
        print(f"Guild {GUILD_ID} not found")
        return

    # Register slash commands
    await self.http.upsert_guild_commands(
        GUILD_ID,
        [
            {
                "name": "ask",
                "description": "Ask the agent a question",
                "options": [{
                    "name": "query",
                    "description": "Your question",
                    "type": 3,  # STRING
                    "required": True
                }]
            }
        ]
    )
```

## SSH Tunnel Topology

If Spacebar runs **locally** but needs to be reachable at a public domain:

```
discy.your-domain.example
    └─ Caddy (Docker on VPS 129.153.x.x)
         ├─ /api/* → 172.17.0.1:3001 (SSH tunnel → localhost:3001)
         └─ /* → 172.17.0.1:8081 (SSH tunnel → localhost:8081)
```

The SSH tunnel:
```bash
ssh -i ~/.ssh/oracle_vps \
  -o ServerAliveInterval=60 \
  -o ExitOnForwardFailure=yes \
  -N -R 0.0.0.0:3001:localhost:3001 \
  ubuntu@129.153.156.190
```

See `vps-hybrid-deployment` skill → `references/expose-local-service-via-ssh-tunnel.md` for the full tunnel setup.

## Full Start Command

```bash
cd ${MY_REPOS}/hermes-agent
PYTHONPATH=${MY_REPOS}/hermes-agent/src \
  python scripts/spacebar-gateway.py \
  --token "$SPACEBAR_BOT_TOKEN" \
  --guild "<discord-channel-id>" \
  --api-url "http://localhost:3001/api/v9" \
  --profile "dev-lead"
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `TypeError: can't access property "at", res.errors` | API server down or wrong port | Check server running, check tunnel alive, verify port match |
| `502 Bad Gateway` from Caddy | Tunnel dead or port mismatch | `ps aux | grep ssh` on local, `ss -tlnp | grep 3001` on VPS |
| `WebSocket` connection refused | Gateway port not forwarded | Add `-R 0.0.0.0:GATEWAY_PORT:localhost:GATEWAY_PORT` to SSH tunnel |
| `msvcrt.locking` error | Windows file lock in MSYS | Add monkey-patch at top of script |
| `401` on commands | Bot token wrong or not registered | Re-login the bot to get a fresh token |
| `needs to be implemented` (console) | Fermi client-side unimplemented feature | Non-blocking, ignore |
| `Cannot read properties of undefined (reading 'emojiReactionFrecency')` | Fermi client undefined state | Non-blocking, ignore |
