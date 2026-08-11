# Discord-to-Spacebar Migration Workflow

End-to-end process for migrating a Discord server (guild, channels, categories, members, bots) to a self-hosted Spacebar instance.

## Phase 1: Audit the Target Spacebar Instance

Before touching anything, map the current Spacebar state:

```bash
# 1. Is Spacebar running? On which port?
curl -s http://localhost:3100/api/v9/gateway

# 2. Check PostgreSQL database
psql -h 127.0.0.1 -U postgres -d spacebar -c "
  SELECT g.name, g.id, g.owner_id, u.username as owner,
    (SELECT count(*) FROM members m WHERE m.guild_id = g.id) as members,
    (SELECT count(*) FROM channels c WHERE c.guild_id = g.id) as channels
  FROM guilds g LEFT JOIN users u ON g.owner_id = u.id;"

# 3. Check all channels in the database
psql -h 127.0.0.1 -U postgres -d spacebar -c "
  SELECT c.guild_id, c.name, c.type, c.parent_id, c.position
  FROM channels c JOIN guilds g ON c.guild_id = g.id
  ORDER BY c.guild_id, c.position;"

# 4. Count users and messages
psql -h 127.0.0.1 -U postgres -d spacebar -c "
  SELECT count(*) as users FROM users;
  SELECT count(*) as messages FROM messages;"

# 5. Check for active ports (port 3001 often has Cal.com/etc)
netstat -ano | grep LISTENING | grep -E "3001|3100|3000|8080"
```

### Common Issues Found During Audit

- **Spacebar not running** — DB has data but server process is dead. Start it.
- **Port conflicts** — Cal.com or other services on 3001. Use port 3100 instead.
- **Duplicate guilds** — Multiple "the operator" guilds from repeated deployments.
- **No channel data visible via psql** — Snowflake IDs may be stored as bigint; use matching types in WHERE clauses.
- **0 bot flag on users** — Spacebar registers bots as regular users; the `bot` column may be `false` for all rows.
- **Fermi instances.json has git merge conflicts** — The `dist/webpage/` file often diverges from `src/webpage/`.

## Phase 2: Fix Spacebar Server

### 2a. Apply known patches (from self-hosted-communication-server skill)

Two patches required for Spacebar bundle mode on first startup with an existing DB:

```bash
# Patch 1: Monitoring.js — handle already-registered prometheus metrics
# Edit dist/util/monitoring/Monitoring.js
# Wrap each client.register.registerMetric() call in try/catch with
# getSingleMetric() fallback (see CDN Route Registration section in the skill)

# Patch 2: Server.js — isolate service starts so one failure doesn't block all
# Edit dist/bundle/Server.js
# Change Promise.all([api.start(), cdn.start(), gateway.start(), webrtc.start()])
# to add .catch() on each:
#   api.start().catch(e => console.error("[API] Failed:", e.message)),
```

### 2b. Start Spacebar

```bash
cd /path/to/spacebar
export CONFIG_PATH=config.production.json
export DATABASE=postgres://postgres@127.0.0.1:5432/spacebar
export NODE_OPTIONS="--max-old-space-size=4096"
export PORT=3100  # avoid port 3001 conflicts
export APPLY_DB_MIGRATIONS=false
node --enable-source-maps dist/bundle/start.js
```

### 2c. Verify it's up

```bash
# Wait for route registration (~10-60s), then:
curl -s http://localhost:3100/api/v9/gateway
# Expected: {"url":"ws://localhost:3100/"}

# Register a test user
curl -s -X POST http://localhost:3100/api/v9/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"architect","password":"TestPass123!","consent":true}'
```

## Phase 3: Fix Fermi Client

### 3a. Resolve instances.json issues

The file exists in two locations. Both must be updated:
- `src/webpage/instances.json` (source for rebuilds)
- `dist/webpage/instances.json` (runtime serving file)

**Fix merge conflicts in dist/webpage/instances.json** (git HEAD vs origin/main markers):
```json
{
  "name": "Local Spacebar",
  "description": "Description",
  "urls": {
    "api": "http://localhost:3100/api/v9",
    "gateway": "ws://localhost:3100/",
    "cdn": "http://localhost:3100",
    "wellknown": "http://localhost:3100"
  },
  "url": "http://localhost:3100",
  "display": true
}
```

