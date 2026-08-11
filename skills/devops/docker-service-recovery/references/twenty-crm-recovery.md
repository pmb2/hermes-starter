# Twenty CRM Docker Recovery — Reference

## Deployment Context

- **Project name**: `agency-stack` (from `docker compose --project-name`)
- **Compose file**: `ghl/compose.yaml` (included from root `docker-compose.yml`)
- **Service**: `agency-twenty` → container `agency-stack-agency-twenty-1`
- **Image**: `agency-twenty-custom:v1.19.0-leads.1` (custom build from `ghl/twenty-custom/Dockerfile`)
- **Reverse proxy**: Traefik (standalone container) — NOT part of the agency-stack compose

## The Three Fixes Applied

### Fix 1: Invalid UUID v4 IDs
**Problem:** Builder companies imported with sequential IDs like `a0000001-0000-0000-0000-000000000001`. These ARE valid UUID format, but Twenty CRM's GraphQL layer (`@graphql-tools/executor`) rejects them — it requires RFC 4122 v4 format.

**Error:** `Error: Invalid UUID: 'a0000001-0000-0000-0000-000000000011'` during `FindManyCompanies` query.

**Fix:** Delete and re-insert with `gen_random_uuid()`:
```sql
DELETE FROM workspace_{schema}.company WHERE id::text LIKE 'a0000001-0000-0000-0000-0000000000%';
INSERT INTO workspace_{schema}.company (id, name, position) VALUES (gen_random_uuid(), 'Name', 1);
```

### Fix 2: IS_MULTIWORKSPACE_ENABLED must match workspace count
**Problem:** `IS_MULTIWORKSPACE_ENABLED=false` but DB had 2 workspaces (<you> + Job Agent). Twenty CRM logs a warning and falls back to "Apple seed workspace" which doesn't exist → crash after login.

**Error:** `WARN  2 workspaces found in database. In single-workspace mode, there should be only one workspace. Apple seed workspace will be used as fallback if it found.`

**Fix Options:**
- **A** (chosen): Delete extra workspace → `IS_MULTIWORKSPACE_ENABLED=false` works cleanly
- **B**: `IS_MULTIWORKSPACE_ENABLED=true` → but causes subdomain redirect to `{subdomain}.domain`

**Workspace deletion steps:**
```sql
-- 1. Find workspace id
SELECT id, "displayName", subdomain FROM core.workspace;

-- 2. Delete from core tables
DELETE FROM core."userWorkspace" WHERE "workspaceId" = '<id>';
DELETE FROM core.view WHERE "workspaceId" = '<id>';
DELETE FROM core."objectMetadata" WHERE "workspaceId" = '<id>';
DELETE FROM core."fieldMetadata" WHERE "workspaceId" = '<id>';
DELETE FROM core.workspace WHERE id = '<id>';

-- 3. Drop the workspace schema
DROP SCHEMA "workspace_{schema}" CASCADE;
```

### Fix 3: DEFAULT_SUBDOMAIN subdomain redirect
**Problem:** With `IS_MULTIWORKSPACE_ENABLED=true` and `DEFAULT_SUBDOMAIN=youragency`, Twenty CRM redirects to `youragency.crm.your-domain.example`. The DNS/wildcard for `*.crm.your-domain.example` doesn't resolve, so the page doesn't load.

**Fix:** Switch to single-workspace mode (`IS_MULTIWORKSPACE_ENABLED=false`) with only one workspace. No subdomain redirect needed.

## Network Topology

```
                     ┌─────────────────────┐
                     │      Traefik         │
                     │  backend_core        │
                     │  backend_edge        │
                     └────────┬────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
  ┌──────┴──────┐   ┌────────┴────────┐   ┌───────┴───────┐
  │ agency-twenty │   │ agency-ollama   │   │ agency-...    │
  │ agency-stack_ │   │ agency-stack_   │   │               │
  │ core          │   │ core            │   │               │
  │ backend_core  │   │ backend_core    │   │               │
  └──────┬───────┘   └─────────────────┘   └───────────────┘
         │
  ┌──────┴───────┐
  │ Postgres      │
  │ (agency-stack_│
  │  core)        │
  └──────────────┘
```

**Key insight:** Containers must be on **BOTH**:
- `agency-stack_core` (compose internal network for DB/Redis)
- `backend_core` (Traefik's network for routing)

## Database Access

```bash
# Main Twenty DB
docker exec agency-stack-postgres-1 psql -U twenty twenty

# Available schemas
# - core (shared metadata: user, workspace, objectMetadata, view, etc.)
# - workspace_{hash} (per-workspace data: company, person, opportunity, etc.)

# List workspaces
SELECT id, "displayName", subdomain FROM core.workspace;

# Check user workspace membership
SELECT u.email, w."displayName" FROM core."userWorkspace" uw
  JOIN core."user" u ON uw."userId" = u.id
  JOIN core."workspace" w ON uw."workspaceId" = w.id
  WHERE u.email = '<email>';
```

## Docker Run Template (for this service)

```bash
export MSYS_NO_PATHCONV=1
docker run -d \
  --name agency-stack-agency-twenty-1 \
  --network agency-stack_core \
  --network backend_core \
  --restart unless-stopped \
  --entrypoint /bin/sh \
  -v "${MY_REPOS}/Documents/github/ghl/scripts/twenty-entrypoint.sh:/opt/agency/twenty-entrypoint.sh:ro" \
  -v "${MY_REPOS}/Documents/github/ghl/overrides/twenty-call-ui/twenty-call-ui.js:/opt/agency/twenty-call-ui.js:ro" \
  -l "com.docker.compose.project=agency-stack" \
  -l "com.docker.compose.service=agency-twenty" \
  -l "traefik.enable=true" \
  -l "traefik.docker.network=backend_core" \
  -l "traefik.http.routers.agency-twenty.entrypoints=websecure" \
  -l "traefik.http.routers.agency-twenty.rule=Host(\`crm.your-domain.example\`)" \
  -l "traefik.http.routers.agency-twenty.tls=true" \
  -l "traefik.http.routers.agency-twenty.tls.certresolver=letsencrypt" \
  -l "traefik.http.services.agency-twenty.loadbalancer.server.port=3000" \
  -e "NODE_ENV=production" \
  -e "NODE_PORT=3000" \
  -e "SERVER_URL=https://crm.your-domain.example" \
  -e "PG_DATABASE_URL=postgres://twenty:twenty@postgres:5432/twenty" \
  -e "REDIS_URL=redis://:redis@redis:6379/1" \
  -e "APP_SECRET=change-me-to-real-secret" \
  -e "IS_MULTIWORKSPACE_ENABLED=false" \
  -e "DISABLE_DB_MIGRATIONS=true" \
  -e "DISABLE_CRON_JOBS_REGISTRATION=true" \
  --network-alias twenty \
  agency-twenty-custom:v1.19.0-leads.1 \
  /opt/agency/twenty-entrypoint.sh node dist/main
```
