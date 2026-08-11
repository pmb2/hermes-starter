# Bridge Control Panel (HTTP Server)

The bridge includes an HTTP control server (via `aiohttp.web`) for on/off toggling.

## Endpoints

| Endpoint | Method | Response |
|----------|--------|----------|
| `/` or `/status` | GET | `{"enabled": bool, "status": "running", "discord_connected": bool, "spacebar_connected": true}` |
| `/toggle` | POST | Flips enabled state, returns `{"enabled": bool}` |
| `/enable` | POST | Sets enabled=true |
| `/disable` | POST | Sets enabled=false |

## Usage

```bash
curl -s http://127.0.0.1:9099/status
curl -s -X POST http://127.0.0.1:9099/disable
curl -s -X POST http://127.0.0.1:9099/enable
```

## Implementation

The `BridgeControl` class initializes an `aiohttp.web.Application` with routes,
starts a `TCPSite`, and stores an `enabled` boolean. Both `DiscordListener`
and `SpacebarListener` check `self.bc.enabled` before forwarding messages.

```python
class BridgeControl:
    def __init__(self, host="127.0.0.1", port=9099):
        self.enabled = True
        # ...routes for /status, /toggle, /enable, /disable

    async def start(self):
        app = web.Application()
        app.router.add_get("/", self.handle_status)
        app.router.add_post("/toggle", self.handle_toggle)
        # ...
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
```

## Guard in Message Handlers

Every inbound message handler (Discord `on_message`, Spacebar `_handle_message`)
checks the enabled flag as the second gate (after author self-check, before
loop prevention):

```python
async def on_message(self, message):
    if message.author.id == self.user.id:
        return
    if not self.bc.enabled:
        return
    if not self.lp.is_new(str(message.id)):
        return
```

## Wiring

In `main()`, the BridgeControl is created before the Spacebar API session,
started after the API authenticates, and passed to both listeners:

```python
bridge_control = BridgeControl()
await bridge_control.start()
discord_client = DiscordListener(sb_api, loop_prev, chan_map, bridge_control)
bridge_control.discord = discord_client  # for status endpoint
sb_listener = SpacebarListener(sb_api, discord_client, loop_prev, chan_map, bridge_control)
```
