# Spacebar Windows Setup (May 2026)

Full end-to-end setup of Spacebar server on Windows 10 as a Discord replacement for AI agent teams.

## Repo

- **Upstream**: https://github.com/spacebarchat/server
- **Fork**: https://github.com/pmb2/spacebar
- **Clone**: `${MY_REPOS}\Documents\github\spacebar`
- **Upstream remote**: `git remote add upstream https://github.com/spacebarchat/server.git`

## Environment

- Windows 10, 13th Gen Intel i9-13900KS, 32 cores
- Node.js 22.14.0, npm 11.12.1
- Python 3.11.9
- PostgreSQL 16 (Windows native install at `C:\Program Files\PostgreSQL\16`)
- Docker Desktop 29.5.2 (unreliable for ghcr.io pulls)

## Database

```sql
CREATE DATABASE spacebar;
CREATE USER spacebar WITH PASSWORD '***';
GRANT ALL PRIVILEGES ON DATABASE spacebar TO spacebar;
GRANT ALL ON SCHEMA public TO spacebar;
```

**🚨 Critical: use `127.0.0.1` not `localhost`.** On Windows, `localhost` resolves to IPv6 `::1` which uses `scram-sha-256` password auth per default `pg_hba.conf`. Only `127.0.0.1` (IPv4) can use `trust` auth. Verify your pg_hba.conf:

```conf
host    all             all             127.0.0.1/32            trust
```

If `trust` is not set, you'll get `password authentication failed` errors when the server starts.

Local PostgreSQL configured with `trust` auth for IPv4 127.0.0.1 (`pg_hba.conf`):
```
host    all             all             127.0.0.1/32            trust
```

## Installation

```bash
git clone https://github.com/pmb2/spacebar.git
cd ${MY_REPOS}/spacebar
npm install        # installs 596 packages
npm run build:tsgo # generates schemas + builds TypeScript
```

## Configuration

### .env
```
DATABASE=postgres://spacebar:***@127.0.0.1:5432/spacebar
CONFIG_PATH=config.json
```

### First run
Start the server to generate `config.json` and database schema:
```bash
npm run start
```
It will fail with "Invalid config values" — that's expected. Edit `config.json`.

### config.json edits for bundle mode
```jsonc
{
  "general": { "serverName": "localhost:3001" },
  "api": {
    "endpointPublic": "http://localhost:3001/api/v9",
    "endpointPrivate": "http://localhost:3001/api/v9"
  },
  "cdn": {
    // 🚨 NO trailing slash — "http://localhost:3001/" + "/avatars/id" = "//avatars/id" → 404
    "endpointPublic": "http://localhost:3001",
    "endpointPrivate": "http://localhost:3001"
  },
  "gateway": {
    "endpointPublic": "ws://localhost:3001/",
    "endpointPrivate": "ws://localhost:3001/"
  },
  "security": {
    "jwtSecret": "<random-hex-32-bytes>"
  },
  "register": {
    "disabled": false,
    "requireCaptcha": false,
    "requireInvite": false,
    "dateOfBirth": { "required": false },
    "email": { "required": false },
    "password": {
      "required": false,
      "minLength": 1,
      "minNumbers": 0,
      "minUpperCase": 0,
      "minSymbols": 0
    },
    "allowNewRegistration": true
  },
  "login": { "requireVerification": false },
  "limits": { "rate": { "enabled": false } }
}
```

## Patch: Username Login

**File**: `src/api/routes/auth/login.ts`
**Issue**: Login only searches by `phone` or `email`, not `username`.
**Fix**: Add `{ username: login }` to the TypeORM `where` clause:

```typescript
// Before (line 69):
where: [{ phone: login }, { email: login }],

// After:
where: [{ phone: login }, { email: login }, { username: login }],
```

**Rebuild**: `npm run build:src` (then restart server)

## Running

```bash
# Start (foreground)
cd ${MY_REPOS}/spacebar && npm run start

# Or double-click start-spacebar.bat
```

Server listens on **port 3001**.

## API Verification

```bash
# Gateway endpoint
curl http://localhost:3001/api/v9/gateway
# → {"url":"ws://localhost:3001/"}

# Register user
curl -X POST http://localhost:3001/api/v9/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"bot","password":"***","email":"bot@spacebar.local","consent":true}'

# Login by username
curl -X POST http://localhost:3001/api/v9/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"bot","password":"***"}'

# Get current user
curl http://localhost:3001/api/v9/users/@me \
  -H "Authorization: <token>"
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port 3001 in use | `taskkill /F /PID <pid>` from netstat output. Check for `wslrelay.exe` (Docker WSL relay) too. |
| Docker ghcr.io 500 | Skip Docker, use npm bundle |
| Token decode error | Set `security.jwtSecret` in config.json |
| Login fails but register works | Patch login.ts to search by username |
| CDN routes return 404 for all methods | CDN `start()` failed inside `Promise.all` — check for Monitoring metric registration errors. Fix: make `Monitoring.attach()` idempotent (try-catch around `new client.Counter`). |
| Avatar upload returns "Invalid /avatars/..." | CDN endpoint double-slash issue — remove trailing `/` from `cdn.endpointPrivate` in config. |
| Login returns token but then crashes with "URL constructor: undefined" | `instances.json` urls object is missing `"wellknown"` — add it set to the base server URL. |
| PostgreSQL auth fails | Use `127.0.0.1` instead of `localhost` in DATABASE URL (IPv6 vs IPv4 resolution on Windows). |

## Client Options

- **Fermo** (web client): https://github.com/MathMan05/Fermi
- **Spacebar React Client**: https://github.com/spacebarchat/client
- **Spacebar Explorer** (client list): https://spacebar-explorer.sovr.top/clients
- Any Discord-compatible client can connect with config pointing at localhost:3001
