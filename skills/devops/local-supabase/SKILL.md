---
name: local-supabase
version: 1.0.0
author: Hermes Agent
license: MIT
title: Local Supabase
description: Run a full Supabase stack locally with Docker Compose (GoTrue auth, PostgREST API, Kong gateway). For any dev project needing auth + SQL without a cloud dependency.
metadata:
  hermes:
    tags: [supabase, local-development, docker-compose, auth, postgres, database]
    triggers: [supabase-local-setup, local-auth, postgrest-api, supabase-docker, supabase-without-cloud, local-supabase, gotrue-auth]
    related_skills: [vps-application-deployment, vector-databases]
---

# Local Supabase

Run a full Supabase backend locally via Docker Compose. Includes GoTrue (auth), PostgREST (auto REST API), Kong (API gateway), Studio (admin UI), and postgres.

## Docker Compose Services

Minimal stack needs these services:
- **db** — Use `supabase/postgres:15.1.0.147` if using GoTrue (it has the `auth` schema extensions); use standard `postgres:15` if handling auth in-app
- **auth** — `supabase/gotrue:v2.163.1`. ⚠️ GoTrue migrations are untested on fresh DB — its `00_init_auth_schema.up.sql` creates tables but later migrations reference `auth.factor_type` which it creates in `public` schema (a GoTrue bug). Workaround options below.
- **postgrest** — `postgrest/postgrest:v12.2.x` (auto REST API over postgres)
- **kong** — `kong:3.4` (declarative config, routes `/auth/v1/` → auth, `/rest/v1/` → postgrest)
- **meta** — `supabase/postgres-meta` (DB introspection, needed by Studio)
- **studio** — `supabase/studio:latest` (admin UI, optional but handy)

## Key configuration

### GoTrue auth container
```
GOTRUE_API_HOST: 0.0.0.0
GOTRUE_API_PORT: 9999
GOTRUE_DB_DRIVER: postgres          # REQUIRED, often missed
GOTRUE_DB_DATABASE_URL: postgres://postgres:postgres@db:5432/postgres
GOTRUE_SITE_URL: http://localhost:PORT
GOTRUE_JWT_SECRET: super-secret-jwt-token-with-at-least-32-characters
GOTRUE_MAILER_AUTOCONFIRM: "true"   # Skip email confirmation in dev
API_EXTERNAL_URL: http://localhost:KONG_PORT/auth/v1   # NOT GOTRUE_API_EXTERNAL_URL
```

### Kong declarative config (`kong.yml`)
- Define `consumers` with `keyauth_credentials` for the anon + service_role keys
- Route `/auth/v1/` → `http://auth:9999`
- Route `/rest/v1/` → `http://postgrest:3000`
- Enable CORS plugin for localhost origins
- Standard local anon key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0`
- Standard local service_role key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJZDJ1M3GcP3E2cWGMJuDk7KQ2G3I0`
- JWT secret: `super-secret-jwt-token-with-at-least-32-characters`

### PostgREST
```
PGRST_DB_URI: postgres://postgres:postgres@db:5432/postgres
PGRST_DB_SCHEMA: public
PGRST_DB_ANON_ROLE: postgres       # Bypass RLS in dev
PGRST_JWT_SECRET: super-secret-jwt-token-with-at-least-32-characters
```

## Reference Files

Full working configs are in this skill's `references/` directory:
- `references/docker-compose.yml` — No-GoTrue variant (app-level auth) with port remapping
- `references/kong.yml` — Declarative config for Kong (rest-only, no auth routes)

### .env.local for Next.js
```
NEXT_PUBLIC_SUPABASE_URL=http://localhost:KONG_PORT
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key-jwt>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key-jwt>
```

## ⚠️ GoTrue Migration Pitfalls

GoTrue v2.163 has several issues when running on a fresh database:

**Issue 1: Missing `auth` schema.** GoTrue's first migration (`00_init_auth_schema.up.sql`) uses `CREATE TABLE IF NOT EXISTS {{ .Namespace }}.users` which fails if the `auth` schema doesn't exist. Fix: create the schema before GoTrue starts — either with `CREATE SCHEMA IF NOT EXISTS auth;` in the DB init migration or by using `supabase/postgres` image (which pre-creates it).

**Issue 2: `factor_type` enum created in `public` schema.** Migration `20221003041349_add_mfa_schema.up.sql` creates `factor_type AS ENUM('totp', 'webauthn')` *without* a schema prefix, so it lands in `public`. A later migration (`20240729123726_add_mfa_phone_config`) references `auth.factor_type`, causing a crash. Fix: pre-create `auth.factor_type` as an enum in the init migration.

