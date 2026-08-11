Fermi Web Client Setup
`src/api/routes/auth/login.ts` line 69 — add `{ username: login }` to the `where` array:
```ts
where: [{ phone: login }, { email: login }, { username: login }],
```

> **🔗 Fleet Launch QA** — Before launching any gateway fleet, verify every profile's token against the Spacebar API. See `references/profile-token-verification.md` for the complete verification pattern, including token refresh and stale state cleanup.

### Bulk Bot Registration

For registering many bot users (10+) on a fresh Spacebar instance:

1. **Disable BOTH rate limiters** in config.json:
   - `limits.rate.enabled: false` (main rate limiter)
   - `limits.absoluteRate.register.enabled: false` (separate absolute rate — 25/hr default)
   - Increase `limits.rate.auth.register.count` to 100+ as safety net
2. Restart the server to pick up config changes
3. Register bots as **regular users** — Spacebar's JSON schema rejects `"bot": true`:
   ```bash
   # Correct — no bot flag
   curl -X POST http://localhost:3001/api/v9/auth/register \
     -H "Content-Type: application/json" \
     -d '{"username":"agent-name","password":"pass","consent":true}'
   ```
4. Use a **1-second delay** between registrations to avoid race conditions
5. After registering, login to get each token (or capture from registration response)

**When the API is unavailable or rate-limited:** use direct DB insertion via PostgreSQL. See `references/spacebar-db-ops.md` for the complete pattern: Snowflake ID generation, all required NOT NULL columns, bcrypt hashing, and guild setup from a clean database. This is also the recovery path when the JWT key rotates on restart and all tokens are invalidated.

**Rate limit recovery:** If you're already rate-limited (429 errors), restarting the Spacebar process clears the in-memory counters. See `references/spacebar-db-ops.md` for the exact kill/restart/verify sequence.

### Full-Fleet Launch Script

`scripts/launch-spacebar-fleet.py` — Scans ALL Hermes profiles, discovers bot tokens (from `.env` or `.env.spacebar`), creates `.env.spacebar` for profiles that only have tokens in `.env`, and starts each bot's gateway silently with `CREATE_NO_WINDOW`. Uses Windows-safe PID checking via `ctypes.windll.kernel32.OpenProcess` to detect already-running bots. Handles 40+ profiles in ~15 seconds.

Run:
```bash
python /path/to/skills/self-hosted-communication-server/scripts/launch-spacebar-fleet.py
```

### Fleet Management — Tiered Bot Deployments

For resource-constrained machines running 30+ bots:

**Updated implementation:** See `scripts/manage-fleet.py` — a Python fleet manager that kills all specialist bots and starts only the Core Council (9 bots), with on-demand team activation via `python manage-fleet.py activate <team>` and deactivation via `python manage-fleet.py deactivate <team>`. Team-to-council-lead ownership mappings are built into the script.

**Clean-env startup template:** See `scripts/start-fleet.py` in this skill's directory — a reusable Python script that starts bot gateways with a clean environment dict, avoiding stale env-var inheritance. Requires `.env.spacebar.local` with token exports and `SPACEBAR_API_BASE=http://localhost:3100/api/v9`.

### Tiered Architecture

- **Core bots** (Executive Council, ~9 bots): Always running. Handle user requests.
- **Team bots** (~30 bots across 5 teams): Started on-demand via command-file IPC.

```
fleet-core.py (single supervisory process)
├── 9 core subprocesses (always-on, monitored)
├── Command-file listener (~/.hermes/fleet-commands.json)
│   → Exec council writes {action: "start_team", team: "specialists"}
│   → Fleet-core picks it up within 15s, launches team bots
└── Watchdog monitors ALL subprocesses (core + teams)
```

| Team | Bots | When to Start |
|------|------|---------------|
| specialists | 8 (manufacturing-lead, ai-agency, ...) | MES/Solumina work |
| pulse | 4 (security-lead, history-lead, automation-lead, creative-lead) | Monitoring needed |
| hermes-dev | 5 (dev-lead, skills-lead, ...) | Coding tasks |
| trading | 8 (data-lead, assistant, ...) | Market analysis |
| social-media | 5 (nova, writing-lead, ...) | Content publishing |

### Fleet State Verification After Launch

