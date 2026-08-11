# Spacebar Gateway Configuration

> **Context:** Hermes agents connected to a Spacebar/Harmony-compatible Discord server need specific Discord-platform config settings that differ from real Discord. This reference documents every config that matters and why.

## Config Reference

### `DISCORD_AUTO_THREAD=false` (Spacebar: REQUIRED)

Spacebar does NOT support Discord's thread API (`POST /channels/{id}/threads`). When a message arrives in a guild channel, the Hermes gateway adapter tries to create an auto-thread to isolate the conversation (like Slack threads). On Spacebar this fails with:

```
Auto-thread creation failed. Direct error: This message does not have guild info attached.
```

**Effect with default (true):** Every incoming message triggers a failed API call (wasted time). The bot never replies in the channel because it's trying to reply inside a thread that doesn't exist. the operator's messages appear to vanish.

**Effect with false:** Bot responds directly in the channel/DM. No thread creation attempted.

**Set via profile config.yaml:**
```yaml
discord:
  auto_thread: false
```

**OR profile .env:**
```
DISCORD_AUTO_THREAD=false
```

### `GATEWAY_ALLOW_ALL_USERS=true` (Fallback — affects most platforms)

The Hermes gateway enforces user allowlists by default. When starting the gateway with `HERMES_HOME` overridden to a profile directory, the profile's `.env` may not have any allowed users configured. The gateway prints:

```
No user allowlists configured. All unauthorized users will be denied.
```

Without this, **all** users (including the owner) are blocked — every message is silently dropped with `Unauthorized user: <id> (<name>) on discord`. This blocks BOTH guild channels AND DMs.

**Set via profile .env:**
```
GATEWAY_ALLOW_ALL_USERS=true
```

**Alternative (more restrictive):** Add specific user IDs via `DISCORD_ALLOWED_USERS=*` (wildcard works).

### `DISCORD_ALLOW_ALL_USERS=true` (⚠️ Discord-specific — REQUIRED for channel responses)

`GATEWAY_ALLOW_ALL_USERS` is a **fallback** that affects most platforms generically. The Discord platform adapter has its own **platform-specific** env var that the `adapter.py` user-authorization check actually reads:

```
DISCORD_ALLOW_ALL_USERS=true
```

**Why both matter:** Even with `GATEWAY_ALLOW_ALL_USERS=true`, the Discord adapter's user authorization check (in `gateway/platforms/discord/`) can still block messages. The `DISCORD_ALLOW_ALL_USERS` env var bypasses the Discord platform's allowlist explicitly. Setting BOTH is the safest approach:

```yaml
# profile/.env:
GATEWAY_ALLOW_ALL_USERS=true
DISCORD_ALLOW_ALL_USERS=true
DISCORD_AUTO_THREAD=false
```

**Verification that both are active:**
```bash
grep -i "unauthorized\|denied" ~/.hermes/logs/spacebar-*.log
# → should be empty after setting both
```

**When deploying via fleet manager:** Both env vars must be passed to each gateway subprocess in `spacebar-fleet-manager.py`:

```python
env["GATEWAY_ALLOW_ALL_USERS"] = "true"
env["DISCORD_ALLOW_ALL_USERS"] = "true"
```

### `DISCORD_ALLOWED_CHANNELS` (channel whitelist for response)

If set, the bot ONLY responds to messages in these channel IDs. All other channels are silently ignored. Use with `require_mention: false` to make a channel representative:

```yaml
discord:
  require_mention: false
  allowed_channels:
    - <discord-channel-id>   # only responds in #general
```

Combine with channel permission overwrites to implement the "one rep per channel" pattern — each channel has exactly one bot that responds by default, and all others require @mention.

**Format:** List of channel IDs as strings in the config.yaml.
**Not an env var:** `allowed_channels` is config-only, not available as an environment variable override.

### `DISCORD_IGNORED_CHANNELS` (channel blacklist)

Comma-separated list of channel IDs where the bot NEVER responds, even if `require_mention=false`. Useful when a bot can see multiple channels but should only respond in one.

**Set via profile .env:**
```
DISCORD_IGNORED_CHANNELS=<discord-channel-id>,<discord-channel-id>
```

### `DISCORD_REQUIRE_MENTION=true` → `false` (channel behavior control)

Controls whether the bot requires `@BotName` in guild channels before responding.

| Value | Channel behavior | DM behavior |
|-------|-----------------|-------------|
| `true` (default) | Bot only responds when `@BotName` is in the message | Bot responds without @mention (DM check is bypassed in adapter code), BUT see GATEWAY_ALLOW_ALL_USERS above |
| `false` | Bot responds to every message in the channel | Same (already works) |

**Why you'd change it:** When only one bot is in a channel (e.g., `#command` with only Chief of Staff), requiring @mention is unnecessary friction. the operator wants to walk into `#command` and just type.

