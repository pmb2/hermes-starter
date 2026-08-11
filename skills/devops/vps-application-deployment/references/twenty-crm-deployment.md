# Twenty CRM Deployment Guide

Twenty CRM is a NestJS + React app deployed via Docker Compose behind Traefik. This covers application-level configuration beyond the infrastructure layer (see parent skill for Traefik, SSL, and Docker basics).

## Env Vars That MUST Be Set

Twenty CRM's NestJS server validates environment variables strictly at startup. Missing or blank values cause `ConfigVariableException` and the process exits.

### Critical (Server Won't Start Without)

```
TWENTY_DB_USER=twenty
TWENTY_DB_PASSWORD=twenty
TWENTY_DB_NAME=twenty
POSTGRES_SUPERUSER=postgres
POSTGRES_SUPERUSER_PASSWORD=postgres
```

These are used by the `PG_DATABASE_URL` template in compose.yaml:
```yaml
PG_DATABASE_URL: postgres://${TWENTY_DB_USER}:${TWENTY_DB_PASSWORD}@postgres:5432/${TWENTY_DB_NAME}
```

If any is blank, `psql` in the entrypoint prompts for a password and the server can't connect.

### Booleans (Must Be `true` or `false`, Not Blank)

Twenty validates these as strict booleans:

```yaml
AUTH_GOOGLE_ENABLED: ${TWENTY_AUTH_GOOGLE_ENABLED:-false}
CALENDAR_PROVIDER_GOOGLE_ENABLED: ${TWENTY_CALENDAR_PROVIDER_GOOGLE_ENABLED:-false}
MESSAGING_PROVIDER_GMAIL_ENABLED: ${TWENTY_MESSAGING_PROVIDER_GMAIL_ENABLED:-false}
```

**Fix:** Always use `:-false` defaults in compose.yaml. Do NOT leave them as bare `${VAR}` — the empty string fails NestJS validation.

### REDIS_URL Must Be a Valid URL

```yaml
REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/1
```

- If Redis has `requirepass "${REDIS_PASSWORD}"` and the password is set, REDIS_URL needs the password in the URL
- If Redis has no password, use `redis://redis:6379/1` (no colon before `@`)
- Twenty's validation rejects `redis://:@redis:6379/1` (empty password with colon)

### APP_SECRET Needs a Fallback

```yaml
APP_SECRET: ${TWENTY_APP_SECRET:-change-me-to-real-secret}
```

The app secret is used for encryption and signing. Use `:-default` so the server starts even if the var isn't in .env.

## Multi-Workspace vs Single-Workspace

### The `.crm.your-domain.example` Redirect

When `IS_MULTIWORKSPACE_ENABLED=true` and `DEFAULT_SUBDOMAIN=""` is empty:

1. Twenty shows a workspace selection page at the root domain
2. When a workspace is selected (or auto-selected), Twenty redirects to `https://{subdomain}.{frontDomain}`
3. If `subdomain` is empty or the default workspace subdomain has no DNS record, the browser navigates to an invalid URL

**Symptom:** Browser shows "This site can't be reached" with URL `https://.crm.your-domain.example` (leading dot)

**Fix options:**

**Option A — Single workspace (no subdomain redirect):**
```yaml
IS_MULTIWORKSPACE_ENABLED: "false"
```
This keeps Twenty on the root domain without any subdomain redirect. All workspaces remain accessible via the root domain.

**Option B — Wildcard DNS + subdomain routing:**
Add `*.crm.your-domain.example` A record to your DNS, and add wildcard routing in Traefik:
```yaml
traefik.http.routers.twenty.rule=Host(`crm.your-domain.example`) || HostRegexp(`{subdomain:[a-z]+}.crm.your-domain.example`)
```

**Option C — Explicit default subdomain:**
```yaml
DEFAULT_SUBDOMAIN: "backus"
```
Only works if `backus.crm.your-domain.example` resolves in DNS and Traefik routes it.

### Multi-Workspace Troubleshooting

Check existing workspaces:
```bash
docker exec <twenty-container> sh -c "psql \"\$PG_DATABASE_URL\" -c 'SELECT id, \"displayName\", subdomain FROM core.workspace;'"
```

If a workspace's `subdomain` field doesn't match any DNS record, the JS frontend will try to navigate there and fail. Either add the DNS record or set `IS_MULTIWORKSPACE_ENABLED=false`.

## Entrypoint Script — CRLF Line Endings

Twenty's entrypoint script (`twenty-entrypoint.sh`) is a shell script that runs `set -e`, database migrations, and background job registration.

**If this script has CRLF (`\r\n`) line endings** (common when edited on Windows), the container crash-loops with:

```
/opt/agency/twenty-entrypoint.sh: set: line 2: illegal option -
```

**Fix:**
```bash
# Convert to Unix line endings
sed -i 's/\r$//' scripts/twenty-entrypoint.sh
# Recreate the container to pick up the fixed file (it's bind-mounted)
docker compose --profile light up -d --no-deps --force-recreate agency-twenty
```

The entrypoint is typically mounted from the host:
```yaml
volumes:
  - ./scripts/twenty-entrypoint.sh:/opt/agency/twenty-entrypoint.sh
```

So fixing it on the host and recreating the container is enough — no image rebuild needed.

## Rebuilding the Twenty Image

Twenty's Dockerfile uses `REACT_APP_SERVER_BASE_URL` as a **build arg**, baked into the compiled frontend JS:

```dockerfile
ARG REACT_APP_SERVER_BASE_URL
ENV REACT_APP_SERVER_BASE_URL=$REACT_APP_SERVER_BASE_URL
```

If you change the domain, you MUST rebuild the image:
```bash
docker compose --profile light build agency-twenty
docker compose --profile light up -d --no-deps --force-recreate agency-twenty
```

**Build takes 2-5 minutes** (clones Twenty source, installs deps, builds server + frontend). Run in background:
```bash
docker compose --profile light build agency-twenty  # ~300s
```

## Database State

Twenty stores its data in PostgreSQL. The database persists across container recreations via a Docker volume.

- **Existing workspaces, users, and data survive** container recreation as long as the postgres container and volume are intact
- **Database migrations run automatically** on every startup (in the entrypoint's `setup_and_migrate_db` function)
- **No migrations pending** means the schema matches the current version

## Common Startup Sequence Logs

Successful startup produces:
```
[Nest] LOG [DatabaseConfigDriver] [INIT] Config variables loaded: N values found in DB, M falling to env vars/defaults
[Nest] LOG [NestApplication] Nest application successfully started
```

Followed by call UI augmentation (if configured):
```
Installing Twenty call UI augmentation...
```

## Quick Verification

```bash
# Server is serving
curl -sk https://crm.your-domain.example | grep -o '<title>[^<]*</title>'
# → <title>Twenty</title>

# Client config
curl -sk https://crm.your-domain.example/client-config | python -c "import sys,json; d=json.load(sys.stdin); print('frontDomain:', d['frontDomain'], 'multi:', d['isMultiWorkspaceEnabled'])"
```
