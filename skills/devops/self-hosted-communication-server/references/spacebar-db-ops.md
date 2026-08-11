# Spacebar DB Operations — Bot Creation, Rate Limit Recovery, Guild Setup

## Direct DB User Creation (When API Registration Fails)

When the Spacebar API registration is rate-limited or registration endpoint has issues, create users directly via PostgreSQL.

### Required: Snowflake ID Generator

Spacebar uses Discord-style snowflake IDs. Use a manual generator for direct DB inserts:

```javascript
let seq = 0;
function genId() {
  const epoch = 1420070400000n;  // Discord epoch
  const now = BigInt(Date.now()) - epoch;
  seq = (seq + 1) % 4096;       // Sequence within same millisecond
  return (now << 22n) | (1n << 17n) | (1n << 12n) | BigInt(seq);
}
```

### Required: ALL NOT NULL Columns

When inserting directly, every NOT NULL column must be provided. Missing columns fail one-at-a-time. Use this complete INSERT:

```sql
INSERT INTO users (
  id, username, discriminator, email, desktop, mobile,
  premium, premium_type, bot, bio, system, nsfw_allowed,
  mfa_enabled, created_at, verified, disabled, deleted,
  flags, public_flags, purchased_flags, premium_usage_flags,
  rights, data, fingerprints, webauthn_enabled, "settingsIndex"
) VALUES (
  $1, $2, '0001', $3, false, false,
  true, 2, $4, '', false, true,
  false, NOW(), true, false, false,
  0, 0, 0, 0,
  $5, $6::jsonb, '{}', false, 1
);
```

Parameter order: `[id, username, email, isBot, rights, data]`

Where:
- `rights` = `BigInt("875069521787904")` (standard user rights)
- `data` = `JSON.stringify({ hash: bcryptHash, valid_tokens_since: isoDate })`
- `discriminator` = `'0001'` for all bots (Spacebar default)
- `isBot` = `true` for bots, `false` for human accounts

### Run from Spacebar Project Directory

```bash
cd /opt/spacebar
NODE_PATH=./node_modules node -r dotenv/config your-script.js
```

The `-r dotenv/config` loads `DATABASE` from `.env`. The `NODE_PATH=./node_modules` finds `pg`, `bcrypt`, etc.

### After DB Insert — Get Auth Token

Even after inserting directly into DB, you still need to login via API to get a JWT token:

```bash
# Login to get token
curl -X POST http://localhost:3100/api/v9/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"bot-name","password":"PulseBot2026!"}'
```

The password is bcrypt-hashed in the `data` field — use the same password you passed to `bcrypt.hash()`.

## Rate Limit Recovery

Spacebar has two rate limit systems:
1. **`limits.rate`** — Main rate limiter (requests/time window per route)
2. **`limits.absoluteRate.register`** — 25 registrations per hour (separate counter)

### Prevent: Set Config Properly

In `config.production.json` or config in DB:
```json
{
  "limits": {
    "rate": { "enabled": false },
    "absoluteRate": { "register": { "enabled": false } }
  }
}
```

**🚨 Pitfall:** If `CONFIG_PATH` is not set, Spacebar reads config from the **database**, not from `config.json`. Set `export CONFIG_PATH="config.json"` to force file-based config.

### Recovery: Restart the Process

When already rate-limited (returns 429 with `retry_after` in seconds), restarting clears in-memory counters:

```bash
# Find and kill the sb-bundle process
kill $(pgrep -f "sb-bundle-3100")

# Systemd auto-restarts it. Verify:
sleep 10
curl -s http://localhost:3100/api/v9/gateway  # Should return JSON
curl -s -X POST http://localhost:3100/api/v9/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"admin","password":"pass"}'  # Should return token
```

### API Call Spacing

Once rate-limited, the `retry_after` can be very long (up to ~2400s = 40min). After recovery:

- Space API calls **500ms-1s apart** to avoid re-triggering
- This is especially critical for: guild creation, channel creation, member addition, and bot token generation
- For 40+ bulk operations, the loop takes 40-80 seconds total — well worth the spacing

### After Process Restart — Tokens Invalidate