**Set via profile config.yaml:**
```yaml
discord:
  require_mention: false
```

**OR profile .env:**
```
DISCORD_REQUIRE_MENTION=false
```

**Caveat when false — multi-agent channel cohabitation:** If MULTIPLE bots share a channel AND nobody is @-mentioned, multiple bots may respond. This is the operator's "channel representative" concern. The adapter's multi-agent filtering (line 807-846) works like this:

- If nobody is @-mentioned → falls through to `DISCORD_IGNORE_NO_MENTION` (default: true → IGNORE the message)
- If a different bot is @-mentioned but not this one → ignore (correct routing)
- If multiple bots are @-mentioned → all respond (may be desirable or not)

**To implement the "one rep per channel" pattern:** Assign each channel to a single designated bot. Remove other bots from the channel or set channel-specific `DISCORD_ALLOWED_CHANNELS` / `DISCORD_IGNORED_CHANNELS` per profile. For example, Chief of Staff gets `#command` exclusively — no other bot should be in that channel.

### `DISCORD_FREE_RESPONSE_CHANNELS` (per-channel exemption from mention requirement)

If `require_mention=true` but you want the bot to respond without @mention in specific channels, set:

```
DISCORD_FREE_RESPONSE_CHANNELS=<discord-channel-id>
```

Where the value is a comma-separated list of channel IDs. Use `*` for all channels.

### `DISCORD_IGNORE_NO_MENTION` (multi-agent channel behavior)

Default: `true` — messages without @mention in channels are ignored.

Set to `false` only when `require_mention=false` AND you want the bot to respond to EVERY message, even when no one is @-mentioned. In channels with multiple bots, this means all bots may respond to the same message — so only set `false` for channels with a single designated bot.

### `DISCORD_NO_THREAD_CHANNELS` (per-channel exemption from auto-thread)

Comma-separated list of channel IDs where auto-thread is skipped even when `DISCORD_AUTO_THREAD=true`. Not needed when `DISCORD_AUTO_THREAD=false` globally (as on Spacebar).

### Gateway Start Script Pattern — Use subprocess.Popen, NOT os.execve

For Spacebar-deployed agents, a Python launcher script is preferable to bash (JWT token special chars break shell quoting). Two options:

**Recommended: subprocess.Popen** (process is tracked by Hermes background process management, allows monitoring, output capture, restart):
```python
import subprocess, os
proc = subprocess.Popen(
    [venv_python, gateway_script, profile_name],
    env={**os.environ, **env_overrides},
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
)
# Stream output
for line in iter(proc.stdout.readline, ""):
    print(line, end="")
```

**NOT recommended: os.execve** — replaces the parent process entirely. Hermes background process tracking loses the child because the PID changes. The process appears to "exit" immediately with code 0, making debugging impossible:
```python
# Don't use this — breaks process tracking
os.execve(venv_python, [venv_python, gw, profile], os.environ)
```

Save as `start_gateway.py` in the profile directory for easy restarts.

## Discord Bot Token vs Spacebar JWT Token Format

The most common failure when connecting to Spacebar is:

```
400 Bad Request (error code: 400): Error: Unsupported token algorithm: undefined
```

**Root cause:** The token being used is a Discord bot token (`MT...` format), not a Spacebar JWT (`eyJ...` format). The Hermes default config.yaml contains a real Discord bot token. When discord.py sends this to Spacebar's auth endpoint, Spacebar rejects it because the token algorithm field (present in JWT but absent in Discord tokens) is `undefined`.

**The two connection modes:**

| Aspect | Real Discord | Spacebar |
|--------|-------------|----------|
| Token format | `MT...` (base64 Discord bot token) | `eyJ...` (JWT with `alg`, `payload`, `signature`) |
| API version | v10 (`discord.com/api/v10`) | v9 (`gc.your-domain.example/api/v9` or `localhost:3100/api/v9`) |
| WebSocket URL | `wss://gateway.discord.gg/` | `wss://gc.your-domain.example/` or `ws://localhost:3100/` |
| HTTP base URL | `https://discord.com/api/v10` | `https://gc.your-domain.example/api/v9` |
| Auth mechanism | `Bot <token>` header | `Bot <token>` header (same format, different token type) |

**To connect a Hermes bot to Spacebar, the `spacebar-gateway.py` wrapper must patch discord.py's HTTP base URL BEFORE importing the gateway adapter:**

```python
import discord
discord.http.Route.BASE = "http://localhost:3100/api/v9"   # local dev
# OR
discord.http.Route.BASE = "https://gc.your-domain.example/api/v9"  # production
```

Then supply the Spacebar JWT token (not the Discord bot token) via the standard `DISCORD_BOT_TOKEN` env var or config.yaml token field.

