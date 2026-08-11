# Gateway Channel Patches for Spacebar Compatibility

When running Hermes gateways against Spacebar via the `spacebar-gateway.py` wrapper,
three discord.py channel classes need `_update` patches to handle missing Spacebar fields:

## VoiceChannel -- `bitrate` not sent

Spacebar does not include the `bitrate` field for voice channels in the guild
READY payload. discord.py's `VoiceChannel._update` does `self.bitrate: int = data['bitrate']`
which raises `KeyError: 'bitrate'`, crashing the gateway before it finishes connecting.

**Patch:**
```python
import discord.channel
_original_voice_update = discord.channel.VoiceChannel._update

def _patched_voice_update(self, guild, data):
    safe_data = dict(data)
    safe_data.setdefault("bitrate", 64000)
    safe_data.setdefault("user_limit", 0)
    safe_data.setdefault("permission_overwrites", [])
    _original_voice_update(self, guild, safe_data)

discord.channel.VoiceChannel._update = _patched_voice_update
```

## CategoryChannel -- `permission_overwrites` not sent

Same pattern -- discord.py expects `permission_overwrites` but Spacebar omits
it for category channels.

**Patch:**
```python
_original_cat_update = discord.channel.CategoryChannel._update

def _patched_cat_update(self, guild, data):
    safe_data = dict(data)
    safe_data.setdefault("permission_overwrites", [])
    _original_cat_update(self, guild, safe_data)

discord.channel.CategoryChannel._update = _patched_cat_update
```

## Alternative: Patch all via `dict.setdefault` wrapper

For a more defensive approach that catches any missing fields:
```python
def _make_safe_channel_update(original_fn):
    def safe_update(self, guild, data):
        safe_data = dict(data)
        safe_data.setdefault("permission_overwrites", [])
        safe_data.setdefault("bitrate", 64000)
        safe_data.setdefault("user_limit", 0)
        safe_data.setdefault("topic", "")
        safe_data.setdefault("rate_limit_per_user", 0)
        return original_fn(self, guild, safe_data)
    return safe_update

discord.channel.TextChannel._update = _make_safe_channel_update(discord.channel.TextChannel._update)
discord.channel.VoiceChannel._update = _make_safe_channel_update(discord.channel.VoiceChannel._update)
discord.channel.CategoryChannel._update = _make_safe_channel_update(discord.channel.CategoryChannel._update)
```

## 🚨 Still Not Enough — READY Event Data Must Be Sanitized First

Even with all three channel-type patches applied, the gateway can still crash
during `parse_ready` → `_add_guild_from_data`. Discord.py's `state.py` processes
the full guild/channel structure from the READY event **before** dispatching it
to individual channel constructors. If **any** field is missing in the raw READY
data (not just in channel _update), the crash happens before the per-channel
patches ever run.

**More robust approach: sanitize the entire READY event at the gateway message
level, BEFORE discord.py's state parser sees it.**

In `spacebar-gateway.py`, extend the `_patched_received_message` function to
intercept the READY event (`t === 'READY'`) and inject defaults for every field
that discord.py expects but Spacebar omits:

```python
async def _patched_received_message(self, data):
    if isinstance(data, dict):
        d = data.get('d')
        if d:
            if data.get('t') == 'READY':
                guilds = d.get('guilds', [])
                for g in guilds:
                    # Sanitize every channel in the guild
                    for c in g.get('channels', []):
                        if not isinstance(c, dict):
                            continue
                        c.setdefault('bitrate', 64000)
                        c.setdefault('user_limit', 0)
                        c.setdefault('rate_limit_per_user', 0)
                        c.setdefault('permission_overwrites', [])
                        c.setdefault('position', 0)
                        c.setdefault('topic', '')
                        c.setdefault('nsfw', False)
                        c.setdefault('rtc_region', None)
                        c.setdefault('video_quality_mode', 1)
                        c.setdefault('last_message_id', None)
                        c.setdefault('parent_id', None)
                    # Sanitize guild-level fields
                    g.setdefault('large', False)
                    g.setdefault('unavailable', False)
                    g.setdefault('member_count', len(g.get('members', [])))
                    g.setdefault('voice_states', [])
                    g.setdefault('emojis', [])
                    g.setdefault('stickers', [])
                    g.setdefault('features', [])
    return await _original_received_message(self, data)
```

This catches ALL missing fields at once, without relying on per-channel patches
that may run too late. The per-channel `_update` patches (VoiceChannel, etc.)
are still useful as a defense-in-depth measure for GUILD_CREATE and channel
update events that arrive after the initial READY.

### Deployment

Both the READY-level sanitization and the per-channel patches should be applied
in the `patch_discord()` function of `spacebar-gateway.py`. The order matters:

1. First, patch `DiscordWebSocket.received_message` (to sanitize READY data)
2. Then, patch TextChannel, VoiceChannel, CategoryChannel `_update` (defense-in-depth)

These patches should be placed in the `patch_discord()` function of the
`spacebar-gateway.py` wrapper, after the existing `TextChannel._update` patch.