**Critical fields for local instance:**
- `urls.wellknown` — REQUIRED. Fermi's Specialuser constructor calls `new URL(json.serverurls.wellknown)`. Without it, login throws `TypeError: URL constructor: undefined is not a valid URL`.
- `urls.gateway` — MUST have trailing slash (`ws://localhost:3100/` not `ws://localhost:3100`).
- `display: true` — Makes it visible in the instance picker.

### 3b. Restart Fermi (required for instances.json changes)

```bash
kill $(pgrep -f 'node dist/index') 2>/dev/null
sleep 1
cd /path/to/Fermi && node dist/index.js
```

Fermi caches instances.json in memory at startup. Simple HTML edits (not instances.json) don't need a restart.

## Phase 4: Consolidate Guilds

Spacebar instances often have multiple duplicate guilds from repeated deployment runs.

### 4a. Identify duplicate guilds

```sql
SELECT g.id, g.name, g.owner_id, u.username,
  (SELECT count(*) FROM members m WHERE m.guild_id = g.id) as members
FROM guilds g LEFT JOIN users u ON g.owner_id = u.id
ORDER BY g.name;
```

### 4b. Delete duplicate guilds (directly in SQL)

```sql
DELETE FROM channels WHERE guild_id = '<duplicate-guild-id>';
DELETE FROM members WHERE guild_id = '<duplicate-guild-id>';
DELETE FROM invites WHERE guild_id = '<duplicate-guild-id>';
DELETE FROM guilds WHERE id = '<duplicate-guild-id>';
```

Best practice: delete all guilds and re-create the one you want via the API, using the admin user's token.

### 4c. Create a new guild via API

```bash
GUILD=$(curl -s -X POST "http://localhost:3100/api/v9/guilds" \
  -H "Content-Type: application/json" \
  -H "Authorization: <admin-token>" \
  -d '{"name":"Automation Team"}' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "Guild ID: $GUILD"
```

**Pitfall:** Don't include `description` in the create payload — Spacebar's schema uses `additionalProperties: false` which rejects it. Create guild with just `{"name":"..."}`.

## Phase 5: Recreate Channels

### 5a. Design Principle: "Take the best from both, improve ours"

When moving from Discord to Spacebar, don't blindly mirror the Discord server's structure. Apply the "improve ours" principle:

- **Keep the Discord channel names** so everyone recognizes where things are
- **Organize into logical categories** rather than one flat list
- **Add categories that improve navigation** — a flat Discord server with 14+ channels can be much better organized with categories

**Bad (literal mirror):**
```
Text Channels
├── #command, #dev, #revenue, #intel, #finance, #legal, #ops, #content
├── #pulse-feed, #health, #sports-betting, #investing, #cyber, #ideas
Voice
├── #voice
```

**Good (optimized):**
```
General           │  Technology        │  Revenue
├── #command      │  ├── #dev          │  ├── #revenue
├── #ideas        │                    │
                   │                    │
Intelligence      │  Finance           │  Legal
├── #intel        │  ├── #finance      │  ├── #legal
├── #pulse-feed   │  ├── #investing    │
                   │                    │
Operations        │  Content & Media   │  Cyber Security
├── #ops          │  ├── #content      │  ├── #cyber
                   │                    │
Health            │  Sports            │  Voice Channels
├── #health       │  ├── #sports-betting│ ├── #voice
```

The rule: **Discord channel names are preserved** (so links and expectations carry over). Categories are redesigned to be cleaner than the original. Channels with related topics go under the same parent.

### 5b. Create categories first, then channels

Channel types:
- Type 0 = GUILD_TEXT
- Type 2 = GUILD_VOICE  
- Type 4 = GUILD_CATEGORY

