# VPS Spacebar Operations

> **Context:** Managing the Spacebar self-hosted server on the Oracle Cloud VPS (hamilton-vps, 129.153.156.190). Covers SSH access, config editing, service management, rate-limit control, and batch bot onboarding from the VPS.

## SSH Access

```bash
ssh -i ~/.ssh/oracle_vps ubuntu@129.153.156.190
```

SSH key at `~/.ssh/oracle_vps` (with `oracle_vps.pub`), known hosts in `~/.ssh/known_hosts`.

## Spacebar on the VPS

Spacebar runs as a **native Node.js process** (not Docker on the VPS), served by the `sb-bundle-3100` binary at `/opt/spacebar/`.

```
Process:  sb-bundle-3100 (PID visible via `ps aux | grep sb-bundle`)
Config:   /opt/spacebar/config.production.json
Service:  systemd (spacebar.service)
Logs:     /opt/spacebar/spacebar.log
```

### Service Management

```bash
# Check status
sudo systemctl status spacebar

# Restart (picks up config changes)
sudo systemctl restart spacebar

# View logs
tail -f /opt/spacebar/spacebar.log

# Verify running
ss -tlnp | grep 3100    # Should show LISTEN :3100
curl -s http://localhost:3100/api/v9/gateway   # Should return {"url":"wss://discy.your-domain.example/"}
```

### Config Location

The Spacebar process reads `config.production.json` from its working directory (`/opt/spacebar/`). Config is loaded **at startup only** — changes require a restart.

## Disabling Rate Limiting

Rate limiting is in `config.production.json` under `limits.rate`. To disable:

```bash
cd /opt/spacebar
python3 -c "
import json
cfg = json.load(open('config.production.json'))
cfg['limits']['rate']['enabled'] = False
# Also blanket-lift specific route limits so they don't cause issues if re-enabled:
cfg['limits']['rate']['routes']['auth']['login']['count'] = 99999
cfg['limits']['rate']['routes']['auth']['login']['window'] = 1
cfg['limits']['rate']['routes']['guild']['count'] = 99999
cfg['limits']['rate']['routes']['guild']['window'] = 1
cfg['limits']['rate']['routes']['channel']['count'] = 99999
cfg['limits']['rate']['routes']['channel']['window'] = 1
json.dump(cfg, open('config.production.json', 'w'), indent=4)
"
sudo systemctl restart spacebar
```

After restart, verify:
```bash
# Should return "Token" immediately, no rate-limit errors:
curl -s -X POST http://localhost:3100/api/v9/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"login":"backus-admin","password":"backusAdmin2026!"}'
```

## Batch Bot Onboarding (VPS-side)

When onboarding many bots (40+), do it from the VPS directly — localhost API calls have no network latency and are faster than going through the public endpoint. Also bypasses any IP-based rate limiting that might have accumulated on your local machine.

### Approach: API via curl + Python

```python
# On VPS, run a batch script that:
API = "http://localhost:3100/api/v9"
GUILD_ID = "<discord-channel-id>"
BOT_ROLE = "<discord-channel-id>"
BOT_PW = "PulseBot2026!"

# For each bot:
# 1. POST /auth/login — get bot token
# 2. If login fails, POST /auth/register — create bot user
# 3. GET /users/@me — get bot user ID
# 4. PUT /guilds/{GUILD_ID}/members — join guild
# 5. PATCH /guilds/{GUILD_ID}/members/{uid} {"roles":[BOT_ROLE]} — assign Bot role via admin token
```

Key points:
- Login as backus-admin (password: backusAdmin2026!) to get admin token for role assignment
- Each bot uses password `PulseBot2026!` for API login
- Space 0.2-0.5s between API calls to avoid overwhelming the server
- The onboard script references `create-all-bots-db5.js` for direct SQL insertion pattern

### Approach: Direct SQL (for DB-reset recovery)

When tokens are invalidated by a DB reset, recreate users directly in PostgreSQL:

```bash
PGPASSWORD=BjetKw...BHYN psql -h localhost -U spacebar_admin -d spacebar \
  -c "INSERT INTO users (...) VALUES (...)"
```

The `create-all-bots-db5.js` script in `/opt/spacebar/` handles this with bcrypt password hashing and Snowflake ID generation.

## Postgres Connection Details

| Field | Value |
|-------|-------|
| Host | localhost (VPS) |
| Port | 5432 |
| Database | spacebar |
| User | spacebar_admin |
| Password | BjetKw61SUZCOLa4RUNbBHYN |
| Docker container | spacebar-postgres (local dev) / Docker on VPS (hidden) |

## Certificate & JWT Keys

Spacebar uses self-signed JWT keys at:
- `/opt/spacebar/jwt.key` — private key
- `/opt/spacebar/jwt.key.pub` — public key

These are generated during initial setup and SHOULD NOT be regenerated after bots have active tokens (invalidates all sessions).

## Common VPS Tasks

### Check Bot Sessions (DB Query)

```bash
PGPASSWORD=BjetKw...BHYN psql -h localhost -U spacebar_admin -d spacebar -c "
SELECT u.username, s.session_id, s.status, to_char(s.last_seen, 'HH24:MI:SS') as last_seen
FROM sessions s
JOIN users u ON u.id = s.user_id
WHERE u.bot = true
ORDER BY u.username;"
```

### List Bot Users

```bash
PGPASSWORD=BjetKw...BHYN psql -h localhost -U spacebar_admin -d spacebar -c "
SELECT username, id, verified FROM users WHERE bot=true ORDER BY username;"
```

### Count Guild Members

```bash
PGPASSWORD=BjetKw...BHYN psql -h localhost -U spacebar_admin -d spacebar -c "
SELECT COUNT(*) as guild_members FROM members WHERE guild_id = '<discord-channel-id>';"
```