When Spacebar restarts, a new JWT key pair is generated (if keys aren't persisted). All existing JWT tokens are invalidated. After restart:

1. **Login as admin** to get a fresh admin token
2. **Regenerate all bot tokens** by logging in as each bot
3. Update the `.env.spacebar` file with new tokens

```javascript
// Login and save token
const login = await fetch("POST", "/auth/login", {
  login: username, password: password
});
const token = login.token;
fs.appendFileSync("/home/ubuntu/.env.spacebar",
  `export SPACEBAR_BOT_${NAME}=${token}\n`);
```

## Guild Setup from Clean DB

After a DB reset (all users + guilds gone):

### Step 1: Create Admin Account + All Bots in DB

Use the direct DB INSERT pattern above. Create users in this order:
1. `backus-admin` (admin, `bot: false`)
2. All 39 bot accounts (bot: `true`)

### Step 2: Login as Admin → Create Guild

```javascript
const guild = await api("POST", "/guilds", { name: "Guild Name" });
// No "description" field — Spacebar rejects it with 50035
```

### Step 3: Create Channel Categories

```javascript
const category = await api("POST", `/guilds/${gid}/channels`, { name: "Category Name", type: 4 });
// type: 4 = GuildCategory
```

### Step 4: Create Text Channels Under Categories

```javascript
const channel = await api("POST", `/guilds/${gid}/channels`, {
  name: "channel-name", type: 0,  // type: 0 = GuildText
  parent_id: categoryId
});
```

### Step 5: Join Bots to Guild

Each bot must join using its own auth token:

```javascript
// For each bot:
const botLogin = await api("POST", "/auth/login", {
  login: botName, password: botPassword
});
const botToken = botLogin.token;
await api("PUT", `/guilds/${guildId}/members/@me`, {}, botToken);
```

⚠️ **Admin cannot add bots** via `PUT /guilds/{id}/members/{user_id}` — that endpoint requires OAuth2. Bots must self-join.

## Token File Management

The `.env.spacebar` file structure:
```bash
export SPACEBAR_API_URL=http://localhost:3100/api/v9
export SPACEBAR_GUILD_ID=<guild-id>
export SPACEBAR_ADMIN_TOKEN=<admin-jwt>
export SPACEBAR_BOT_VIGIL=<bot-jwt>
export SPACEBAR_BOT_CHRONICLE=<bot-jwt>
# ... one per bot
```

Token variable naming: `SPACEBAR_BOT_<NAME>` where `NAME` is uppercase with hyphens→underscores:
- `chief-of-staff` → `SPACEBAR_BOT_CHIEF_OF_STAFF`
- `scout` → `SPACEBAR_BOT_PAUL_SCOUT`

## Duplicate User Cleanup

After multiple registration runs (bot account creation via API or DB), users table accumulates duplicate usernames. Each "duplicate" is a separate Spacebar user record with the same username but different ID — created by separate registration calls.

### Detect Duplicates

```sql
SELECT username, count(*) as cnt, 
  string_agg(id::text, ', ') as ids
FROM users 
WHERE username IN (
  SELECT username FROM users GROUP BY username HAVING count(*) > 1
)
GROUP BY username ORDER BY cnt DESC;
```

### Safe Cleanup Strategy

Only users with zero messages are safe to delete. The profile-linked user (the one whose ID matches a profile's `DISCORD_BOT_TOKEN`) should be kept.

1. Build a KEEP list of user IDs (the ones with valid profile tokens)
2. Delete from members table for non-keep users in the guild
3. Delete non-keep users with 0 messages

```sql
-- 1. Delete stale member records
DELETE FROM members 
WHERE id NOT IN (<keep_ids_csv>) 
AND guild_id = '<guild_id>';

-- 2. Delete non-keep users with no messages
DELETE FROM users 
WHERE id NOT IN (<keep_ids_csv>) 
AND NOT EXISTS (
  SELECT 1 FROM messages m WHERE m.author_id = users.id
);
```

### After Cleanup — Sync member_count

Spacebar's `member_count` in the guilds table is NOT updated automatically when members are removed via DB. It only counts members that joined via the API. After any DB-level member cleanup:

```sql
UPDATE guilds SET member_count = (
  SELECT count(*) FROM members WHERE guild_id = '<guild_id>'
) WHERE id = '<guild_id>';
```

Verify via API: `GET /api/v9/guilds/<guild_id>` should show the correct count.

## Node.js Script Template for VPS Operations

```javascript
const { Pool } = require("pg");
const http = require("http");

const API = "http://localhost:3100/api/v9";
const pool = new Pool({ connectionString: process.env.DATABASE });

function api(method, path, data, token) {
  return new Promise((resolve, reject) => {
    const u = new URL(API + path);
    const opts = { hostname: u.hostname, port: u.port, path: u.pathname, method,
      headers: { "Content-Type": "application/json" } };
    if (token) opts.headers["Authorization"] = token;
    const req = http.request(opts, (res) => {
      let d = "";
      res.on("data", c => d += c);
      res.on("end", () => { try { resolve(JSON.parse(d)); } catch { resolve({ raw: d }); } });
    });
    req.on("error", reject);
    if (data) req.write(JSON.stringify(data));
    req.end();
  });
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
```

Run from Spacebar project directory:
```bash
cd /opt/spacebar && NODE_PATH=./node_modules node -r dotenv/config your-script.js
```