**Issue 3: Backfill migration compares UUID = text.** Migration `20221208132122_backfill_email_last_sign_in_at.up.sql` does `WHERE id = user_id::text` on the `identities` table where `id` is `text`. If the table was created with `id` as UUID (from wrong schema state), this fails.

**Workaround A — Skip GoTrue entirely** (recommended for local dev):
- Remove GoTrue from the stack
- Implement auth in-app: verify passwords against the `users` table directly
- Use a simple session cookie (base64-encoded JSON) instead of Supabase sessions
- The app's middleware checks the cookie; the API route handles login
- This avoids all GoTrue migration issues

**Workaround B — Rescue GoTrue manually:**
In your DB init migration (runs before GoTrue connects), add:
```sql
CREATE SCHEMA IF NOT EXISTS auth;
DO $$ BEGIN
  CREATE TYPE auth.factor_type AS ENUM('totp', 'webauthn', 'phone');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  CREATE TYPE auth.factor_status AS ENUM('unverified', 'verified');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
  CREATE TYPE auth.aal_level AS ENUM('aal1', 'aal2', 'aal3');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
```

Also set `search_path` for the postgres user to `auth, public` so GoTrue finds its tables. But this only gets GoTrue partially running — some migrations may still fail.

## Auth Without GoTrue Pattern

When GoTrue is too problematic, implement auth directly in the app:

1. **Login route** (`POST /api/auth`): Verify email/password against the `users` table. Use the `service_role` key (via `@supabase/supabase-js`) to query `users`.
2. **Session**: Create a simple base64-encoded JSON token with `{sub, email, role, exp}`. Store it in a `session_token` cookie.
3. **Middleware**: Read the cookie, decode the payload, check expiry. Redirect to `/login` if missing or expired.
4. **Client-side hook**: Call `/api/auth` on mount with `action: "check_session"` to validate the cookie server-side.

## 🚨 Critical: `@supabase/supabase-js` + PostgREST = Broken Queries

The `@supabase/supabase-js` client sends BOTH `apikey` AND `Authorization: Bearer <key>` headers by default. PostgREST tries to validate the `Authorization` value as a JWT, and the local service_role key triggers `JWSError (JSONDecodeError "Not valid base64url")`. This causes **every query to silently fail** — auth returns "User not found", data queries return empty arrays.

**Fix: Never use `@supabase/supabase-js` client with a local PostgREST. Always use raw `fetch()` with only `apikey`.**

```typescript
// ✅ CORRECT — raw fetch, just apikey
const SRV = '<service-role-key>';
async function pg(method: string, path: string, body?: any) {
  const res = await fetch(`http://localhost:PORT/rest/v1${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', apikey: SRV },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.status === 204 ? null : JSON.parse(await res.text());
}

// ❌ WRONG — Supabase client sends Authorization header, breaks PostgREST
const supabase = createClient(url, key);
const { data } = await supabase.from('users').select('*'); // ← FAILS SILENTLY
```

This applies to:
- `lib/data-service.ts` — server-side CRUD (all route handlers)
- `scripts/seed-*.js` — seed scripts
- `app/api/auth/route.ts` — login and session check
- Any file that queries the local PostgREST

If you use `@supabase/supabase-js` on the client-side (browser), it's fine — the browser sends requests through Kong which validates the apikey and routes to GoTrue (not PostgREST). The `Authorization` header issue only affects server-side PostgREST queries.

## Debugging auth failures

When `POST /api/auth` returns 401 ("Invalid credentials" or "User not found") after everything is configured:

```
1. Test PostgREST directly:
   curl -s "http://localhost:PORT/rest/v1/users?email=eq.admin@demo.com" \
     -H "apikey: <service-role-key>"
   # If this returns data → PostgREST is fine, bug is in your app code
   # If this returns 401 → check Kong/apikey
   # If this returns "Not valid base64url" → you sent Authorization: Bearer, use raw fetch

2. Test your app code via node -e:
   node -e "
   const r = await fetch('http://localhost:PORT/rest/v1/users?email=eq.admin@demo.com', {
     headers: {'apikey':'<key>'}
   });
   console.log(r.status, await r.text());
   " --input-type=module
   # If this works but the file doesn't → env var / module type issue

3. Compare file vs -e results:
   - File works, -e fails? → Check absolute/relative paths, CWD, import syntax
   - -e works, file fails? → Module type mismatch, env var override, or file encoding issues
