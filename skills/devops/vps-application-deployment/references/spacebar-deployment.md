# Spacebar/Fermi Deployment on VPS

Spacebar (Discord-compatible backend) + Fermi (Harmony client) is a non-trivial deployment that differs from the standard Next.js pattern.

## Architecture

```
Browser → discy.your-domain.example
               ↓
          Caddy (Docker, port 80/443)
               ↓ (via handle/    handle @api)
          ┌────┴────┐
       Fermi UI   Spacebar API
      (port 8081) (port 3001/3100)
```

## Caddy Config (Docker)

The Caddy container (`caddy:2` image) needs multi-route config:

```caddy
discy.your-domain.example {
    encode gzip

    # Well-known auto-discovery
    @wellknown path /.well-known/spacebar*
    handle @wellknown {
        header Content-Type application/json
        respond {"api":"https://discy.your-domain.example/api/v9"}
    }

    # API + WebSocket proxying — preserve full path
    @api path /api/*
    handle @api {
        reverse_proxy 172.17.0.1:3100   # Spacebar API (not 3001 — port changed during VPS migration)
    }

    # Fermi UI — web client, everything that isn't /api/ or /.well-known/
    handle {
        reverse_proxy 172.17.0.1:8081
    }
}

# Optional: Fermi on a separate subdomain (e.g., gc.your-domain.example)
gc.your-domain.example {
    encode gzip
    reverse_proxy 172.17.0.1:8081   # Same Fermi UI, different subdomain
}
```

**Multi-domain pattern:** When Fermi gets its own subdomain (`gc.your-domain.example`), both `discy` and `gc` can proxy to the same Fermi backend. The `discy.your-domain.example` default handler also serves Fermi, so users can access the client from either domain. DNS must resolve both subdomains to the VPS IP.

**Key detail:** When Caddy is a Docker container, `172.17.0.1` is the Docker bridge gateway (the host). Use this to reach services running on the host or in other Docker networks.

## Running Spacebar

### Option A: Docker (recommended for VPS)

```yaml
# docker-compose.yml (partial)
services:
  spacebar:
    build: .
    container_name: spacebar
    ports: ["3001:3001"]
    environment:
      NODE_ENV: production
      PORT: "3001"
      DATABASE: postgres://spacebar_admin:***@postgres:5432/spacebar
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    mem_limit: 256m

  postgres:
    image: postgres:16-alpine
    container_name: spacebar-postgres
    environment:
      POSTGRES_USER: spacebar_admin
      POSTGRES_PASSWORD: ***
      POSTGRES_DB: spacebar
    volumes:
      - spacebar_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U spacebar_admin -d spacebar"]
    restart: unless-stopped
    mem_limit: 256m
```

### Option B: Native (local dev)

```bash
cd ${MY_REPOS}/spacebar
NODE_ENV=production PORT=3001 \
  DATABASE="postgres://spacebar_admin:***@127.0.0.1:5432/spacebar" \
  node --enable-source-maps dist/bundle/start.js
```

## SSH Tunnel Pattern (For Dev/Local Setup)

When running Spacebar locally but exposing it through a VPS:

```bash
ssh -i ~/.ssh/oracle_vps \
  -o StrictHostKeyChecking=no \
  -o ServerAliveInterval=60 \
  -o ExitOnForwardFailure=yes \
  -N -R 0.0.0.0:3001:localhost:3001 \
  ubuntu@129.153.156.190
```

This forwards VPS:3001 → localhost:3001. The Caddy config points to `172.17.0.1:3001` which routes through the tunnel.

## Config Files

Spacebar uses two config files:
- `config.json` — development defaults (port 3001)
- `config.production.json` — production overrides (port 3100, the operator branding)

**Important:** The `PORT` env var takes precedence over both config files. If your Caddy/SSH tunnel forwards a different port than what's in `config.production.json`, override with PORT env var.

## Migration Path: Local → VPS

1. Copy Spacebar code to VPS: `tar czf - ... | ssh ... tar xzf -`
2. Set up Docker Compose with PostgreSQL
3. Update Caddy config (if using Docker Caddy, target changes from SSH tunnel to `spacebar:3001` Docker service name)
4. Verify: `curl https://discy.your-domain.example/api/v9/auth/login` should return 401

## Common Pitfalls

- **Port mismatch:** Caddy config says `3001` but config.production.json says `3100` → set `PORT=3001` env var
- **Postgres auth:** Windows native PG uses trust auth for 127.0.0.1; Docker PG needs explicit password
- **Migration type:** From `DB_SYNC` → `APPLY_DB_MIGRATIONS` — if you switch, TypeORM may crash on already-existing tables. Set `APPLY_DB_MIGRATIONS=false` with native PG that already has schema.
- **Fermi UI needs separate service port** (8081) — not part of Spacebar itself