```bash
# Create a category
CAT_ID=$(curl -s -X POST "http://localhost:3100/api/v9/guilds/$GUILD_ID/channels" \
  -H "Content-Type: application/json" \
  -H "Authorization: $TOKEN" \
  -d '{"name":"Category Name","type":4}' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Create a text channel under the category (order by position)
curl -s -X POST "http://localhost:3100/api/v9/guilds/$GUILD_ID/channels" \
  -H "Content-Type: application/json" \
  -H "Authorization: $TOKEN" \
  -d "{\"name\":\"channel-name\",\"type\":0,\"parent_id\":\"$CAT_ID\"}"
```

### 5b. Script the full channel structure

For a migration with 10+ channels, write a Python script that reads a channel map and creates them sequentially:

```python
import requests, time

API = "http://localhost:3100/api/v9"
TOKEN = "<admin-token>"
GUILD_ID = "<guild-id>"

HEADERS = {"Authorization": TOKEN, "Content-Type": "application/json"}

# Define channel structure: (name, type, parent_position or None)
CHANNELS = {
    "categories": [
        {"name": "Command Center", "type": 4},
        {"name": "Technology", "type": 4},
        {"name": "Operations", "type": 4},
    ],
    "channels": [
        ("general", 0, 0),          # Under Command Center
        ("announcements", 0, 0),    # Under Command Center
        ("command", 0, 0),          # Under Command Center
        ("dev", 0, 1),              # Under Technology
        ("infra", 0, 1),            # Under Technology
        ("alerts", 0, 2),           # Under Operations
    ]
}

# Create categories, collect IDs
cat_ids = []
for cat in CHANNELS["categories"]:
    r = requests.post(f"{API}/guilds/{GUILD_ID}/channels", headers=HEADERS,
                      json={"name": cat["name"], "type": cat["type"]})
    cat_ids.append(r.json()["id"])
    time.sleep(0.5)

# Create channels under their parent category
for name, ctype, parent_idx in CHANNELS["channels"]:
    requests.post(f"{API}/guilds/{GUILD_ID}/channels", headers=HEADERS,
                  json={"name": name, "type": ctype, "parent_id": cat_ids[parent_idx]})
    time.sleep(0.5)
```

## Phase 6: Invite Members

### 6a. Spacebar invites: use SQL to add members

Spacebar's `PUT /guilds/:id/members/:user_id` requires OAuth2. For non-OAuth setups, add members directly in SQL.

**Full INSERT pattern (all required columns):**

```sql
INSERT INTO members (id, guild_id, nick, joined_at, deaf, mute, pending, settings, bio, flags)
VALUES (
  <user-id>,      -- the user's Snowflake ID from users table
  '<guild-id>',   -- the guild Snowflake ID
  '<nickname>',   -- optional display name
  NOW(),
  false, false, false,
  '{"flags":0,"muted":false,"version":0,"guild_id":null,"mobile_push":true,"mute_config":null,"suppress_roles":false,"channel_overrides":{},"notify_highlights":0,"suppress_everyone":false,"hide_muted_channels":false,"message_notifications":1,"mute_scheduled_events":false}',
  '',
  0
);
```

**Bulk insert all users at once:**
```sql
INSERT INTO members (id, guild_id, nick, joined_at, deaf, mute, pending, settings, bio, flags)
SELECT 
  u.id, 
  '<guild-id>'::bigint, 
  u.username, 
  NOW(), 
  false, false, false, 
  '{"flags":0,"muted":false,"version":0,"guild_id":null,"mobile_push":true,"mute_config":null,"suppress_roles":false,"channel_overrides":{},"notify_highlights":0,"suppress_everyone":false,"hide_muted_channels":false,"message_notifications":1,"mute_scheduled_events":false}'::jsonb,
  '', 
  0
FROM users u
WHERE NOT EXISTS (
  SELECT 1 FROM members m 
  WHERE m.id = u.id AND m.guild_id = '<guild-id>'::bigint
);
```

### 6b. Verify members via API

```bash
curl -s -H "Authorization: <token>" \
  "http://localhost:3100/api/v9/guilds/<guild-id>/members?limit=100" \
  | python -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} members')"
```

## Phase 7: Migrate Bot Gateways

### 7a. Fresh registration approach (recommended)

When migrating to a NEW Spacebar instance with different JWT keys, old tokens are invalid. The simplest approach is to register fresh bot accounts via the API:

