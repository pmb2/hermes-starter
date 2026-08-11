# Buzz Real-Time Adapter — Auto-Reconnect & Subscription Management

The `BuzzPlatformAdapter` class implements the Hermes gateway's
`BasePlatformAdapter` ABC for real-time buzz relay interaction.

## Architecture

```
GatewayRunner
  └── BuzzPlatformAdapter
        └── BuzzRealtimeClient (persistent WebSocket)
              ├── connect() – NIP-42 auth
              ├── subscribe(channels, callback) – REQ subscriptions
              ├── _listen_loop() – background thread, reads incoming events
              ├── send_channel_message(channel, text) – kind 9 events
              └── _reconnect() – auto-recovery on disconnect
```

## Thread Model

The adapter runs its own daemon thread (`_listen_loop`) that reads the
WebSocket in a tight loop with a 1-second timeout. Incoming EVENT messages
are dispatched to a callback that forwards them to the gateway's message
handler. The thread is `daemon=True` — it dies when the gateway process exits.

## Auto-Reconnect

When the WebSocket disconnects:

1. `_listen_loop` catches the exception
2. Logs the error
3. Calls `_reconnect()` which:
   - Closes the old socket
   - Creates a new connection
   - Re-authenticates via NIP-42
   - Re-issues all active subscriptions
4. Retries up to 3 times with 5-second backoff

## Subscription Management

Subscriptions are tracked in `_subs` dict keyed by sub_id:

```python
self._subs[sub_id] = {
    "channel": channel_uuid,
    "filter": filter_dict,  # {"kinds": [9], "limit": 0}
}
```

On reconnect, all subscriptions are re-issued with new sub_ids. The
`_subs` dict is protected by a threading lock.

## Channel UUID Resolution

Messages reference channels by UUID (`h` tag), not by name. The adapter
loads `buzz_channels.json` and resolves names on-the-fly:

```python
def resolve_channel_uuid(channel: str) -> str:
    if '-' in channel and len(channel) == 36:
        return channel  # already a UUID
    cmap = _load_channel_map()
    return cmap.get(channel, channel)  # fallback to raw string
```

## Configuration Per Profile

```yaml
platform: buzz
buzz_relay_url: ws://localhost:3000
buzz_secret_key: <from_env>
buzz_channel_uuids: <uuid1 uuid2 uuid3>
```

The adapter reads its config from env vars (`BUZZ_RELAY_URL`,
`BUZZ_SECRET_KEY`, `BUZZ_CHANNEL_UUIDS`) set per-profile in `.env`.

## Known Limits

- No typing indicators (Nostr has no equivalent)
- No message streaming (events are sent in full, not streamed)
- No edit/delete support yet
- No NIP-04 encrypted DMs yet