After starting gateways, verify each one connected to Spacebar successfully. The gateway writes a `gateway_state.json` file in each profile's directory:

```bash
cd ~/AppData/Local/hermes/profiles
for p in <profile1> <profile2> <profile3>; do
  sf="$p/gateway_state.json"
  if [ -f "$sf" ]; then
    state=$(grep -o '"gateway_state":"[^"]*"' "$sf" | cut -d'"' -f4)
    discord=$(grep -o '"discord":{"state":"[^"]*"' "$sf" | cut -d'"' -f6)
    pid=$(grep -o '"pid":[0-9]*' "$sf" | cut -d: -f2)
    echo "$p: state=$state discord=$discord pid=$pid"
  else
    echo "$p: NO STATE (still initializing)"
  fi
done
```

**Expected healthy output:** Each profile shows `state=running discord=connected pid=<number>`.

**Troubleshooting missing state files:**
- Gateways take 30-60 seconds to initialize plugins before connecting. Wait 60s and re-check.
- Check if the process is still running: `ps aux | grep spacebar-gateway`
- The first `import discord` is slow (~10-15s on cold start) — this is normal, not a hang.
- If the gateway process exited, check its log file: `~/.hermes/logs/<profile>-gateway.log` or the full output from the terminal session that launched it.
- Common cause: the JWT token in the profile's `.env` expired after a Spacebar restart. Generate a fresh one by logging in via the Spacebar API and update the `.env`.

### Tiered Deployment Script

See `scripts/deploy-spacebar-bots.py` for a minimal Python-only deploy (register → join → token propagation).

The `.bat` reference file for Windows: `references/fleet-deploy-windows.md`.

### Gateway Lock File Contention (Windows)

When a gateway process is killed without clean shutdown (`taskkill /F`), `.lock` files persist. Fix:

```bash
# 1. Find orphaned Python processes holding the lock
/c/Windows/System32/tasklist.exe //FI "IMAGENAME eq python.exe" //FO CSV //NH

# 2. Kill by specific PID
/c/Windows/System32/taskkill.exe //F //PID <pid>

# 3. Prevention: stop gateways via `hermes -p <name> gateway stop` (clean drain)
```

### .env File Pitfall for Subprocess Inheritance

The `set -a` auto-export trick must be used when sourcing profile `.env` files, because without `export` the variables are bash-only and invisible to Python:

```bash
set -a
source ~/.hermes/profiles/dev-lead/.env
set +a
python scripts/spacebar-gateway.py dev-lead
```

On Windows batch files, `set VAR=value` in CMD always writes to the environment block — use that directly instead of bash `export`.

### 🚨 `.env.spacebar` Precedence Trap

The `spacebar-gateway.py` wrapper reads tokens in this order:

1. **Environment variable** `SPACEBAR_BOT_TOKEN` (highest priority)
2. **Environment variable** `DISCORD_BOT_TOKEN`
3. **File `.env`** in the profile directory (scans for `DISCORD_BOT_TOKEN=` or `export SPACEBAR_BOT_TOKEN=`)
4. **File `.env.spacebar`** in the profile directory (lowest priority, same scan logic)

**The trap:** If you previously ran `set -a; source profile/.env; set +a` to start a gateway (which exports `DISCORD_BOT_TOKEN` into the environment), that variable persists in the terminal shell. Subsequent gateway starts — even from a different working directory — inherit this stale env var, which wins over whatever is in `.env` on disk.

Additionally, an old `.env.spacebar` file in the profile directory may contain `export SPACEBAR_BOT_TOKEN=OLD_TOKEN`. The wrapper's env-var check (step 1) catches this if a prior command sourced it, or the file-read fallback (step 4) picks it up if steps 1-3 all miss.

**Symptom:** Gateway log shows `login id=15104207...` (old user ID) even though the `.env` file was updated with a new token.

**Diagnosis:**
```bash
# Check what token the gateway wrapper is actually finding
grep "login id" scripts/logs/<profile>-gateway.log | tail -1

# Check for stale .env.spacebar in profile
ls -la ~/AppData/Local/hermes/profiles/<profile>/.env.spacebar

# Check for global env bleed
echo "DISCORD_BOT_TOKEN=[${DISCORD_BOT_TOKEN:0:30}]..."
```