```bash
# Register a new bot user (Spacebar rejects "bot": true, register as regular)
curl -s -X POST http://localhost:3100/api/v9/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"chief-of-staff","password":"FreshPass123!","consent":true,"date_of_birth":"1990-01-01"}'

# Capture the token from the response -- this is your DISCORD_BOT_TOKEN
```

**Important:** Registration also captures the user's ID (from JWT payload). You'll need to add this user to the guild via SQL (Phase 6) since the invite endpoint requires OAuth2.

### 7b. Point Hermes gateway at Spacebar

Edit the profile's `.env`:
```env
DISCORD_BOT_TOKEN=<spacebar-token>
HERMES_GATEWAY_BUSY_ACK_ENABLED=false
DISCORD_COMMAND_SYNC_POLICY=off   # REQUIRED — prevents slash-command sync crash
```

**🚨 `DISCORD_COMMAND_SYNC_POLICY=off` is REQUIRED.** Without this, every gateway crashes ~20s after connecting because Spacebar returns 404 on the slash-command sync endpoint (`/applications/{id}/commands`). Set it in every profile's `.env`.

**Bulk fix:**
```bash
for d in ~/AppData/Local/hermes/profiles/*/; do
  echo "DISCORD_COMMAND_SYNC_POLICY=off" >> "$d/.env"
done
```

### 7c. Clean up stale state files

Before starting gateways, remove old state that causes token/session bleed:

```bash
# Remove stale .env.spacebar files (override tokens with old values)
find ~/AppData/Local/hermes/profiles -name ".env.spacebar" -delete

# Remove stale gateway state files
for profile in ~/AppData/Local/hermes/profiles/*/; do
  rm -f "$profile/gateway.pid" "$profile/gateway_state.json" \
        "$profile/gateway.lock.spacebar" "$profile/.gateway_state"*
done

# Clear old logs to avoid confusion
rm -f scripts/logs/*-gateway.log
```

### 7d. Start gateways with clean environments

Use the spacebar-gateway.py wrapper (in agent-fleet repo) which patches discord.py constants to point at localhost:3100.

**Recommended startup method — Python subprocess with clean env dict:**
This avoids stale env var inheritance from the parent shell. See the `scripts/start-fleet4.py` example in the agent-fleet repo for the complete pattern.

Key points for the env dict:
```python
env = {
    "DISCORD_BOT_TOKEN": "<token>",
    "HERMES_HOME_BASE": "${USER_HOME}/AppData/Local/hermes",
    "SPACEBAR_API_BASE": "http://localhost:3100/api/v9",
    "SPACEBAR_WS_URL": "ws://localhost:3100/",
    "HERMES_GATEWAY_BUSY_ACK_ENABLED": "false",
    # Copy essential system vars from parent
    "PATH": os.environ.get("PATH", ""),
    "HOME": os.environ.get("HOME", ""),
    "USERPROFILE": os.environ.get("USERPROFILE", ""),
    "APPDATA": os.environ.get("APPDATA", ""),
    "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
    "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
    "COMSPEC": os.environ.get("COMSPEC", ""),
}
proc = subprocess.Popen(
    ["python", "scripts/spacebar-gateway.py", profile],
    stdout=open(log_file, "a"), stderr=subprocess.STDOUT,
    cwd=project_dir, env=env,
    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
)
```

## Phase 8: Import Message History (from Discord API)

After the guild structure and members are in place, import message history from Discord into the Spacebar PostgreSQL database.

### 8a. Export messages from Discord

Use the Discord REST API with a bot token that has access to the target server. The bot needs `READ_MESSAGE_HISTORY` intent (enabled in Discord Developer Portal).

**Full pagination pattern (messages are fetched newest-first using `before` cursor):**

```python
def paginate_messages(channel_id, limit=100):
    """Fetch ALL messages from a Discord channel. Stops when batch < limit."""
    all_msgs = []
    before = None
    while True:
        params = f"?limit={limit}"
        if before:
            params += f"&before={before}"
        r = requests.get(f"https://discord.com/api/v10/channels/{channel_id}/messages{params}",
                         headers={"Authorization": f"Bot {TOKEN}"})
        batch = r.json()
        if not batch or not isinstance(batch, list):
            break
        all_msgs.extend(batch)
        if len(batch) < limit:
            break  # Reached the beginning of history
        before = batch[-1]["id"]
        time.sleep(0.5)  # Discord rate limit: 50 req/s
    return all_msgs
```

