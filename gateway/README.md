# Gateway

The gateway connects Hermes to messaging platforms so your agents live where you chat.
This kit covers the two setups used in production: **Discord** and **Buzz** (Nostr relay).

```
┌──────────────────────────────────────────────────────┐
│                    Hermes Agent                      │
│            (model router / fallback chain)           │
└─────────┬────────────────────────────┬───────────────┘
          │                            │
   ┌──────▼───────┐           ┌────────▼────────┐
   │  Discord     │           │  Buzz relay     │
   │  gateway     │           │  (ws://local)   │
   │  personas    │           │  per-agent      │
   │  per channel │           │  Nostr keys     │
   └──────┬───────┘           └────────┬────────┘
          │                            │
    your Discord server          Buzz Desktop / relay
```

## Guides

- **[discord.md](./discord.md)** — bot creation, intents, channel personas, gateway lifecycle
- **[buzz.md](./buzz.md)** — local relay, key generation, bridge, per-agent identities

## Platform matrix

| Platform | Requirement | Agent identity model |
|----------|-------------|----------------------|
| Discord | Bot token + Message Content Intent | One bot, per-channel personas via `channel_prompts` |
| Buzz | Local Nostr relay (`ws://localhost:3000`) | Each agent has its own keypair — @mention routes to the persona |
| Telegram / Slack / etc. | Tokens per platform | `hermes gateway setup` handles these natively |

Start everything:

```bash
hermes gateway start          # Discord / native platforms
python scripts/start_buzz_bridge.py   # Buzz bridge (separate process)
```