**Fix A — Remove stale .env.spacebar files from ALL profiles:**
```bash
find ~/AppData/Local/hermes/profiles -name ".env.spacebar" -delete
```

**Fix B — Start gateways with a clean environment (recommended):**
Instead of relying on `set -a; source`, use a Python launch script that builds a fresh env dict with only the needed variables:

```python
import subprocess, os

env = {}
# Copy only essential system vars from parent
for k in ("PATH", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "SYSTEMROOT", "COMSPEC", "HERMES_HOME_BASE"):
    if k in os.environ:
        env[k] = os.environ[k]
# Set gateway-specific vars
env["DISCORD_BOT_TOKEN"] = "<fresh-token>"
env["SPACEBAR_API_BASE"] = "http://localhost:3100/api/v9"
env["SPACEBAR_WS_URL"] = "ws://localhost:3100/"
env["HERMES_GATEWAY_BUSY_ACK_ENABLED"] = "false"

proc = subprocess.Popen(
    ["python", "scripts/spacebar-gateway.py", profile],
    stdout=open(log_file, "a"), stderr=subprocess.STDOUT,
    cwd=project_dir, env=env,
    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
)
```

This approach ensures no stale env vars bleed in. The gateway wrapper's file-fallback reads `.env` directly from disk. Downside: must update token in two places (script + .env) when rotating.

**Fix C — Unset stale vars before each start (bash workaround):**
```bash
unset DISCORD_BOT_TOKEN
unset SPACEBAR_BOT_TOKEN
unset SPACEBAR_GATEWAY_URL
unset SPACEBAR_API_URL
set -a
source ~/AppData/Local/hermes/profiles/<profile>/.env
set +a
python scripts/spacebar-gateway.py <profile>
```

### Direct DB Bot Registration (Bulk / Rate-Limit Bypass)

When the API rate-limits are aggressive or unavailable, insert bots directly into PostgreSQL:

```javascript
const { Pool } = require("pg");
const bcrypt = require("bcrypt");
// Snowflake ID generator + bcrypt hash + INSERT into users table
// See references/spacebar-db-ops.md for full column list
```

**🚨 BCrypt hash generation pitfall:** Python's `bcrypt` library generates
hashes that Node.js `bcrypt.compare()` may fail to verify, even though
Python `bcrypt.checkpw()` confirms they're correct. Always use **Node.js**
to generate hashes for Spacebar passwords. See `references/bcrypt-hash-pitfall.md`.

**Key columns in Spacebar's `users` table:** id, username, discriminator, desktop, mobile, premium, premium_type, bot, bio, system, nsfw_allowed, mfa_enabled, created_at, verified, disabled, deleted, flags, public_flags, purchased_flags, premium_usage_flags, rights, data, fingerprints

For `members` table: id, guild_id, joined_at, deaf, mute, pending, settings, bio, flags.

### Discord CAPTCHA Workflow

Creating apps on Discord's developer portal always triggers hCaptcha. See `references/discord-app-captcha-workflow.md` for browser automation and CapSolver integration patterns.

### Guild &amp; Channel Setup

&gt; **🔗 VPS Deployment QA** — When deploying to a public domain via VPS reverse proxy, run the full 7-layer QA checklist in `references/vps-deployment-qa.md` before marking complete. Covers: DNS, TLS, Caddy, Spacebar internal API, WebSocket, Fermi client, and guild data verification.

> **🔗 Migration from Discord** — For the full end-to-end workflow of migrating a Discord server (channels, categories, members, bots) to Spacebar, see `references/discord-to-spacebar-migration.md`. Covers audit, server fix, Fermi config, guild consolidation, channel recreation, and verification.
>
> **🚨 Thread discovery blind spot:** The `channels/{id}/threads/archived/public` and `private` endpoints only find ARCHIVED threads. Discord also has a **guild-level active threads endpoint** (`guilds/{id}/threads/active`) that returns ALL currently-active threads regardless of parent channel. In one real migration, switching from per-channel archived search to the guild-level active endpoint discovered **31 additional threads** with 10,000+ messages that the per-channel archived-only approach completely missed. Always check BOTH the guild-level active endpoint AND per-channel archived endpoints with pagination.
&gt;
&gt; **🔗 Migration Philosophy** — Phase 10 in the migration reference covers the &quot;best of both&quot; design principle (preserve Discord channel names, redesign categories to improve over both the original and a plain mirror) and the operator&#39;s standards for completeness. Apply these when planning any Spacebar guild layout.

