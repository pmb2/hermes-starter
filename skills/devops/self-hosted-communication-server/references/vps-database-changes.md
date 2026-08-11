# VPS vs Local Database: Changes That Don't Stick

## The Root Cause of "Nothing Works"

Spacebar deployments commonly have **two PostgreSQL instances**:

| Instance | Location | Host | Port | Used For |
|----------|----------|------|------|----------|
| **VPS Database** | 129.153.156.190 | 127.0.0.1 | 5432 | Production Spacebar data |
| **Local Docker Postgres** | Local desktop | 127.0.0.1 | 5434 | Development/testing |

These are **completely separate databases** with different credentials, different passwords, and different schema states. Changes applied to one are invisible to the other.

**The critical trap:** When you SSH into the VPS and run SQL via `docker exec` or `psql`, you're hitting the VPS database. But when you run SQL via a local Docker command (`docker exec spacebar-postgres psql ...`), you're hitting the local database. The Spacebar server running on the VPS reads from the VPS database — it has no idea about the local one.

## How This Manifests

- You create 8 new team channels via SQL → they appear in `SELECT count(*) FROM channels` locally (returning 32)
- But `curl https://discy.your-domain.example/api/v9/guilds/{id}/channels` shows only 24 channels
- the operator reports "I don't see any of it implemented"
- You check the VPS DB → still only 24 channels

## Diagnosis: Verify Which Database You're Talking To

### Local Docker Postgres

```bash
# Use these commands for local changes (development only):
docker exec spacebar-postgres psql -U spacebar_admin -d spacebar -c "SELECT count(*) FROM channels;"

# Alternative with explicit port:
psql -h localhost -p 5434 -U spacebar_admin -d spacebar -c "SELECT count(*) FROM channels;"
```

### VPS Production Database

```bash
# Extract the exact connection URL from the Spacebar config:
DB_URL=$(grep "^DATABASE=" /opt/spacebar/.env | head -1 | sed 's/^DATABASE=//')

# Connect using the URL (handles password with special chars):
PGCONNECT_TIMEOUT=5 psql "$DB_URL" -c "SELECT count(*) FROM channels;"
```

**If the password contains special characters,** the `$DB_URL` approach is the most reliable. Avoid `-h`/`-U`/`PGPASSWORD` approaches which may fail on complex passwords.

## Fix: Apply Changes to the Right Database

### Step 1: Determine what needs changing locally

```bash
# Check local DB state:
docker exec spacebar-postgres psql -U spacebar_admin -d spacebar -c \
  "SELECT id::text, name FROM channels WHERE guild_id=<guild_id> ORDER BY id;"
```

### Step 2: Compare with VPS

```bash
ssh -i ~/.ssh/oracle_vps ubuntu@129.153.156.190 "
DB_URL=\$(grep '^DATABASE=' /opt/spacebar/.env | head -1 | sed 's/^DATABASE=//')
PGCONNECT_TIMEOUT=5 psql \"\$DB_URL\" -c \
  \"SELECT id::text, name FROM channels WHERE guild_id=<guild_id> ORDER BY id;\"
"
```

### Step 3: Apply changes to VPS

Write a SQL migration script and run it via SSH:

```bash
ssh -i ~/.ssh/oracle_vps ubuntu@129.153.156.190 "
DB_URL=\$(grep '^DATABASE=' /opt/spacebar/.env | head -1 | sed 's/^DATABASE=//')
PGCONNECT_TIMEOUT=5 psql \"\$DB_URL\" << 'EOSQL'
-- Your SQL here
INSERT INTO channels (...) VALUES (...);
UPDATE channels SET ...;
UPDATE guilds SET channel_ordering = ... WHERE id = ...;
EOSQL
"
```

### Step 4: Restart Spacebar on VPS

```bash
ssh -i ~/.ssh/oracle_vps ubuntu@129.153.156.190 "
kill <sb-bundle-pid>
cd /opt/spacebar && node --enable-source-maps dist/bundle/start.js &
sleep 5
curl -s http://localhost:3100/api/v9/gateway
"
```

## Common DB Operations That Need VPS Targeting

1. **Channel creation** (SQL INSERT) — must go to VPS DB
2. **Permission overwrites** (UPDATE channels SET permission_overwrites) — must go to VPS DB
3. **Channel ordering** (UPDATE guilds SET channel_ordering) — must go to VPS DB
4. **Role permissions** (UPDATE roles SET permissions) — must go to VPS DB AND restart after
5. **Member role assignment** (INSERT INTO member_roles) — must go to VPS DB AND restart after
6. **Bot user creation** (INSERT INTO users) — must go to VPS DB
7. **Application records** (INSERT INTO applications) — must go to VPS DB

## Verification After Changes

```bash
# From SSH:
ssh ubuntu@<vps> "curl -s http://localhost:3100/api/v9/guilds/<guild_id>/channels | python3 -c 'import json,sys; d=json.load(sys.stdin); print(f\"{len(d)} channels\")'"

# From anywhere (via public API):
curl -s -H "Authorization: <token>" \
  "https://discy.your-domain.example/api/v9/guilds/<guild_id>/channels" \
  | python -c "import json,sys; d=json.load(sys.stdin); print(f'{len(d)} channels')"
```

## Why This Keeps Happening

- Local commands (type `docker` or local `psql`) feel natural during development
- Sub-agents spawned with `delegate_task` default to the local environment
- The VPS requires SSH which adds friction
- The two databases are never automatically synced

**The fix:** Before any DB operation, explicitly ask: "Which Spacebar server is this change for?" If it's for the production instance that the operator uses, route through SSH to the VPS Postgres.
