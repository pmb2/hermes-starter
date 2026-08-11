# New Bot Lifecycle on Spacebar — Full Creation Sequence

When adding NEW Hermes agent profiles to a Spacebar fleet (bots that don't yet exist in the database), the naive approach of "create a Postgres row for the user" misses several critical pieces. Each missing piece causes a different failure mode. This reference documents every required step, in order, with the symptom each step prevents.

## The Full Sequence

```
1. Create user record (users table)
2. Create OAuth2 application (applications table)
3. Set valid_tokens_since in users.data
4. Add guild membership (members table)
5. Generate JWT token (via gen-vps-tokens.js)
6. Inject token into local profile .env and .env.spacebar
7. Start gateway
```

## Step-by-Step

### 1. Create User Record

Insert a row in `users`. The `id` is a Discord-style snowflake (timestamp-based bigint). Use Node.js BigInt:

```javascript
const epoch = 1420070400000n;
const now = BigInt(Date.now()) - epoch;
const id = (now << 22n) | (1n << 17n) | (1n << 12n) | BigInt(seq++);

await client.query(
  `INSERT INTO users (id, username, discriminator, email, desktop, mobile,
     premium, premium_type, bot, bio, system, nsfw_allowed,
     mfa_enabled, created_at, verified, disabled, deleted,
     flags, public_flags, purchased_flags, premium_usage_flags,
     rights, data, fingerprints, webauthn_enabled)
   VALUES ($1, $2, $3, $4, false, false,
     true, 2, true, $5, false, true,
     false, NOW(), true, false, false,
     0, 0, 0, 0,
     $6, $7::jsonb, $8, false)`,
  [id.toString(), username, "0001", username + "@bot.local", "", "0", "{}", "{}"]
);
```

**Required columns:** id, username, discriminator, email, bot=true.  
**Pitfall:** Missing `data` field → valid_tokens_since never set → Step 5's tokens silently rejected.

### 2. Create OAuth2 Application

Without this, the gateway gets `404 Unknown application` on slash command sync and the bot can't register slash commands. The application ID **must be the same as the user ID**:

```javascript
await client.query(
  `INSERT INTO applications (id, owner_id, bot_user_id, name, hook,
     bot_public, bot_require_code_grant, flags, redirect_uris, verify_key)
   VALUES ($1, $2, $3, $4, true, true, false, 0, $5, $6)`,
  [userId, userId, userId, username, "{}", ""]
);
```

**Required columns:** id (same as user ID), owner_id (same), bot_user_id (same), name, hook=true, bot_public=true, bot_require_code_grant=false, flags=0, redirect_uris={}::text[], verify_key=''.

### 3. Set `valid_tokens_since` in `users.data`

This is the most commonly missed step. Spacebar checks every incoming token against `users.data -> 'valid_tokens_since'`. Tokens generated **before** this timestamp are rejected. If `data` is `{}` (no `valid_tokens_since`), behavior is undefined — tokens may work for REST but fail for WebSocket, or vice versa.

```javascript
const validSince = new Date().toISOString();
await client.query(
  "UPDATE users SET data = $1::jsonb WHERE id = $2",
  [JSON.stringify({ valid_tokens_since: validSince }), userId]
);
```

**Symptom if missed:** Token authenticates fine via REST (`GET /users/@me` returns 200) but the gateway's WebSocket IDENTIFY never completes — Spacebar's session handler silently rejects the token. The bot never shows as online. **The gateway_state.json reports "discord=connected" (WebSocket is open at transport layer) but the bot has no guild data, never receives messages, and the WebSocket IDENTIFY payload is silently discarded.**

### 4. Add Guild Membership

Without this, the bot connects to the gateway but doesn't appear on any guild. Insert into `members`:

```javascript
const maxIdx = await client.query(
  "SELECT COALESCE(MAX(index), 0) + 1 as next_idx FROM members WHERE guild_id = $1",
  [guildId]
);

await client.query(
  `INSERT INTO members (index, id, guild_id, joined_at, deaf, mute, pending, settings, bio, flags)
   VALUES ($1, $2, $3, NOW(), false, false, false, $4::jsonb, $5, $6)`,
  [maxIdx.rows[0].next_idx, userId, guildId, "{}", "", 0]
);
```

**Required columns:** index (sequential per guild), id (user ID, used as PK), guild_id, joined_at, deaf, mute, pending, settings={}::jsonb, bio='', flags=0.

**⚠️ `members.id` = user.id**. The members table uses the user's snowflake ID as its primary key. There is no separate `user_id` column.

### 5. Generate JWT Token

Use the existing batch script on the VPS:

```bash
cd /opt/spacebar
node gen-vps-tokens.js
```

This reads ALL bot users from the DB, creates a session row per user, signs an ES512 JWT with the instance's private key, and writes `vps-bot-tokens.env`. Always regenerate ALL tokens after adding new bots — the script rebuilds the entire file.

### 6. Inject Token into Local Profile

The `vps-bot-tokens.env` file uses the format `SPACEBAR_BOT_<NAME>=<jwt>` where `<NAME>` is the username in UPPERCASE with hyphens → underscores. Map to local profile `.env`:

```
DISCORD_BOT_TOKEN=<jwt>
```

And `.env.spacebar`:

```
export SPACEBAR_BOT_TOKEN=<jwt>
export SPACEBAR_GATEWAY_URL=wss://gc.your-domain.example/
export SPACEBAR_GUILD_ID=<discord-channel-id>
export SPACEBAR_API_URL=https://gc.your-domain.example/api/v9
```

### 7. Start Gateway

```bash
cd /path/to/agent-fleet/scripts
python fleet-manager.py deploy
```

## ⚠️ Critical Pitfall: Parallel Subagents Overwrite .env Files

**DO NOT use parallel subagents** (`delegate_task`) to build out Hermes profiles by reading, modifying, and writing `.env` files. Subagents will overwrite the `.env` with a single common token, rendering ALL bots identical on Spacebar.

**Why it happens:** Each subagent reads a profile's `.env`, sees the current token, then writes its own "authoritative" version. Since all subagents use the same baseline (either the original token or whatever they first read), every `.env` winds up with an identical token. The first write wins, the rest confirm they already match.

**Symptoms after:**
- Every bot shows the same username in the gateway log (`Connected as <first-bot>#0001`)
- Only one bot's token is actually in the DB session table
- All other bots silently fail IDENTIFY with `Invalid Token`

**Fix once corrupted:**
1. Re-create bot users in the DB that don't exist (steps 1-4 above, for any that weren't fully registered)
2. Regenerate ALL tokens: `node /opt/spacebar/gen-vps-tokens.js`
3. Re-download: `scp` the `vps-bot-tokens.env` file to the local machine
4. Re-inject into every profile's `.env` and `.env.spacebar` (one-pass script, NOT subagents)
5. Restart the fleet