### 🚨 Duplicate User Cleanup — Remove Stale Registration Copies

After many automated registration runs, the `users` table accumulates duplicate copies of the same username. These duplicates have 0 messages but cause confusion and bloat.

**Identify duplicates:**
```sql
SELECT username, count(*) as cnt,
  string_agg(id::text, ', ') as ids
FROM users
WHERE username IN (
  SELECT username FROM users GROUP BY username HAVING count(*) > 1
)
GROUP BY username ORDER BY cnt DESC;
```

**Safe cleanup strategy — keep profile-linked users, delete the rest:**
1. Build a KEEP list of user IDs that correspond to active Hermes profile tokens (validate each profile's `DISCORD_BOT_TOKEN` against `GET /api/v9/users/@me` to confirm the user ID)
2. Only delete users with 0 messages (`NOT EXISTS (SELECT 1 FROM messages WHERE author_id = users.id)`)
3. Delete stale member records first, then users:

```sql
-- Remove stale member records for non-keep users
DELETE FROM members WHERE id NOT IN (<keep_ids>) AND guild_id='<guild_id>';

-- Delete non-keep users that authored no messages
DELETE FROM users WHERE id NOT IN (<keep_ids>)
  AND NOT EXISTS (SELECT 1 FROM messages m WHERE m.author_id = users.id);
```

**Verification:** Confirm no duplicates remain and member count is accurate:
```sql
SELECT username, count(*) as cnt FROM users
GROUP BY username HAVING count(*) > 1;

UPDATE guilds SET member_count = (SELECT count(*) FROM members WHERE guild_id = guilds.id);
```

See `references/spacebar-db-ops.md` for the `users` table schema (all NOT NULL columns required for INSERT).

### 🚨 Post-Import DB Cleanup — `last_message_id` and `member_count`

After importing messages directly into PostgreSQL (bypassing the Spacebar API), the `channels` table still has `last_message_id = NULL` and the `guilds` table `member_count` is wrong. Fermi clients rely on `last_message_id` to know there are messages to load and scroll to.

**Fix both in one pass:**

```sql
UPDATE channels c SET last_message_id = (
    SELECT m.id::text FROM messages m
    WHERE m.channel_id = c.id
    ORDER BY m.id DESC LIMIT 1
) WHERE EXISTS (
    SELECT 1 FROM messages m WHERE m.channel_id = c.id
);

UPDATE guilds SET member_count = (
    SELECT count(*) FROM members WHERE guild_id = guilds.id
);
```

**Verification:**
```sql
SELECT c.name, c.last_message_id FROM channels c
WHERE c.guild_id='<guild_id>' AND c.type=0 AND c.last_message_id IS NOT NULL
ORDER BY c.name;
```

The `guilds.member_count` field is a cached counter Spacebar maintains. Direct DB inserts of members don't increment it — the UPDATE above syncs it. Without this, the API returns `member_count: 1` even when 100+ members exist.

### 🚨 Messages Imported But Not Displaying — `reactions` Must Be Array

> **📄 Detailed reference:** See `references/message-import.md` for the complete
> import SQL template, field-by-field requirements, author mapping strategy, and
> duplicate prevention pattern.

> **📄 Bulk migration workflow:** See `references/bulk-message-migration.md` for
> the end-to-end pipeline: thread audit (guild-level active + per-channel archived),
> full export, delta export, author resolution, bulk import with `ON CONFLICT DO NOTHING`,
> and post-import cleanup.

When importing messages from Discord into Spacebar's `messages` table, the
`reactions` column must be a JSON **array** `'[]'::jsonb`, not a JSON **object**
`'{}'::jsonb`. Spacebar's message serialization iterates over reactions with
`.forEach()`:

```javascript
// Spacebar compiled code (message serialization)
const reactionData = (x.reactions || []).forEach(...)
```

Passing `{}` causes a 500 error:

```json
{"code": 500, "message": "TypeError: (x.reactions || []).forEach is not a function"}
```

**Fix — Update after import:**
```sql
UPDATE messages SET reactions = '[]'::jsonb
WHERE reactions = '{}'::jsonb;
```

Or fix the import SQL to use `'[]'::jsonb` from the start:
```sql
INSERT INTO messages (..., embeds, reactions, ...)
VALUES (..., '[]'::jsonb, '[]'::jsonb, ...)
```

**Other NOT NULL columns that trip up imports:** `embeds` (`'[]'::jsonb`),
`message_snapshots` (`'[]'::jsonb`), `type` (0), `flags` (0).

### 🚨 Thread Import — Foreign Key Workaround for Discord Author IDs

When importing thread messages exported from Discord, the `author_id` column references the `users` table via a foreign key. Discord users who are not registered on Spacebar will cause `violates foreign key constraint` errors.

**Fix — Create minimal placeholder users for each unique Discord author:**

```sql
INSERT INTO users (
  id, username, discriminator, bot, verified, disabled, deleted,
  created_at, flags, public_flags, purchased_flags, premium_usage_flags,
  rights, data, fingerprints, desktop, mobile, premium, premium_type,
  bio, system, nsfw_allowed, mfa_enabled, webauthn_enabled
)
SELECT
  <discord_author_id>, '<username>', '0000', true, false, false, false,
  now(), 0, 0, 0, 0,
  0, '{}'::jsonb, '{}', false, false, false, 0,
  '', false, false, false, false
WHERE NOT EXISTS (SELECT 1 FROM users WHERE id = <discord_author_id>);
```

**Determine which authors are needed:** Load the export JSON, collect unique `author.id` values, check each against the Spacebar `users` table, and create INSERTs for any that don't exist.

**INSERT template (minimal columns for psycopg2):**

```python
INS = """INSERT INTO messages
(id, channel_id, guild_id, author_id, content, timestamp, embeds, reactions, type, flags, mention_everyone, tts, message_snapshots)
VALUES (%s::bigint, %s::bigint, %s::bigint, %s::bigint, %s, %s, '[]'::jsonb, '[]'::jsonb, 0, 0, false, false, '[]'::jsonb)
ON CONFLICT (id) DO NOTHING"""
```

**Important:** The Spacebar `messages` table does NOT have `mentions`, `mention_roles`, or `attachments` columns. Store those inside `embeds` as JSON if needed. Required NOT NULL columns: `embeds` (`'[]'::jsonb`), `reactions` (`'[]'::jsonb`), `message_snapshots` (`'[]'::jsonb`), `type` (0), `flags` (0).

### 🚨 @everyone Permissions: WebSocket Drop Loop After Login

```bash
# Create guild
curl -X POST http://localhost:3001/api/v9/guilds -H "Content-Type: application/json" -H "Authorization: <token>" -d '{"name":"My Guild"}'

# Create category (type=4) first
CAT_ID=$(curl -s -X POST "http://localhost:3001/api/v9/guilds/$GUILD_ID/channels" -H "Content-Type: application/json" -H "Authorization: $TOKEN" -d '{"name":"Category","type":4}' | jq -r '.id')

# Create text channel (type=0) under category with parent_id
curl -X POST "http://localhost:3001/api/v9/guilds/$GUILD_ID/channels" -H "Content-Type: application/json" -H "Authorization: $TOKEN" -d "{\"name\":\"chat\",\"type\":0,\"parent_id\":\"$CAT_ID\"}"
```

### 🚨 @everyone Permissions: WebSocket Drop Loop After Login

When creating a new guild, Spacebar's default `@everyone` role permissions value
(`2251804225`) is **missing** `VIEW_CHANNEL` (1024), `READ_MESSAGE_HISTORY`
(65536), and several other basic permissions. The Fermi (or any Discord) client:

1. Logs in and connects via WebSocket (OP 10 Hello → OP 2 Identify → OP 0 READY ✅)
2. Gets the guild data (READY_SUPPLEMENTAL) and renders the dashboard briefly
3. Sends **OP 14 (Lazy Request)** to load channel data for the sidebar
4. Spacebar rejects with `Op 14 HTTPError: You are missing the following permissions VIEW_CHANNEL`
5. WebSocket closes with code **4000**
6. Client reconnects → goes back to step 1 → **infinite retry loop**

The user sees the dashboard flash for a second, then "Unable to connect to the
server, retrying in 9 seconds..." — repeating forever.

**Fix — Add VIEW_CHANNEL and other base permissions to @everyone:**

```sql
-- Grant VIEW_CHANNEL (1024), SEND_MESSAGES (2048), EMBED_LINKS (16384),
-- ATTACH_FILES (32768), READ_MESSAGE_HISTORY (65536), MENTION_EVERYONE (131072)
UPDATE roles SET permissions = 2251804225 + 1024 + 65536 + 2048 + 16384 + 32768 + 131072
WHERE name = '@everyone' AND guild_id = '<guild_id>';
```

Or via the API:

```bash
# Get the @everyone role ID (same as guild ID for Spacebar)
curl -s -X PATCH "http://localhost:3100/api/v9/guilds/$GUILD_ID/roles/$GUILD_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: $TOKEN" \
  -d '{"permissions": 2251804225 + 1024 + 65536 + 2048 + 16384 + 32768 + 131072}'
```

After updating, the user must **reconnect** (clear browser site data if the
retry loop is already active). The WebSocket should stay stable with heartbeats
(OP 1 → OP 11 ACK).

**Prevention:** Always set base @everyone permissions as part of guild creation,
before inviting users.

### 🚨 READY Payload Missing `members` Array — Channels Invisible After Login

After fixing the @everyone permissions, the user can log in and the dashboard
loads, but clicking on the guild shows **no channels or members**. The client
knows the guild exists but can't render its contents.

**Root cause:** Spacebar's `Identify.ts` constructs the READY event payload
with a `guilds` array (containing channels, roles, etc.) but **omits the
`members` array** that should contain the current user&#39;s Guild Member object
for each guild. Discord&#39;s protocol requires each guild in READY to have a
corresponding member entry so the client knows the user&#39;s roles, nick,
permissions, and join timestamp. Without it, the client displays the guild
in the sidebar but shows zero channels when selected.

**Symptom (WebSocket READY payload inspection):**
```
READY: 1 guilds, 0 members    ← members array is missing
```

**Fix — Add `members` array to the READY payload:**

In `/opt/spacebar/dist/gateway/opcodes/Identify.js`, find the line containing
`guilds: remappedGuilds,` in the READY data object (around line 491):

```javascript
const { result: d, elapsed: buildReadyEventDataTime } = (0, util_1.timeFunction)(() =&gt; ({
    // ... other fields ...
    guilds: remappedGuilds,                    // ← find this line
    // ... rest of payload ...
}));
```

Add the `members` mapping immediately after the `guilds` line:

```javascript
guilds: remappedGuilds,
members: members.map(function(m) {
    return { ...m.toPublicMember(), user: user.toPublicUser() };
}),
```

Both `members` (Member.find result) and `user` (authenticated user) are already
in scope in the Identify handler — no imports needed.

After patching, restart Spacebar:

```bash
sudo systemctl restart spacebar.service
```

**Verification — READY payload should show 1+ members:**

```bash
TOKEN=$(curl -s -X POST https://domain/api/v9/auth/login \
  -H &quot;Content-Type: application/json&quot; \
  -d &#39;{&quot;email&quot;:&quot;user&quot;,&quot;password&quot;:&quot;pass&quot;}&#39; \
  | python3 -c &#39;import sys,json; print(json.load(sys.stdin)[&quot;token&quot;])&#39;)
python3 -c &quot;
import asyncio, websockets, json
async def t():
    async with websockets.connect(&#39;wss://domain/?encoding=json&amp;v=9&#39;) as ws:
        await ws.recv()                                         # Hello
        await ws.send(json.dumps({&#39;op&#39;:2,&#39;d&#39;:{&#39;token&#39;:&#39;$TOKEN&#39;,
            &#39;capabilities&#39;:16381,&#39;properties&#39;:{&#39;browser&#39;:&#39;Fermi&#39;},
            &#39;compress&#39;:False,&#39;presence&#39;:{&#39;status&#39;:&#39;online&#39;},
            &#39;large_threshold&#39;:100}}))
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=10)
            d = json.loads(msg)
            if d[&#39;op&#39;] == 0 and d.get(&#39;t&#39;) == &#39;READY&#39;:
                print(f&#39;READY: {len(d[&quot;d&quot;].get(&quot;guilds&quot;,[]))} guilds, &#39;
                      f&#39;{len(d[&quot;d&quot;].get(&quot;members&quot;,[]))} members&#39;)
                break
asyncio.run(t())
&quot;
# Expected: &quot;READY: 1 guilds, 1 members&quot;
```

**Note:** This patch modifies a compiled JavaScript file — it will be overwritten
on the next `npm run build`. For persistence across builds, also patch the
TypeScript source at `src/gateway/opcodes/Identify.ts`.

### Guild ownership issue

After fixing the @everyone permissions, the operator could log in and the dashboard
would load, but clicking on the guild showed **no channels or members**. The
Fermi (or any Discord) client knows the guild exists but can't render its
contents.

**Root cause:** Spacebar's `Identify.ts` constructs the READY event payload
with a `guilds` array (containing channels, roles, etc.) but **omits the
`members` array** that should contain the current user's Guild Member object
for each guild. Discord's protocol requires each guild in READY to have a
corresponding member entry so the client knows the user's roles, nick,
permissions, and join timestamp for that guild. Without it, the client
displays the guild in the sidebar but shows zero channels when selected.

Verified by connecting via WebSocket and inspecting the READY payload:
```
READY: 1 guilds, 0 members    ← members array is missing
```

The fix patches `dist/gateway/opcodes/Identify.js` to include mapped member
data in the READY payload.

**Fix — Add `members` array to the READY payload:**

In `/opt/spacebar/dist/gateway/opcodes/Identify.js`, find the line containing
`guilds: remappedGuilds,` in the READY data object (around line 491):

```javascript
const { result: d, elapsed: buildReadyEventDataTime } = (0, util_1.timeFunction)(() => ({
    // ... other fields ...
    guilds: remappedGuilds,                    // ← find this line
    // ... rest of payload ...
}));
```

Add the `members` mapping immediately after the `guilds` line:

```javascript
guilds: remappedGuilds,
members: members.map(function(m) {
    return { ...m.toPublicMember(), user: user.toPublicUser() };
}),
```

The `members` variable is already in scope (it's the result of the
`util_1.Member.find({ where: { id: this.user_id } })` query from earlier in
the function). The `user` variable is also in scope (the authenticated user).

After patching, restart Spacebar:

```bash
sudo systemctl restart spacebar.service
# or
fuser -k 3100/tcp; sleep 2; cd /opt/spacebar && CONFIG_PATH=... nohup node dist/bundle/start.js &
```

**Verification:**

```bash
TOKEN=$(curl -s -X POST https://domain/api/v9/auth/login -H "Content-Type: application/json" \
  -d '{"email":"user","password":"pass"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')
python3 -c "
import asyncio, websockets, json
async def t():
    async with websockets.connect('wss://domain/?encoding=json&v=9') as ws:
        await ws.recv()  # Hello
        await ws.send(json.dumps({'op':2,'d':{'token':'$TOKEN','capabilities':16381,
            'properties':{'browser':'Fermi'},'compress':False,
            'presence':{'status':'online'},'large_threshold':100}}))
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=10)
            d = json.loads(msg)
            if d['op'] == 0 and d.get('t') == 'READY':
                guilds = len(d['d'].get('guilds', []))
                members = len(d['d'].get('members', []))
                print(f'READY: {guilds} guilds, {members} members')
                break
asyncio.run(t())
"
# Expected: "READY: 1 guilds, 1 members"
```

If `members` count is 1 or more, the fix is working. If it's still 0, the
patch wasn't applied or the wrong file was edited.

**Note:** This patch modifies a compiled JavaScript file — it will be
overwritten on the next `npm run build`. For persistent changes, also patch
the TypeScript source at `src/gateway/opcodes/Identify.ts`.

### Guild ownership issue
If you re-run deployment with a different admin token, the new admin **is not the guild owner**. Fix:
- Delete the old guild from PostgreSQL: `DELETE FROM channels WHERE guild_id='<id>'; DELETE FROM guilds WHERE id='<id>';`
- Re-create with the correct admin's token
- The `PUT /guilds/:id/members/:user_id` endpoint requires OAuth2 — can't bypass for member invites
