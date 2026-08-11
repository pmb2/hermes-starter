# Discord Gateway Setup

Hermes speaks Discord natively — one bot, multiple **personas**, one per channel.
Each channel can have its own agent identity (Dev, Intel, Ops…) that auto-responds
when you message in that channel.

## 1. Create the bot

1. <https://discord.com/developers/applications> → New Application
2. Bot tab → Reset Token → copy token → `DISCORD_BOT_TOKEN` in `.env`
3. **Privileged Gateway Intents** → enable **Message Content Intent** ← required,
   otherwise the bot is silent. Enable **Server Members Intent** if you use
   `DISCORD_ALLOWED_USERS`.
4. OAuth2 → URL Generator → scope `bot` + permissions (`Send Messages`,
   `Read Messages/View Channels`, `Embed Links`, `Attach Files`, `Add Reactions`).
   Open the URL and add the bot to your server.

## 2. Wire config

`.env`:

```bash
DISCORD_BOT_TOKEN=...
DISCORD_HOME_CHANNEL=<id of your home channel>
```

`config.yaml`:

```yaml
discord:
  require_mention: true          # reply without @mention only in persona channels
  channel_prompts:
    '<channel-id>': 'You are Dev, the Development Lead. ...'
```

Channel IDs: Settings → Advanced → Developer Mode → right-click channel → Copy ID.

## 3. Run

```bash
hermes gateway run        # foreground first; watch it come online
hermes gateway install    # then as a background service
hermes gateway status
```

Logs: `~/AppData/Local/hermes/logs/gateway.log` (Windows) / `~/.hermes/logs/gateway.log`.

## 4. Conversation model

| Where | Behavior |
|-------|----------|
| Channel with a `channel_prompts` entry | Agent auto-responds with that persona (no @mention needed) |
| Channel without a prompt | Agent replies only when @mentioned |
| Home channel | Undirected/scheduled messages land here |

In-session Discord commands: `/restart` (reload config), `/sethome` (set current
channel as home), `/status`, `/platforms`.

## 5. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Silent bot | Enable Message Content Intent → `/restart` |
| 403 on messages | Re-invite with `Send Messages` permission |
| Config changes ignored | `/restart` in Discord (gateway caches config at boot) |
| Bot sees nothing | Check bot role can read the channel; check `DISCORD_ALLOWED_CHANNELS` isn't filtering it out |