**Member pagination uses `after` cursor (opposite direction):**
```python
def paginate_members(guild_id, limit=1000):
    all_members = []
    after = None
    while True:
        params = f"?limit={limit}"
        if after:
            params += f"&after={after}"
        batch = api("GET", f"/guilds/{guild_id}/members{params}")
        if not batch or not isinstance(batch, list):
            break
        all_members.extend(batch)
        if len(batch) < limit:
            break
        after = batch[-1]["user"]["id"]
        time.sleep(0.5)
    return all_members
```

**Note:** `before` goes backwards from newest to oldest (messages endpoint). `after` goes forward (members endpoint). Using the wrong cursor direction returns empty results.

### 8b. Import messages into Spacebar

The Spacebar `messages` table has several NOT NULL columns that don't accept defaults:

```sql
\d messages
```

**Critical NOT NULL columns:**
- `embeds` jsonb NOT NULL — must be `'[]'::jsonb`
- `reactions` jsonb NOT NULL — must be `'{}'::jsonb`  
- `message_snapshots` jsonb NOT NULL — must be `'[]'::jsonb`
- `type` integer NOT NULL — use `0` (DEFAULT)
- `flags` integer NOT NULL — use `0` (DEFAULT)

**INSERT SQL template:**
```sql
INSERT INTO messages (
    id, channel_id, guild_id, author_id, content, timestamp,
    embeds, reactions, type, flags, mention_everyone, tts,
    pinned_at, nonce, message_reference, message_snapshots
) VALUES (
    <discord-message-id>,     -- bigint (Discord snowflake fits in PG bigint)
    <spacebar-channel-id>,    -- bigint
    <spacebar-guild-id>,      -- bigint
    <author-user-id>,         -- bigint (must exist in users table)
    '<message-content>',      -- varchar
    '<timestamp>',            -- ISO 8601 timestamp
    '[]'::jsonb,              -- embeds
    '{}'::jsonb,              -- reactions
    0, 0, false, false,       -- type, flags, mention_everyone, tts
    NULL, NULL, NULL,         -- pinned_at, nonce, message_reference
    '[]'::jsonb               -- message_snapshots
)
ON CONFLICT (id) DO NOTHING;
```

**Author mapping:** Discord user IDs != Spacebar user IDs. Map by matching Discord message author `username` to Spacebar's `users.username`. For unmatched authors (like "Hermes Agent" bot), assign messages to an admin user:

```python
AUTHOR_MAP = {
    "Hermes Agent": architect_user_id,  # Messages from the main bot
    "the.engineer": architect_user_id,  # External user
}
```

**Duplicate handling:** Use `ON CONFLICT (id) DO NOTHING` since Discord message Snowflake IDs are unique and fit in PostgreSQL bigint. If the same message was already imported (e.g., from a previous run), it's safely skipped.

**Note about message_timestamp:** Discord timestamps are ISO 8601 with timezone (e.g., `2026-06-21T13:56:07.106000+00:00`). Cast directly to PostgreSQL `timestamp without time zone` — the timezone info is preserved in the value.

### 8c. Thread messages — full discovery with pagination

Discord threads are separate virtual channels. There are THREE sources that must all be checked with pagination:

**1. Active threads** — currently unarchived (recent activity):
```python
active = api("GET", f"/channels/{channel_id}/threads/active")
```

**2. Archived public threads** — paginated by `archive_timestamp` using the `has_more` flag:
```python
def paginate_archived_threads(channel_id, thread_type="public"):
    """Fully paginate archived threads. thread_type: 'public' or 'private'."""
    threads = []
    before = None
    while True:
        path = f"/channels/{channel_id}/threads/archived/{thread_type}?limit=100"
        if before:
            path += f"&before={before}"
        data = api("GET", path)
        if not data or "threads" not in data or len(data["threads"]) == 0:
            break
        threads.extend(data["threads"])
        # has_more is the key — without it you miss threads when the
        # last batch happens to have exactly 100 results
        if not data.get("has_more") or len(data["threads"]) < 100:
            break
        before = data["threads"][-1]["thread_metadata"]["archive_timestamp"]
        time.sleep(0.5)
    return threads
```