### Safer Profile Build-Out Workflow

1. **Build profiles in parallel** using subagents for `AGENTS.md`, `SOUL.md`, and `config.yaml` only
2. **NEVER include `.env` or `.env.spacebar`** in the subagent's task description
3. **After subagents finish**, run a single non-subagent script to inject the correct unique tokens from `vps-bot-tokens.env` into all profiles
4. Verify uniqueness by checking the **middle portion** of each JWT (NOT the first 20 chars — see below)

## Verification: Token Uniqueness

**JWT first-20-chars comparison gives false positives.** All JWTs start with the same base64-encoded header (`eyJhbGciOiJIUzI1...`). To check uniqueness, compare a middle slice (characters 40-70):

```python
seen = {}
for name, token in token_map.items():
    mid = token[40:70]
    if mid in seen:
        print(f"DUPE: {name} == {seen[mid]}")
    else:
        seen[mid] = name
```

A true duplicate means the `gen-vps-tokens.js` script was run before the new bot user was registered in the DB, or the script doesn't pick up the new user yet.

## Sequence Diagram

```
                    VPS PostgreSQL                     Local Machine
                    ─────────────                     ────────────
  1. INSERT INTO users ──────────────────────────┐
  2. INSERT INTO applications                    │
  3. UPDATE users SET data = ...                 │
  4. INSERT INTO members                         │
  5. node gen-vps-tokens.js                      │
       └── creates session rows                  │
       └── signs JWT for each user               │
  6. cat vps-bot-tokens.env ──scp────────────►   │
                                                 ▼
                                            inject-tokens.py
                                                 │
                                    ┌────────────┼────────────┐
                                    ▼            ▼            ▼
                              profile/.env  profile/.env  profile/.env
                              token=JWT-A   token=JWT-B   token=JWT-C
```

## One-Shot Injection Script Pattern

Keep a reusable script at `~/AppData/Local/hermes/scripts/inject-tokens.py`:

```python
import os, re

TOKEN_FILE = '${USER_HOME}/vps-tokens.env'
PROFILES_DIR = os.path.expanduser('~/AppData/Local/hermes/profiles')

with open(TOKEN_FILE) as f:
    content = f.read()

token_map = {}
for line in content.strip().split('\n'):
    if '=' in line and not line.startswith('#'):
        var, token = line.split('=', 1)
        var = var.strip()
        if var.startswith('SPACEBAR_BOT_'):
            name = var.replace('SPACEBAR_BOT_', '').lower().replace('_', '-')
            token_map[name] = token.strip()

for name, token in token_map.items():
    for fname in ('.env', '.env.spacebar'):
        fpath = os.path.join(PROFILES_DIR, name, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, 'r') as f:
            content = f.read()
        content = re.sub(
            r'^(DISCORD_BOT_TOKEN|export SPACEBAR_BOT_TOKEN)=.*',
            r'\1=' + token,
            content,
            flags=re.MULTILINE
        )
        with open(fpath, 'w') as f:
            f.write(content)
```

This script is safe to run repeatedly — it only updates the token lines and leaves everything else intact.