**To reproduce the specific error for debugging:** Set `discord.http.Route.BASE` to Spacebar URL while keeping the default config's Discord bot token — you get `400 Unsupported token algorithm`. Set the Route.BASE back to `https://discord.com/api/v10` — the default Discord token works fine. This confirms token type mismatch, not network or version incompatibility.

Spacebar rate-limits per-IP, and the limit applies **across all endpoints** — not just auth. When you hit this, three things happen simultaneously:

1. **Auth/login fails** — `POST /auth/login` returns `{"message":"You are being rate limited.","retry_after":<seconds>,"global":false}`
2. **Gateway REST calls fail** — The gateway's Discord adapter makes REST calls (like `/users/@me` for login bootstrap), which return HTTP 429
3. **Gateway WebSocket fails** — The gateway can't establish the WebSocket connection. Log shows: `Reconnect discord error: discord connect timed out after 30s, next retry in 60s`

**The gateway self-heals** — It enters a reconnect loop with `60s` retry interval. When the rate window clears (typically 15-20 minutes), the gateway automatically reconnects and continues normally:

```
[Spacebar] INFO Connecting to discord...
[Spacebar] INFO Registered /skill command with 77 skill(s) via autocomplete
[Spacebar] INFO Connected as chief-of-staff#0001
[Spacebar] INFO ✓ discord connected
[Spacebar] INFO Gateway running with 1 platform(s)
```

**Do NOT restart the gateway while rate-limited** — It will just time out again and enter the same reconnect loop. Let the self-healing mechanism work.

**Avoiding rate limits during batch operations:**
- Spacebar's default rate limit is ~5 requests per window
- Each `/auth/login` call consumes one token
- Space between auth calls: at least 1 second apart
- After hitting the limit, wait for `retry_after` seconds (the server returns the exact clearance time)
- For bulk bot creation, use direct SQL inserts (via `create-all-bots-db5.js` pattern) instead of the API
- If you must batch-login multiple bots (to get their user IDs or join them to guilds), do it serially with 2-3 second delays and expect to hit the limit around 5-10 calls

## Central Token File Pattern

All bot tokens and passwords live in a single source-of-truth file:

**Location:** `${MY_REPOS}/Documents/github/agent-fleet/.env.spacebar`

**Naming convention:**
```
export SPACEBAR_BOT_{UPPERCASE_NAME}=<jwt-token>
export SPACEBAR_BOT_{UPPERCASE_NAME}_PASS=<password-for-login-api>
```

**Critical: hyphen-to-underscore normalization.** Bot profile names use hyphens (`chief-of-staff`, `technology-lead`) but the token file uses underscores (`CHIEF_OF_STAFF`, `TECHNOLOGY_LEAD`). When looking up a token by profile name:

```python
def get_bot_token(bot_name):
    norm_name = bot_name.upper().replace("-", "_")
    key = f"SPACEBAR_BOT_{norm_name}"
    return TOKENS.get(key, "")
```

When the profile's `.env.spacebar` gets out of sync with the central file (e.g., after a DB reset that invalidated all tokens), recreate the profile token file from the central source:

```python
prof_dir = Path.home() / "AppData/Local/hermes/profiles" / bot_name
env_sb = prof_dir / ".env.spacebar"
env_sb.write_text(f"""export SPACEBAR_BOT_TOKEN=*** SPACEBAR_GUILD_NAME="the operator"
export SPACEBAR_GATEWAY_URL=wss://discy.your-domain.example/
export SPACEBAR_GUILD_ID=<discord-channel-id>
export SPACEBAR_API_URL=https://discy.your-domain.example/api/v9
""")
```

Then also update the profile's `.env` with the gateway config flags. The utility script at `${USER_HOME}/update_profiles.py` does this for all 40 profiles in one pass.

## Full Config File for Spacebar Chief-of-Staff (Reference)

```yaml
# profile/config.yaml additions:
discord:
  require_mention: false
  auto_thread: false

# profile/.env additions:
GATEWAY_ALLOW_ALL_USERS=true
DISCORD_ALLOWED_USERS=*
DISCORD_AUTO_THREAD=false
DISCORD_REQUIRE_MENTION=false
```

## Verification: Config Applied

Check the gateway log after restart:

```bash
# No thread creation attempts:
grep -i "auto-thread" ~/AppData/Local/hermes/profiles/<name>/logs/gateway.log
# → should be empty (no output = no attempts)

# No unauthorized user blocks:
grep -i "unauthorized" ~/AppData/Local/hermes/profiles/<name>/logs/gateway.log
# → should be empty

# Gateway connected:
grep "discord connected" ~/AppData/Local/hermes/profiles/<name>/logs/gateway.log
# → ✓ discord connected
```