**3. Archived private threads** — same pattern, different endpoint:
```python
archived_private = paginate_archived_threads(channel_id, "private")
```

**De-duplicate threads across sources** (same thread can appear in active AND archived):
```python
all_threads = []
seen_ids = set()
for batch in [active_threads, archived_public, archived_private]:
    for t in batch:
        if t["id"] not in seen_ids:
            all_threads.append(t)
            seen_ids.add(t["id"])
```

**Import thread messages into parent channel in Spacebar** (Spacebar doesn't have full thread support):
```python
for thread in all_threads:
    thread_msgs = paginate_messages(thread["id"])
    for msg in thread_msgs:
        insert_into_spacebar(msg, spacebar_parent_channel_id)
```

## Phase 9: Deploy to Public Domain

After the local Spacebar instance has the complete migrated data (guild, channels, members, messages, bots), deploy it to a public-facing VPS.

### 9a. Dump local DB and transfer to VPS

```bash
# Dump local database (no owner/ACL to avoid VPS user mismatch)
pg_dump -h 127.0.0.1 -U postgres -d spacebar --no-owner --no-acl -f /tmp/spacebar_dump.sql

# Transfer to VPS
scp -i ~/.ssh/oracle_vps /tmp/spacebar_dump.sql ubuntu@vps:/tmp/spacebar_dump.sql

# On VPS: verify DB credentials work BEFORE stopping Spacebar
PGPASSWORD='<db-password>' psql -h 127.0.0.1 -U <db-user> -d spacebar -c 'SELECT 1;'
# ↑ If this fails, the DB password may need resetting. Fix:
#   sudo -u postgres psql -c "ALTER USER <db-user> WITH PASSWORD '<db-password>';"

# Stop Spacebar (kill ALL instances — not just the first one!)
kill $(pgrep -f 'dist/bundle/start') 2>/dev/null
# Or more aggressively if multiple PIDs hold the port:
fuser -k 3100/tcp 2>/dev/null
sleep 2

# Drop and recreate schema
psql -h 127.0.0.1 -U <db-user> -d spacebar -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
# Restore dump
psql -h 127.0.0.1 -U <db-user> -d spacebar -f /tmp/spacebar_dump.sql

# Verify data restored
psql -h 127.0.0.1 -U <db-user> -d spacebar -c 'SELECT count(*) as users FROM users;'
psql -h 127.0.0.1 -U <db-user> -d spacebar -c 'SELECT count(*) as messages FROM messages;'
```

**🚨 ALWAYS kill ALL Spacebar processes, not just the first one.** `pgrep -f 'dist/bundle/start'` can return multiple PIDs (stale instances from previous failed starts). A leftover instance keeps the port bound, causing `EADDRINUSE` on restart. If you see `Error: listen EADDRINUSE: address already in use :::3100` in the logs, `fuser -k 3100/tcp` is the nuclear option that clears them all. Verify with `ss -tlnp | grep 3100 || echo "Port clear"`.

**🚨 PostgreSQL password may need resetting after restore.** The role password hash from the dump may not match scram-scram on the target cluster. The symptom: `psql` works as `postgres` superuser but fails as the app user. Fix with `ALTER USER` as shown above.

### 9b. Update Spacebar config for public domain

Edit `config.production.json` on the VPS:

```json
{
  "general": { "serverName": "gc.your.domain" },
  "api": { "endpointPublic": "https://gc.your.domain/api/v9" },
  "gateway": { "endpointPublic": "wss://gc.your.domain/" },
  "cdn": { "endpointPublic": "https://gc.your.domain" }
}
```

**All four fields must be updated to the public domain.** Spacebar returns the `gateway.endpointPublic` value in the `GET /api/v9/gateway` response. Fermi compares this URL's hostname against the API URL's hostname — if they don't match, login is blocked.

### 9c. Restart Spacebar on VPS

```bash
cd /opt/spacebar
export CONFIG_PATH=config.production.json
export DATABASE=postgres://<user>:<pass>@127.0.0.1:5432/spacebar
export NODE_OPTIONS='--max-old-space-size=4096'
export PORT=3100
nohup node --enable-source-maps dist/bundle/start.js >> spacebar.log 2>&1 &
```

### 9d. Update Fermi instances on VPS

Fermi's `instances.json` must list the public domain as the primary instance. Restart Fermi after changing instances.json (it's cached at startup).

