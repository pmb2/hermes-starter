# Local Spacebar Deployment (Windows Desktop)

When the VPS can't handle 39+ bots, run Spacebar entirely on Windows Desktop.

## Architecture

```
Windows Desktop
├── Docker PostgreSQL (spacebar-postgres, port 5434)
├── Spacebar Server (Node.js native, port 3100)
├── 39+ Bot Gateways (spacebar-gateway.py → localhost:3100)
└── External access via VPS Caddy (if needed)
```

## Key Differences from VPS Deployment

| Aspect | VPS | Local |
|--------|-----|-------|
| DB location | VPS Postgres (port 5432) | Docker Postgres (port 5434) |
| Spacebar API | discy.your-domain.example/api/v9 | localhost:3100/api/v9 |
| JWT algorithm | ES512 (ECDSA P-521) | HS256 (HMAC-SHA256) |
| JWT secret | VPS-generated keypair | Config `jwtSecret` value |
| Token generation | Node.js script with ES512 signing | Python `jwt.encode()` with HS256 |

## Local Setup

### 1. Docker PostgreSQL

```bash
# Start the spacebar Postgres container
docker run -d --name spacebar-postgres \
  -e POSTGRES_USER=spacebar_admin \
  -e POSTGRES_DB=spacebar \
  -p 5434:5432 \
  postgres:16-alpine

# Restore or create the DB
PGCONNECT_TIMEOUT=5 psql -U spacebar_admin -h localhost -p 5434 -d spacebar
```

### 2. Spacebar Config

Config at `${MY_REPOS}/spacebar/config.production.json`:

```json
{
  "api": { "endpointPrivate": "http://localhost:3100/api/v9", ... },
  "gateway": { "endpointPrivate": "ws://localhost:3100/", ... },
  "cdn": { "endpointPrivate": "http://localhost:3100", ... },
  "general": { "autoCreateBotUsers": true },
  "security": {
    "captcha": { "enabled": false },
    "jwtSecret": "<relay-pubkey-hex>"
  },
  "limits": { "rate": { "enabled": false } }
}
```

`.env` file:
```
DATABASE=postgres://spacebar_admin@localhost:5434/spacebar
PORT=3100
CONFIG_PATH=config.production.json
APPLY_DB_MIGRATIONS=false
```

### 3. Start Spacebar

```bash
cd ${MY_REPOS}/spacebar
export DATABASE="postgres://spacebar_admin@localhost:5434/spacebar"
export PORT=3100
export NODE_ENV=production
nohup node --enable-source-maps dist/bundle/start.js > spacebar.log 2>&1 &
```

Verify: `curl -s -o /dev/null -w "%{http_code}" http://localhost:3100/api/v9/gateway` → `200`

### 4. Generate Bot Tokens (Python + HS256)

Use PyJWT with the config's `jwtSecret` value. Spacebar's HS256 accepts simple symmetric JWTs.

```python
import jwt, time

JWT_SECRET = "<relay-pubkey-hex>"

def generate_bot_token(bot_id, username):
    now = int(time.time())
    payload = {
        "id": bot_id,
        "username": username,
        "bot": True,
        "iat": now,
        "exp": now + 31536000,  # 1 year
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# Verify against Spacebar API
token = generate_bot_token("<discord-channel-id>", "chief-of-staff")
# curl -s http://localhost:3100/api/v9/users/@me -H "Authorization: $token"
# → Returns user object with "bot": true
```

### 5. Create Bot Users (DB INSERT)

Since Spacebar's `POST /auth/register` doesn't accept `bot: true` as a property, create bot users directly:

```python
# Generate snowflake ID
import time
seq = 0
def snowflake():
    global seq
    epoch = 1420070400000  # Discord epoch
    now = int(time.time() * 1000) - epoch
    seq = (seq + 1) % 4096
    return (now << 22) | (1 << 17) | (1 << 12) | seq

# INSERT into users table
INSERT INTO users (
  id, username, discriminator, bot, created_at, verified,
  data, rights, flags, public_flags, purchased_flags,
  premium_usage_flags, desktop, mobile, premium, premium_type,
  bio, system, nsfw_allowed, mfa_enabled, disabled, deleted,
  email, fingerprints, badge_ids, avatar_decoration_data
) VALUES (
  <snowflake>, '<name>', '0000', true, NOW(), true,
  '{"hash": "$2b$12$...", "valid_tokens_since": "1970-01-01T00:00:00.000Z"}'::jsonb,
  875069521787904, 0, 0, 0, 0,
  false, false, true, 2, ''::character varying,
  false, false, false, false, false,
  ''::character varying, '{}'::character varying[],
  '{}'::bigint[], NULL::jsonb
);
```

### 6. Write Tokens to Profile .env

Each profile at `~/.hermes/profiles/<name>/.env` needs:
```
DISCORD_BOT_TOKEN=<jwt_token>
GATEWAY_ALLOW_ALL_USERS=true
DISCORD_ALLOW_ALL_USERS=true
```

### 7. Start Bot Gateways

```bash
PYTHONPATH=${HERMES_HOME}/hermes-agent \
SPACEBAR_API_BASE=http://localhost:3100/api/v9 \
SPACEBAR_WS_URL=ws://localhost:3100/ \
GATEWAY_ALLOW_ALL_USERS=true \
DISCORD_ALLOW_ALL_USERS=true \
${HERMES_HOME}/hermes-agent/venv/Scripts/python.exe \
${MY_REPOS}/agent-fleet/scripts/spacebar-gateway.py \
<profile_name>
```

Start bots sequentially with 3-5 second stagger to avoid identify collisions on Spacebar.

## Fleet Manager

`fleet-core.py` at `agent-fleet/scripts/fleet-core.py` handles sequential launch + watchdog for the Executive Council.
