# Discord ↔ Spacebar Bidirectional Bridge

Real-time two-way message and channel sync between a Discord server and
a self-hosted Spacebar/Fermi instance.

## Architecture

The bridge is a standalone Python daemon that connects to both platforms simultaneously:

```
Discord WS ──→ on_message ──→ Spacebar REST API (send_message)
Spacebar WS ──→ MESSAGE_CREATE ──→ Discord py (channel.send)
```

- **Discord side**: `discord.py` WebSocket client. Listens for `on_message` and `on_guild_channel_create` events.
- **Spacebar side**: Raw WebSocket connection (Discord v9 gateway protocol). Parses `MESSAGE_CREATE` and `CHANNEL_CREATE` events.
- **No database needed**: The bridge is stateless. Channel mapping is done by name at runtime.

## Requirements

```
pip install discord.py websockets aiohttp
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_BOT_TOKEN` | (from Hermes .env) | Discord bot token for reading/sending |
| `SPACEBAR_API_BASE` | `https://gc.your-domain.example/api/v9` | Spacebar REST API URL |
| `SPACEBAR_WS_URL` | `wss://gc.your-domain.example/` | Spacebar WebSocket URL |
| `BRIDGE_CHANNEL_MAP` | `./migration_data/channel_map.json` | Channel name↔ID mapping file |

When `SPACEBAR_BOT_TOKEN` is not set, the bridge logs in to Spacebar as
a regular user using `SPACEBAR_LOGIN` / `SPACEBAR_PASSWORD` (defaults:
`the operator` / `<bridge-password>`).

## Channel Map Format (1:1 ID Mapping)

The `channel_map.json` defines a bidirectional mapping between Discord and
Spacebar channels using exact Discord/channel IDs. This ensures reliable
matching even when channel names change.

```json
{
  "guild_id": "<discord-channel-id>",
  "spacebar_guild_id": "<discord-channel-id>",
  "channels": {
    "command": {
      "discord_id": "<discord-channel-id>",
      "spacebar_id": "<discord-channel-id>"
    },
    "dev": {
      "discord_id": "<discord-channel-id>",
      "spacebar_id": "<discord-channel-id>"
    }
  },
  "threads": {
    "Get it done.": {
      "discord_id": "<discord-channel-id>",
      "parent_discord": "<discord-channel-id>",
      "parent_spacebar": "<discord-channel-id>",
      "message_count": 11659
    }
  }
}
```

**Channels**: Each entry maps one Discord channel to one Spacebar channel by ID.

**Threads**: Discord thread IDs map to their parent's Spacebar channel. When a
message arrives from a Discord thread, the bridge routes it to the parent
Spacebar channel with a `[Thread: name]` content prefix.

**Verification**: Every Discord channel must have a Spacebar counterpart.
Compare counts after building:
- List all text channels from both platforms
- Query Spacebar DB: `SELECT c.name, count(m.id) FROM messages m JOIN channels c ON c.id=m.channel_id WHERE m.guild_id='<gid>' AND c.type=0 GROUP BY c.name`
- Compare against Discord export counts for the same channels
- Any gap means a missing channel or import

## Channel Matching

The bridge looks up channels by **ID** using two runtime lookup tables:

- `discord_to_spacebar`: `{discord_id -> spacebar_id}`
- `spacebar_to_discord`: `{spacebar_id -> discord_id}`

For thread messages, the bridge checks the `threads` map to find the parent
Spacebar channel and routes there with a thread prefix.

## Loop Prevention

Each relayed message ID is cached for **5 minutes** in an in-memory set.
If a message arrives on either WebSocket whose ID is in the cache, it
is silently ignored. This prevents echo loops when a relayed message
arrives back on the sender's WebSocket.

**Important:** The cache is in-memory only. If the bridge restarts, the
cache is empty, and any messages that were relayed just before the restart
will be relayed again (harmlessly — recipients see a duplicate).

## Message Format

- **Discord → Spacebar**: `**[{author_name}]** {content}` — bolded author
  name prefix. Thread messages include `[Thread: {name}]` before content.
  Attachment URLs appended on new lines.
- **Spacebar → Discord**: `**[{author_name} (Spacebar)]** {content}` —
  same format with an explicit "(Spacebar)" tag for source clarity.

## Channel Sync

