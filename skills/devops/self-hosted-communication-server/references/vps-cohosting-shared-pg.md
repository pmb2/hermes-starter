# Spacebar + Fermi VPS Co-Hosting (Shared PostgreSQL)

When deploying Spacebar to an existing VPS that already runs PostgreSQL for another app (e.g., Hamilton Web App), use the **shared PostgreSQL** pattern to conserve memory.

## Architecture

```
Browser → https://spacebar.your.domain
              ↓
          Caddy (existing on VPS)
           ├── /api/* → :3001 → Spacebar (Docker or native)
           ├── /.well-known/spacebar* → returns {api: "..."}
           └── /* → :8081 → Fermi (Docker or native)
                                 ↓
                          PostgreSQL (existing, port 5432)
                           ├── existing_app_db
                           └── spacebar_db (new, schema already migrated)
```

## Prerequisites

- VPS with Docker + Caddy already running (e.g., from another web app deployment)
- Caddy already configured to proxy at least one domain
- PostgreSQL already running (for another app)
- DNS A record for the Spacebar domain pointing to the VPS IP

## Step 1: Create Spacebar Database in Existing PostgreSQL

Don't run a separate PostgreSQL container. Create a database in the existing one:

```bash
# On the VPS
sudo -u postgres psql << 'SQL'
CREATE DATABASE spacebar;
CREATE USER spacebar_admin WITH PASSWORD 'your_generated_password';
GRANT ALL PRIVILEGES ON DATABASE spacebar TO spacebar_admin;
\c spacebar
GRANT ALL ON SCHEMA public TO spacebar_admin;
SQL

# Verify
psql -U spacebar_admin -d spacebar -c '\l'
```

## Step 2: Build Spacebar Docker Image on VPS

```bash
# Clone or copy spacebar to VPS
git clone https://github.com/your-org/spacebar.git /opt/spacebar
cd /opt/spacebar

# Build the Docker image (or use the existing Dockerfile)
docker build -t spacebar-server -f Dockerfile .
```

**⚠️ Memory during build:** Docker build can spike memory usage. On a 1GB VPS, a TypeScript build + schema generation may push into swap territory. Consider:
- Building locally and transferring the image: `docker save spacebar-server | gzip | ssh ... "gunzip | docker load"`
- Or building on the VPS during low-usage periods

## Step 3: Create Docker Compose for Spacebar (Postgres-optional)

Don't include PostgreSQL in the compose file — use external connection:

```yaml
services:
  spacebar:
    image: spacebar-server
    container_name: spacebar
    restart: unless-stopped
    ports:
      - "3001:3001"
    environment:
      NODE_ENV: production
      PORT: 3001
      CONFIG_PATH: /app/config.production.json
      DATABASE: postgres://spacebar_admin:***@172.17.0.1:5432/spacebar
      APPLY_DB_MIGRATIONS: "false"
    volumes:
      - ./config.production.json:/app/config.production.json:ro
    mem_limit: 256m
    memswap_limit: 512m
    networks:
      - backend_edge

networks:
  backend_edge:
    external: true
    name: backend_edge
```

**⚠️ Pitfall — `host.docker.internal` on Linux:** This DNS name only works on Docker Desktop (Mac/Windows). On a Linux VPS, use `172.17.0.1` (Docker bridge gateway) or the host's private IP.

## Step 4: Create config.production.json with HTTPS Endpoints

```json
{
  "general": {
    "instanceName": "Your Spacebar",
    "serverName": "spacebar.your.domain",
    "correspondenceEmail": "admin@your.domain"
  },
  "api": {
    "endpointPublic": "https://spacebar.your.domain/api/v9",
    "endpointPrivate": "https://spacebar.your.domain/api/v9",
    "defaultVersion": "9",
    "activeVersions": ["6","7","8","9"]
  },
  "cdn": {
    "endpointPublic": "https://spacebar.your.domain",
    "endpointPrivate": "https://spacebar.your.domain"
  },
  "gateway": {
    "endpointPublic": "wss://spacebar.your.domain/",
    "endpointPrivate": "wss://spacebar.your.domain/"
  },
  "security": {
    "jwtSecret": "your-generated-64-char-hex",
    "requestSignature": "your-request-signature-key"
  },
  "register": {
    "disabled": false,
    "requireCaptcha": false,
    "requireInvite": false,
    "email": { "required": false },
    "dateOfBirth": { "required": false }
  },
  "limits": {
    "rate": { "enabled": false },
    "absoluteRate": { "register": { "limit": 1000, "enabled": false } }
  }
}
```

## Step 5: Add Caddy Route to Existing Caddyfile

Append to the existing Caddyfile (system `/etc/caddy/Caddyfile` or user `~/Caddyfile`):

```
spacebar.your.domain {
  encode gzip

  @wellknown path /.well-known/spacebar*
  handle @wellknown {
    header Content-Type application/json
    respond {"api":"https://spacebar.your.domain/api/v9"}
  }

  @api path /api/*
  handle @api {
    reverse_proxy 172.17.0.1:3001
  }

  handle {
    reverse_proxy 172.17.0.1:8081
  }
}
```

**⚠️ handle vs handle_path:** Using `handle_path /api/*` strips the `/api` prefix before proxying — Spacebar receives `/v9/auth/login` instead of `/api/v9/auth/login`. Use `handle @api path /api/*` with plain `reverse_proxy`.

**Reload:**
```bash
sudo systemctl reload caddy   # system-level Caddy
docker exec hmac-caddy caddy reload --config /etc/caddy/Caddyfile   # Docker Caddy
```

## Step 6: Verify

```bash
# Direct to Spacebar container
curl -s -o /dev/null -w "%{http_code}" http://localhost:3001/api/v9/gateway
# → 200

# Through Caddy/SSL
curl -s https://spacebar.your.domain/api/v9/gateway
# → {"url":"wss://spacebar.your.domain/"}
```

## Resource Budget (1GB VPS with Existing Web App)

| Component | Memory |
|-----------|--------|
| Caddy (existing) | ~20MB |
| PostgreSQL (shared, existing) | ~100-150MB |
| Web app frontend (existing) | ~20-50MB |
| Spacebar (Docker) | ~100-200MB |
| Fermi (Docker or native) | ~20-50MB |
| **Total additional** | **~120-250MB** |

With ~445MB available on a typical Oracle free tier AMD VPS (956MB total), this leaves ~200-325MB headroom. **Workable for light usage.** Add swap (2GB) as OOM safety net before deploying.
