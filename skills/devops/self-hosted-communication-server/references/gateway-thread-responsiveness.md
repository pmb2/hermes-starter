# Gateway Thread Responsiveness — Configuring Free Response Channels

When a Hermes gateway connected to Spacebar doesn't respond to messages
in threads (or in any channel), the root cause is usually one of two
configuration gaps.

## Root Cause 1: No Free Response Channels

The Hermes discord adapter's `on_message` handler checks `free_response_channels`
before delivering a message to the agent. If the channel is not in the free
response list AND the bot isn't @mentioned, the message is silently dropped.

```python
# adapter.py on_message handler logic:
_channel_id = str(message.channel.id)
_parent_id = None
if hasattr(message.channel, "parent_id") and message.channel.parent_id:
    _parent_id = str(message.channel.parent_id)
_free_channels = adapter_self._discord_free_response_channels()
_channel_ids = {_channel_id}
if _parent_id:
    _channel_ids.add(_parent_id)  # Thread parent is also checked
if "*" not in _free_channels and not (_channel_ids & _free_channels):
    return  # Message silently dropped here
```

Note: The code already handles **thread parent channels** — if `parent_id` is
set on the channel object, both the thread ID and parent ID are checked
against the free response list.

**Fix:** Set `DISCORD_FREE_RESPONSE_CHANNELS` in the profile's `.env`:

```env
DISCORD_FREE_RESPONSE_CHANNELS=<discord-channel-id>,<discord-channel-id>,...
```

Or set to `*` to allow all channels:
```env
DISCORD_FREE_RESPONSE_CHANNELS=*
```

Alternatively, disable the mention requirement entirely:
```env
DISCORD_IGNORE_NO_MENTION=false
```

With `DISCORD_IGNORE_NO_MENTION=false`, the bot responds to every message
in every channel (subject to `DISCORD_ALLOWED_USERS`).

## Root Cause 2: DISCORD_ALLOWED_USERS Excludes the Sender

The `DISCORD_ALLOWED_USERS` env var (global `.env`) limits who can interact
with the bot to specific Discord/Spacebar user IDs. If the sender's Spacebar
user ID is not in this list, the bot ignores them regardless of channel
membership.

The global `.env` file often has this set to a Discord user ID from an
earlier configuration:

```env
# ~/AppData/Local/hermes/.env (global)
DISCORD_ALLOWED_USERS=<discord-channel-id>  # the.engineer Discord ID
```

**Problem:** Spacebar user IDs are DIFFERENT from Discord user IDs. The
same the operator has a Discord ID (`<discord-channel-id>`) and a Spacebar ID
(`<discord-channel-id>`). Both must be in the allowlist if the bot needs
to respond in both environments.

**Fix:** Add the Spacebar user ID to the global allowlist:

```env
DISCORD_ALLOWED_USERS=<discord-channel-id>,<discord-channel-id>
```

You can find the Spacebar user ID by logging in and checking `/users/@me`
via the API, or by querying the database:
```sql
SELECT id, username FROM users WHERE username = 'the operator';
```

## Root Cause 3: Bot Not Joined to Threads (Private Threads Only)

For private threads, Discord requires the bot to explicitly join via
`PUT /channels/{thread_id}/thread-members/@me` before it can read messages.
The Hermes gateway does not auto-join threads.

**Workaround:** Use `DISCORD_IGNORE_NO_MENTION=false` combined with
public threads only. Spacebar does not differentiate between public and
private thread membership the way Discord does.

## Verification

After making config changes, restart the gateway and send a test message
in a thread:

```bash
# Check the gateway picked up the new config
grep -i "free_response\|ignore_no_mention\|allowed_users" ~/.hermes/profiles/<profile>/.env

# Restart
kill <gateway_pid>
python scripts/spacebar-gateway.py <profile>
```

If the bot still doesn't respond, check the gateway log for:
- `"Message from unauthorized user"` — DISCORD_ALLOWED_USERS issue
- `"MESSAGE_CREATE"` events arriving — WebSocket is working
- Any exception tracebacks — could be a channel type discord.py doesn't expect