When a `CHANNEL_CREATE` event fires on either side, the bridge creates
a matching channel on the other side with the same name and base type
(text → text, voice → voice, category → category). The new channel's
ID is added to the runtime channel map.

## Running

```bash
python discord-spacebar-bridge.py
```

### Windows Auto-Start (Persistent)

A batch file with infinite restart loop:

```batch
@echo off
cd /d E:\Path\To\agent-fleet
:restart
echo [%date% %time%] Bridge starting...
set DISCORD_BOT_TOKEN=
for /f "tokens=1,* delims==" %%a in ('type "%USERPROFILE%\AppData\Local\hermes\.env"') do if "%%a"=="DISCORD_BOT_TOKEN" set "DISCORD_BOT_TOKEN=%%b"
start /B /WAIT python -u scripts/discord-spacebar-bridge.py >> /tmp/bridge.log 2>&1
timeout /t 5 /nobreak >nul
goto restart
```

Add a shortcut to `shell:startup` for boot persistence.

## Verification

1. Start the bridge. Log should show:
   ```
   [Bridge] Spacebar WS connected (heartbeat=30.0s)
   [Bridge] Spacebar WS ready (session=...)
   [Bridge] Discord connected as BotName (id=...)
   ```
2. Send a message in Spacebar → check the matching Discord channel
3. Send a message in Discord → check the matching Spacebar channel
4. Check `S→D #channelname: ...` and `D→S #channelname: ...` in the logs

## Complete Audit Protocol

When asked to "deep dive every channel and thread and message" for completeness:

1. **Export all Discord data** — Fetch every message from every channel/thread
   via the Discord API (bot token). Paginate with `before` cursor, 100 per page,
   until the response is empty. Save each channel's messages to a JSON file.

2. **Query Spacebar DB** — Compare message counts per channel:
   ```sql
   SELECT c.name, count(m.id) FROM messages m
   JOIN channels c ON c.id = m.channel_id
   WHERE m.guild_id = '<spacebar_guild_id>' AND c.type = 0
   GROUP BY c.name ORDER BY c.name;
   ```

3. **Side-by-side table**:
   | Channel | Discord | Spacebar | Delta | Status |
   ✅ = identical (delta only from post-export messages)
   ❌ = gap needs import

4. **Fix gaps** — Export the missing channel to JSON, SCP to VPS, bulk INSERT
   with `ON CONFLICT (id) DO NOTHING`, update `last_message_id`.

5. **Verify structure** — Every Discord text channel must have a Spacebar
   counterpart. Remove/reconcile orphans (e.g. `general` with no Discord match).

## Troubleshooting

### Bridge connects but no messages relayed

- Check the channel map has correct Discord/Spacebar IDs for every channel.
- Run the Complete Audit Protocol to verify message counts match.
- Check `DISCORD_ALLOWED_USERS` — the user's Spacebar user ID must be in the list.
- Discord bot needs `READ_MESSAGE_HISTORY` + `SEND_MESSAGES` permissions.

### Gateway doesn't respond in threads

Three root causes (fix in the profile's `.env`):

1. **No free response channels** — Set `DISCORD_FREE_RESPONSE_CHANNELS` to a
   comma-separated list of Spacebar channel IDs, or set
   `DISCORD_IGNORE_NO_MENTION=false` to respond everywhere.
2. **DISCORD_ALLOWED_USERS mismatch** — the operator's Discord user ID differs from his
   Spacebar user ID. Both must be in the allow list.
3. **Thread parent routing** — The Hermes adapter already checks
   `message.channel.parent_id` in `on_message`. If it still fails, add the parent
   channel IDs to `DISCORD_FREE_RESPONSE_CHANNELS` explicitly.

### Discord REST API returns 403
- The bot token may only have WebSocket access, not REST API access.
- This doesn't affect the bridge — it uses discord.py's WebSocket client,
  which has different auth paths than raw REST calls.

### Loop prevention too aggressive
- The 5-minute TTL means messages relayed >5 minutes apart are treated as new.
- This is fine for normal usage. Only an issue if the same message ID appears
  on both sides more than 5 minutes apart.

### Channel not found
- New channels created outside the bridge (e.g., by another admin) won't
  be in the channel map. The bridge only mirrors channels created while
  it's running. Restart the bridge to pick up new channels, or add them
  to the channel_map.json file manually.
