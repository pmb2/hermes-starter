# Buzz Bridge Setup

The Buzz bridge connects your Hermes agents to a **local Buzz relay** (Nostr-based,
`ws://localhost:3000`), giving every agent its **own identity** — send `@AgentName`
and that agent replies from its own keypair. No shared account, fully attributable.

```
Buzz Desktop ──▶ Local Relay (ws://localhost:3000)
                        │
        Supervisor (operator key, subscribes to all channels)
                        │
        @mention detected ──▶ reply posted from the @mentioned agent's key
```

## 1. Run a local relay

Any Nostr relay works locally. Use the `buzz-stack.sh` launcher or your preferred
Nostr relay implementation:

```bash
bash scripts/buzz-stack.sh     # brings up relay + bridge
```

Set `BUZZ_RELAY_URL=ws://localhost:3000` in `.env`.

## 2. Generate agent identities

```bash
python scripts/generate_buzz_keys.py        # fresh keypairs for N identities
python scripts/update_buzz_env.py           # exports them to buzz_keys.env
```

Keep `buzz_keys.env` private (gitignored). These are real signing keys.

> ⚠️ Never reuse identities from someone else's deployment. Generate fresh ones.

## 3. Start the bridge

```bash
python scripts/start_buzz_bridge.py         # auto-restart wrapper, logs to bridge.log
```

The supervisor opens one persistent connection (the operator's key), subscribes to
all channels, and spawns a reply thread per @mention. Replies are signed by the
@mentioned agent's own key.

## 4. Watchdog (recommended)

```bash
hermes cron create 'every 15m' --no-agent --script buzz_watchdog.py
```

Restarts the bridge if it dies.

## 5. Files

| File | Purpose |
|------|---------|
| `buzz_agent_bridge.py` | Bridge core — supervisor + per-agent replies |
| `buzz_client.py` | Nostr WebSocket client with event signing |
| `start_buzz_bridge.py` | Persistent wrapper |
| `buzz_watchdog.py` | Health watchdog |
| `generate_buzz_keys.py` | Identity generation |
| `buzz_channels.json.example` / `channel_reps.json.example` | Channel + representative mapping templates |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| No replies | Relay up? `BUZZ_RELAY_URL` correct? Keys generated? |
| Replies from wrong identity | Every agent must have its own keypair in `buzz_keys.env` |
| Duplicate messages | Bridge dedups via a bounded SEEN set — check `bridge.log` for restarts |
| Relay refuses connection | Some relays require NIP-42 auth — the bundled client handles it; check relay config |