```

**Common gotchas in this flow:**
- **ESM/CommonJS mismatch**: If `package.json` lacks `"type": "module"` but the script uses `import` syntax, Node re-parses with a warning. This can cause subtle runtime differences. Fix: either add `"type": "module"` to package.json, or write scripts as CommonJS (`require`, `module.exports`).
- **Module-level code vs function scope**: The key variable might be module-scoped and accessible in the seed function's closure, but if the script is running as ESM-with-warning, variable initialization order changes.
- **`write_file` truncation**: If the key in the file contains literal `...` (three dots) instead of the full JWT, the `write_file` tool truncated the parameter. Verify with `grep -c "eyJ" file.js` (counts occurrences) or `node -e "process.exit(require('fs').readFileSync('file.js','utf8').match(/'([^']{150,})'/)?.[1].length)"` to check actual key length.

## 🚨 Stale Environment Variable Pitfall

System-level or shell-level env vars can silently override fallback keys in scripts. If `SUPABASE_SERVICE_ROLE_KEY` is set (even to a truncated value), Node.js scripts using `process.env.SUPABASE_SERVICE_ROLE_KEY || '<fallback>'` will use the stale truncated key, causing "Invalid authentication credentials" (401) from Kong. The truncation can happen from:
- A previous `write_file` call where the key appeared as `eyJhbG...G3I0` in the tool parameter display — write_file writes the literal parameter value, so the abbreviated version ends up on disk
- A system env var set by Docker Desktop or another process

**Fix**: `unset SUPABASE_SERVICE_ROLE_KEY` at the top of startup scripts, or embed the key literally in files without env var fallback. When writing files that contain long keys, write them via `terminal` using `cat` or `sed` instead of `write_file` to avoid parameter truncation. Better yet, verify the key length after writing: `grep -c "eyJh" file.js` should match the expected count, and the file should contain the full JWT (no literal `...` in the string).

## Kong YAML Pitfalls

Kong 3.x declarative config (`kong.yml`) has strict YAML formatting requirements:

**CORS `headers`**: Must be a YAML array of strings:
```yaml
plugins:
  - name: cors
    config:
      headers:
        - Accept
        - Authorization
        - Content-Type
        - apikey
```

**`request-transformer` `config.add.headers`**: Must use string format `"Header-Name: value"`, not YAML key/value:
```yaml
# ✅ CORRECT
  - name: request-transformer
    config:
      add:
        headers:
          - "Accept: application/json"
```
```yaml
# ❌ WRONG — creates object instead of string
  - name: request-transformer
    config:
      add:
        headers:
          - Accept: application/json
```

### PostgREST for Local Dev

For local development, bypass RLS by setting:
```yaml
PGRST_DB_ANON_ROLE: postgres
```
This makes all requests (even unauthenticated ones) run as the `postgres` superuser, bypassing row-level security. Remove this for staging/production.

⚠️ The `@supabase/supabase-js` client sends `Authorization: Bearer <key>` which PostgREST tries to validate as a JWT. The local service_role JWT fails base64url validation. **Always use raw `fetch()` with only the `apikey` header** for server-side operations, or configure the Supabase client to not send the `Authorization` header.

### 🚨 PostgREST Direct (Port 54324) vs Kong (Port 44444)

When Kong's `key-auth` is broken (truncated placeholder API keys in `kong.yml`), bypass it and connect directly to PostgREST on port **54324** (default Docker compose mapping):

```typescript
// ✅ Direct PostgREST (no Kong) — for when Kong key-auth is unreliable
const API = 'http://localhost:54324'  // NOT localhost:44444/rest/v1/
const SRV = '' // apikey not needed when PGRST_DB_ANON_ROLE = postgres