### 9e. Update local bot profiles

After the public domain is live, update all local Hermes profiles to point at the public domain instead of localhost, then restart gateways.

### 9f. Verify end-to-end through public domain

Check API responds (200), Fermi UI loads (302), login works (token returned), guild structure intact.

## Phase 10: Migration Philosophy

### 10a. The "Best of Both" Principle

When migrating from Discord to Spacebar, the operator's direction is: **"take the best from both setups and improve ours."** This means:

1. **Preserve Discord channel names** so everyone recognizes where things are
2. **Redesign the category structure** — Discord tends to accumulate flat channel lists. Use Spacebar's self-hosted advantage to organize better
3. **Eliminate dead channels** — Don't carry over channels that were never used
4. **Add logic that was missing** — If Discord had 14 channels in one category, split them into meaningful groups

The channel layout should be better than both the original Discord AND a plain mirror.

### 10b. the operator's Standards

- **Completeness is non-negotiable.** "Copy everything, past threads too, full pagination" — every export must paginate fully with before/after cursors and check has_more on every response.
- **Threads are the biggest blind spot** — always check active, archived public, AND archived private with separate pagination loops.
- **Don't settle for good enough.** Push through until every channel, message, role, and bot is verified.
- **Improve on what you find.** Don't just mirror — make it better.

## Phase 11: Verification Checklist
- [ ] Fermi loads at `http://localhost:8080` with "Local Spacebar" instance visible
- [ ] Login works from Fermi with a registered admin user
- [ ] The target guild appears in the channel list
- [ ] All categories and channels visible in correct order
- [ ] Bot gateways connect with `[Spacebar] INFO Route.BASE` log showing localhost
- [ ] Gateway logs show `Connected as botname#0001` with NO slash-sync crash
- [ ] Messages can be sent and received in channels
- [ ] `DISCORD_COMMAND_SYNC_POLICY=off` is set in every profile's `.env`
- [ ] Thread message count matches Discord export (check `has_more` on every page)

## Pitfalls Summary

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Port 3001 taken by Cal.com | Spacebar won't start | Use PORT=3100 |
| Prometheus metric double-registration | Spacebar crashes at startup | Patch Monitoring.js with try/catch |
| Fermi instances.json merge conflicts | Fermi loads wrong URLs | Clean up dist/webpage/instances.json |
| Missing `wellknown` in instances.json | Fermi login fails with URL constructor error | Add "wellknown" to urls object |
| Guild create with description field | Returns 50035 Invalid Form Body | Create with `{"name": "..."}` only |
| `localhost` resolves to IPv6 on Windows | PostgreSQL auth fails | Use `127.0.0.1` instead |
| valid_tokens_since after restart | All tokens rejected | Reset to epoch in SQL |
| No guilds visible | New user can't find guilds | Add members directly in SQL |
| Gateway crashes after connecting | Slash command sync 404 | Set `DISCORD_COMMAND_SYNC_POLICY=off` |
| Stale .env.spacebar in profile | Gateway uses old token | Delete all .env.spacebar files |
| Stale env vars in parent shell | Gateway inherits wrong token | Use clean env dict in subprocess |
| `APPLY_DB_MIGRATIONS=false` required | TypeORM migration crash on existing DB | Disable migrations for pre-seeded DB |
| Thread pagination missing `has_more` check | Miss threads when batch = 100 | Check `data.get("has_more")` before continuing |
| Using wrong cursor direction | API returns empty results | Messages use `before`, Members use `after` |
| Missing `embeds`/`reactions` in INSERT | Message import fails NOT NULL constraint | Always include `'[]'::jsonb` and `'{}'::jsonb` |