async function pg(method: string, path: string, body?: any) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  // CRITICAL: PostgREST returns 201 with NO response body for POST by default.
  // Without this header, createProject() returns null even when it succeeded.
  if (method === 'POST') headers['Prefer'] = 'return=representation'

  const res = await fetch(`${API}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const text = await res.text()
    console.error(`[pg] ${method} ${path}: ${res.status} ${text}`)
    return null
  }
  const text = await res.text()
  return text ? JSON.parse(text) : null
}
```

**Key differences from Kong-based approach:**
- PostgREST direct serves at `/users`, `/projects`, etc. — **no `/rest/v1/` prefix**
- No `apikey` header needed when `PGRST_DB_ANON_ROLE = postgres` (all requests run as superuser)
- Kong's CORS, rate limiting, and routing are bypassed — only use this for local dev
- The `/api/setup` route must return `{ configured: true }` so client hooks don't fall back to demo mode

### 🚨 PostgREST POST: Prefer: return=representation

PostgREST's default POST behavior is HTTP 201 with **no response body**. If your data-service layer calls PostgREST POST and then checks the response:

```typescript
const result = await pg('POST', '/projects', { name: '...' })
// result is null even though the project was created!
```

Add `Prefer: return=representation` to the POST request headers to get the created record in the response body:

```typescript
if (method === 'POST') headers['Prefer'] = 'return=representation'
```

Without this header, any code that checks `if (!data) { /* failed */ }` will report failure on success — the record IS created but the response body is empty. This can cause confusing bugs where creating something appears to fail (error toast shown) but the data actually exists in the database.

### 🚨 PostgREST DATE NOT NULL Constraints

Columns declared as `DATE NOT NULL` reject **empty strings** `''` with error `invalid input syntax for type date: ""`. This often happens in create functions where date fields default to `''`:

```typescript
// ❌ BROKEN — PostgREST returns 400: invalid input syntax for type date
createProject({ start_date: '', estimated_completion: '', ... })

// ✅ CORRECT — provide computed defaults
createProject({
  start_date: args.start_date || new Date().toISOString().split('T')[0],
  estimated_completion: args.estimated_completion ||
    new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
  ...
})
```

Always provide sensible default dates in data-service create functions. The exact same pitfall applies to GoTrue auth tables and any other schema with `DATE NOT NULL` columns that lack `DEFAULT` clauses.

### 🚨 Killing Demo Mode in Next.js Apps

When client-side hooks check `api.setup.check()` (or similar) to decide between real API data and hardcoded demo/mock data, the response must include a `configured: true` field:

```typescript
// app/api/setup/route.ts — MUST return configured: true
export async function GET() {
  try {
    const stats = await getDbStats()
    return NextResponse.json({
      status: 'ok',
      configured: true,  // ← THIS field is what hooks check
      database: 'Local Supabase',
      stats,
    })
  } catch {
    return NextResponse.json({ status: 'error', configured: false })
  }
}
```

The client-side hooks (e.g. `useAdminData`, `useDashboardData`) typically do:
```typescript
const setupCheck = await api.setup.check()
if (!setupCheck.success || !setupCheck.data?.configured) {
  // Falls back to DEMO/MOCK data — you NEVER see real data
  return
}
```

If `configured` is missing or `false`, the app silently serves demo data despite a healthy database connection. Verify by checking the raw response of `/api/setup` — it should include `"configured": true` at the top level.

## Schema

Use either `postgres:15` (for app-level auth) or `supabase/postgres:15.1.0.147` (if using GoTrue). The Supabase image has pre-installed extensions (pg_cron, pgaudit) and sets up internal infrastructure, but its init scripts can conflict with user migrations.

Key differences:
- **`postgres:15`**: Clean PostgreSQL. Use `gen_random_uuid()` instead of `uuid_generate_v4()` (built-in since pg 13, no extension needed). No `auth` schema. No `auth.uid()` RLS function.
- **`supabase/postgres:15.1.0.147`**: Supabase-specific image with extensions plus internal roles/schemas. The `auth` schema is NOT auto-created despite the name — user migration must do it. Has `supabase_admin` role for extension management.

The `auth.uid()` function for RLS policies is NOT available with plain postgres — either define it yourself or use `service_role` key server-side.

## Supabase CLI: Container Conflict Recovery

When `supabase start` fails with:
```
failed to create docker container: Error response from daemon: Conflict.
The container name "/supabase_<service>_BookEnds" is already in use
```

Or when services show as "Stopped" after a partial start (interrupted by timeout):

```bash
# 1. Full stop with backup purge (data-safe if you want fresh)
npx supabase stop --no-backup

# 2. Verify no orphaned containers remain
docker ps -a --filter "name=supabase" --format "{{.Names}}"

# 3. If orphaned containers from a different supabase run exist (different naming pattern):
docker rm -f <container-name>

# 4. Start fresh
npx supabase start
```

**Root cause:** First-run `supabase start` pulls Docker images then initialises the schema, which can take 5+ minutes. If the command times out (300s default), containers are orphaned and block subsequent starts with "name already in use" errors.

**First-run timing:** Pulling all Supabase Docker images (postgres, auth, kong, rest, realtime, storage, studio, etc.) takes 2-4 minutes on first run. Schema initialisation with migrations adds another 30-90 seconds. Set command timeout to at least 300s for first `supabase start`.

**Prevention:** After the initial full pull and schema init, subsequent `supabase start` calls complete in seconds. Use `supabase stop --no-backup` before restarting to avoid orphan conflicts.

Docker Desktop for Windows can hold ports in a proxy cache even after containers are removed. If `docker compose up -d` fails with `Bind for 0.0.0.0:XXXXX failed` and nothing is actually listening (netstat shows no LISTEN on that port):
1. Kill all stale containers: `docker rm -f $(docker ps -aq --filter "name=supabase")`
2. Remove networks/volumes: `docker network prune -f && docker volume rm <volume>`
3. **Restart Docker Desktop** — this clears the proxy cache (`"C:\Program Files\Docker\Docker\Docker Desktop.exe" --restart`)
4. If still failing, remove `127.0.0.1:` prefix from port bindings (use bare `"XXXXX:8000"` instead)
5. Choose a port never used before to avoid TIME_WAIT conflicts

## Production same-origin behind Traefik (`*.your-domain.example`)

When exposing a local Supabase CLI project on a public subdomain (e.g. BookEnds):

1. Keep `npx supabase start` running (`supabase_network_<Project>`).
2. Put a thin reverse proxy on **three** networks: app, `backend_edge`, `supabase_network_<Project>`.
3. Set `NEXT_PUBLIC_SUPABASE_URL=https://<sub>.your-domain.example` (not `127.0.0.1:54321`) and rebuild the Next image so the client uses same-origin `/auth` `/rest` etc.
4. Proxy Kong paths from the domain to `supabase_kong_<Project>:8000`.

Full checklist: skill `backus-agency-edge-deploy` + `references/bookends-traefik-bringup.md`.

## Next.js Integration

When using local Supabase with a Next.js project, the workflow adds project-specific steps.

### End-to-End Setup

```bash
# 1. Clone & install
gh repo clone <org>/<repo>
cd <repo>
npm install

# 2. Start Supabase (if not already running)
cd /path/to/project  # must have supabase/config.toml
npx supabase start   # timeout=300 for first run (pulls images)
# First run downloads ~15 Docker images (~1.5GB), takes 3-5 min

# 3. Capture keys from `npx supabase start` output:
#    Project URL → NEXT_PUBLIC_SUPABASE_URL
#    anon key    → NEXT_PUBLIC_SUPABASE_ANON_KEY
#    service_role→ SUPABASE_SERVICE_ROLE_KEY

# 4. Configure environment
cp .env.template .env.local
# Edit .env.local:
# NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
# NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key>
# SUPABASE_SERVICE_ROLE_KEY=<service-role-key>

# 5. Build & serve
npx next build
npx next start -p 3090
# OR for dev (hot reload):
npx next dev -p 3090
```

### Environment Variable Precedence

⚠️ System-level env vars silently override `.env.local` in Next.js. If `NEXT_PUBLIC_SUPABASE_URL` is set at the system level (Windows env vars), Next.js inlines the system value at compile time. Verify with:
```bash
grep "SUPABASE_URL" .next/static/chunks/app/*.js | head -5
```

### Port Conflicts on Windows

When a port is already in use (Next.js, Supabase services, or Docker), free it:
```bash
netstat -ano | grep :PORT
taskkill //F //PID <pid>  # MSYS: double-slash to avoid path conversion
```

### Common Next.js Pitfalls

- **Duplicate `paths` key in `tsconfig.json`**: Next.js SWC compiler chokes with confusing "Failed to read source code" error. Keep only one `compilerOptions.paths` entry.
- **Dev server chunk compilation race**: After `rm -rf .next && npx next dev`, JS/CSS chunks compile lazily. The HTML shell returns 200 but referenced chunks 404 until webpack finishes. Warm up chunks before testing: `for page in "/login" "/dashboard"; do while [ "$(curl -s -o /dev/null -w '%{http_code}' localhost:PORT$page)" != "200" ]; do sleep 3; done; done`
- **Port conflicts**: Check with `netstat -ano | grep :PORT`. Use `taskkill //F //PID` on Windows/git-bash.
- **Dev server output may buffer in git-bash**: Use `next start` (production) instead — output appears immediately. Build first with `next build`.
- **`.next/` cache is branch/environment-specific**: After swapping env vars, always rebuild: `npx next build`.
- **Standalone output**: `output: 'standalone'` in `next.config` is for Docker — doesn't affect local dev.

### Supabase CLI Migration Commands

```bash
npx supabase db push              # Apply pending migrations
npx supabase db reset             # Drop all data and re-run migrations
npx supabase migration list       # List migration status
npx supabase migration new <desc> # Create a new migration
```

## Migrating from JSON file to Supabase

When replacing a JSON-file data service with Supabase:
1. Keep all function signatures identical — the API routes just `await` the result
2. Use `service_role` key server-side (bypasses RLS for CRUD)
3. Handle integer-ID → UUID transition: regenerate UUIDs from a deterministic namespace
4. Seed from old JSON: create auth users first via GoTrue admin API, then insert data with matching UUIDs
5. Remove `parseInt()` calls from API routes — query params are already strings
