# Docker Compose + Traefik Deployment

Deploying multi-service Docker Compose stacks behind a Traefik reverse proxy with Let's Encrypt TLS. This covers the common pattern where Traefik runs as a standalone container (often in a separate compose project like `n8n/docker-compose.yml`) and your application stack registers its services with it via Docker labels.

## Core Architecture

```
┌─────────────────────────────────────────────┐
│  Traefik (port 80 → 443)                    │
│  ACME: letsencrypt, HTTP-01 challenge       │
│  Provider: Docker (exposedbydefault=false)   │
├─────────────────────────────────────────────┤
│  Docker Network:  backend_core (shared)      │
├────────────┬────────────────────┬────────────┤
│  app-stack │  another-stack     │  n8n-stack │
│  (agency)  │  (reseller-os)     │  (traefik) │
└────────────┴────────────────────┴────────────┘
```

## Env Var Interpolation Gotchas

### The `.env` file is your Single Source of Truth

Docker Compose auto-reads a `.env` file from the compose file's directory. Any variable referenced in `compose.yaml` as `${VAR_NAME}` or `${VAR_NAME:-default}` will be interpolated from:
1. Shell environment variables (highest priority)
2. The `.env` file in the compose directory
3. The default from `:-syntax` (lowest priority)

**Critical: missing vars → empty strings, not errors.**

```yaml
# compose.yaml
labels:
  - traefik.http.routers.app.entrypoints=${TRAEFIK_ENTRYPOINTS}
```

If `TRAEFIK_ENTRYPOINTS` is not in `.env` and not in the shell env, this evaluates to:
```yaml
labels:
  - traefik.http.routers.app.entrypoints=
```
...which produces a **blank entrypoints label** → Traefik ignores the router or routes incorrectly.

### `:-default` Syntax Prevents Silent Blanks

When a compose file references `${VAR}` and VAR is unset, it becomes empty string — not an error. Use `:-default` to provide safe fallbacks:

```yaml
# Instead of:
FASTER_WHISPER_BEAM_SIZE: ${FASTER_WHISPER_BEAM_SIZE}
# Use:
FASTER_WHISPER_BEAM_SIZE: ${FASTER_WHISPER_BEAM_SIZE:-1}
```

This prevents Python `int('')` crashes, empty label values, and blank connection strings.

**Proactive fix pattern:** When you see `The "X" variable is not set. Defaulting to a blank string.` warnings from Docker Compose for a variable that HAS a sensible default, change `${VAR}` to `${VAR:-default}` in compose.yaml.

### The Deadliest Blank: Multi-Origin FRONTEND_ORIGIN

```yaml
environment:
  FRONTEND_ORIGIN: https://${TWENTY_HOST},https://${LEADS_HOST:-leads.your-domain.example}
```

When `TWENTY_HOST` is unset:
- Evaluates to: `https://,https://crm.your-domain.example`
- First origin is `https://` (empty host)
- SvelteKit/Auth middleware parses this and redirects to: `https://.crm.your-domain.example` (the leading dot comes from resolving `https://` relative to the current domain)

**Fix:** Always set `TWENTY_HOST` in `.env` (or any variable used in multi-origin constructs).

## Required Traefik Labels Per Service

For a service to be reachable via Traefik with HTTPS+Let's Encrypt:

```yaml
services:
  my-app:
    labels:
      - traefik.enable=true
      - traefik.docker.network=${TRAEFIK_DOCKER_NETWORK:-backend_core}
      - traefik.http.routers.my-app.entrypoints=${TRAEFIK_ENTRYPOINTS:-websecure}
      - traefik.http.routers.my-app.rule=Host(`app.example.com`)
      - traefik.http.routers.my-app.tls=true
      - traefik.http.routers.my-app.tls.certresolver=${TRAEFIK_CERTRESOLVER:-letsencrypt}
      - traefik.http.services.my-app.loadbalancer.server.port=3000
```

**Every one of these must resolve to a non-empty value.** Missing entrypoints or certresolver will silently break HTTPS.

### The `--no-deps` issue

When recreating a single service with `docker compose up -d --no-deps service-name`:
- Docker Compose re-interpolates ALL labels from compose.yaml using current env
- If `.env` changed between original deploy and now, the new labels may differ
- Missing vars that were present at original deploy now become blank

**Always verify labels after `up -d --no-deps`:**
```bash
docker inspect container-name --format '{{json .Config.Labels}}' | grep -o 'traefik[^\"]*'
```

## Let's Encrypt ACME Configuration

Traefik's ACME config is set via command-line args (static config), usually in the Traefik container's compose entry:

```yaml
command:
  - --certificatesresolvers.letsencrypt.acme.email=admin@example.com
  - --certificatesresolvers.letsencrypt.acme.storage=/acme.json
  - --certificatesresolvers.letsencrypt.acme.httpchallenge=true
  - --certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web
```

### The Empty ACME Storage Trap

If `/acme.json` is empty (0 bytes) or has incorrect permissions:
- Traefik logs: `Router uses a nonexistent certificate resolver certificateResolver=letsencrypt`
- All services serve the TRAEFIK DEFAULT CERT (self-signed) instead of Let's Encrypt
- The ACME challenge may never start

**Diagnose:**
```bash
# Check ACME storage inside container
docker exec traefik sh -c 'ls -la /acme.json && wc -c /acme.json'

# Check Traefik logs for ACME activity (grep for 'permission' too!)
docker logs traefik 2>&1 | grep -i 'acme\\|challenge\\|cert.*obtain\\|permission'

# Check what cert is served
echo | openssl s_client -connect domain.com:443 -servername domain.com 2>&1 | openssl x509 -noout -subject -issuer
```

### SESSION SIGNAL: "Nonexistent Certificate Resolver"

The misleading error `Router uses a nonexistent certificate resolver certificateResolver=letsencrypt` on EVERY router is almost always an **acme.json permissions issue**, not a missing resolver configuration.

**Real root cause:** Traefik v3.x requires acme.json permissions to be **600** (`-rw-------`). If permissions are too open (e.g., 644 or 777), Traefik silently skips the ACME resolver with:
```
error="unable to get ACME account: permissions 777 for /acme.json are too open, please use 600"
```
This startup error is then buried under thousands of "nonexistent certificate resolver" lines.

**Why 777 happens on Windows:** Docker Desktop for Windows bind-mounts files with overly permissive permissions. A file created via `touch`, `echo -n '' >`, or `New-Item` on Windows gets 777 (`-rwxrwxrwx`) inside the Linux container by default. Traefik rejects this.

**Fix (without losing existing certs):**
```bash
# Fix permissions on the running container
docker exec traefik chmod 600 /acme.json

# Restart Traefik so it re-reads acme.json and initializes the ACME provider
docker compose -f /path/to/compose.yaml restart traefik

# Verify ACME initialized
docker logs traefik 2>&1 | grep -i 'acme\\|cert.*obtain'
# Expected output:
#   INF Starting provider *acme.Provider
#   INF Testing certificate renew...
#   INF Register...
```

**Prevention:** After any `docker compose up -d` that recreates the Traefik container, verify permissions:
```bash
docker exec traefik sh -c 'stat -c "%a %n" /acme.json'
# If output is 777, fix it:
docker exec traefik chmod 600 /acme.json && docker compose restart traefik
```

### Docker Desktop for Windows — File Permissions Quirk

When bind-mounting host files into containers on Docker Desktop for Windows:
- Files created on Windows (`touch`, `echo >`, GUI) get **777** permissions (`-rwxrwxrwx`) inside Linux containers
- This violates security requirements for files like SSH keys (600) and ACME storage (600)
- `chmod` inside the container fixes it but does NOT persist across container recreation
- After `docker compose up -d --force-recreate`, re-run `chmod` on any permission-sensitive files

**Files commonly affected:**
| File | Required Perm | Issue |
|------|--------------|-------|
| `acme.json` | 600 | ACME resolver skipped |
| `id_rsa` | 600 | SSH rejects key |
| `.pgpass` | 600 | PostgreSQL rejects |

**Workaround patterns:**
1. **Post-start entrypoint**: Add a startup script inside the Docker image that chmods the file
2. **Post-compose command**: Always `docker exec <container> chmod 600 /path` after `docker compose up -d`
3. **Dockerfile COPY (not bind mount)**: If the file can be included in the image, permissions are preserved correctly

**Pitfall — `touch` creates directories on Windows:** When a bind mount target's source path was previously deleted and recreated, `touch` on MSYS/Git Bash may create a **directory** instead of a file. Docker then fails to mount with:
```
error mounting "/path/to/file" to rootfs at "/dest": not a directory: Are you trying to mount a directory onto a file?
```
**Fix:** `rm -rf /path && echo -n '' > /path` to ensure a regular file.

### Fresh ACME State (No Previous Certs)

When `acme.json` is empty (fresh deploy or lost state):
- Traefik requests certs from Let's Encrypt when it first sees traffic for each domain
- HTTP-01 challenge requires port 80 to be accessible from the internet
- Cert provisioning can take 30 seconds to a few minutes
- During provisioning, Traefik serves its default self-signed cert → ERR_CERT_AUTHORITY_INVALID in browsers
- Once provisioned, certs persist in `/acme.json`

**To trigger certificate request**, make an HTTPS request to the domain:
```bash
curl -sk https://domain.com/login > /dev/null
```

**Verify cert is live:**
```bash
echo | openssl s_client -connect domain.com:443 -servername domain.com 2>&1 | openssl x509 -noout -subject -issuer -dates
# Expected:
#   subject=CN=domain.com
#   issuer=C=US, O=Let's Encrypt, CN=YR2
#   notBefore=Jun 16 ...
#   notAfter=Sep 14 ...
```

## The `.runtime.env` Pattern

Some compose stacks reference a service-specific env file:

```yaml
services:
  backend:
    env_file:
      - ./path/to/.runtime.env
```

**This file MUST exist**, or `docker compose up` fails with:
```
env file ./path/to/.runtime.env not found: GetFileAttributesEx ... The system cannot find the file specified.
```

Create it from `.env.example` if one exists, then adapt for production:
```bash
cp path/to/.env.example path/to/.runtime.env
# Then edit: NODE_ENV=production, FRONTEND_ORIGIN=https://domain.com, etc.
```

## Docker Build Caching

### `COPY . .` layer caching

The `COPY . .` Docker layer caches based on **content checksums of every file** in the build context. If a file changes, the cache is invalidated. However:

- **Windows line ending changes** (`\r\n` vs `\n`) count as content changes
- **Unstaged git changes** that weren't committed still change the file on disk
- Docker Desktop uses file metadata + content hash for cache keys

**When the cache incorrectly matches:**
```bash
# Use --no-cache to force a full rebuild
docker build --no-cache -t image:latest .

# Build arg trick only works if referenced in Dockerfile:
# Dockerfile must have: ARG BUILD_KILLCACHE
docker build --build-arg BUILD_KILLCACHE=$(date +%s) -t image:latest .
```

### Cached pip install (~6 min)

For Python dependencies-heavy Dockerfiles (scrapegraphai, langchain, etc.):
- The `RUN pip install -r requirements.txt` layer is cached as long as requirements.txt doesn't change
- A `--no-cache` rebuild from scratch takes ~6 minutes (386s measured)
- Use background builds with `notify_on_complete=true` to avoid blocking

## Traefik Multi-Service Port Conflicts

### Same-Host Routing Conflict

When TWO services have `Host(same.domain.com)` in their Traefik labels:
- Traefik uses the one with higher `priority` (default 0)
- Lower-priority service is unreachable unless path-based differentiation is used
- Solution: use `PathPrefix(/api)` + `priority` on one, bare `Host(...)` on the other

### Resolving Routing Conflicts by Changing Subdomains

When a custom frontend and Twenty CRM both target the same host (e.g., `crm.your-domain.example`), the fix isn't always a Traefik priority tweak — it's often a **variable change in `.env`** that moves one service to a different subdomain.

**Pattern:** Use `${LEADS_HOST:-default}` in compose labels and set it in `.env`. Changing `LEADS_HOST` from `crm.your-domain.example` → `leads.your-domain.example` causes Docker Compose to regenerate the frontend container's labels with the new host, and Traefik picks it up on next container start. Twenty CRM remains on `crm.your-domain.example` (uses a separate variable `TWENTY_HOST`).

```yaml
# compose.yaml — variable-based host routing
services:
  frontend:
    labels:
      - traefik.http.routers.frontend.rule=Host(`${LEADS_HOST:-leads.your-domain.example}`)
  twenty:
    labels:
      - traefik.http.routers.twenty.rule=Host(`${TWENTY_HOST:-crm.your-domain.example}`)
```

**After `.env` change, recreate the container:**
```bash
docker compose --profile light up -d --no-deps --force-recreate frontend-service
```

**Verify:**
```bash
curl -sk -o /dev/null -w "%{http_code}" https://crm.your-domain.example   # → Twenty CRM
curl -skL -o /dev/null -w "%{http_code}" https://leads.your-domain.example # → Custom PWA
```

**Third option — file-based router wins over docker labels:** If the file provider (`/config/dynamic.yml`) has a router for the same host, the docker label router (with explicit `priority=220`) can outrank the file router (default priority 0). Either adjust priorities or move the docker-label service to a different subdomain.

## SvelteKit Build Cache

For SvelteKit frontends, the `env` values are baked into the JS bundle at build time:
```html
<script>
  __sveltekit_xxx = {
    base: new URL(".", location).pathname.slice(0, -1),
    env: {"PUBLIC_SOCKET_URL":"https://domain.com"}
  };
</script>
```

- PUBLIC_SOCKET_URL is embedded at build time via `npm run build`
- Changing it after build requires a rebuild
- The base path is computed client-side (relative URL resolution)

## Container Crash Debugging

### Exit Code 137 (SIGKILL / OOM)

Exit code 137 = 128 + 9 (SIGKILL). Almost always an **out-of-memory kill** by the kernel OOM killer.

**Check memory limit:**
```bash
docker inspect container-name --format '{{json .HostConfig.Memory}}'
# 2147483648 = 2GB, 4294967296 = 4GB, 0 = unlimited
```

**Check swap:**
```bash
docker inspect container-name --format '{{json .HostConfig.MemorySwap}}'
# -1 = unlimited, 4294967296 = 4GB (total memory+swap)
```

**Fix — increase memory limit in compose.yaml:**
```yaml
deploy:
  resources:
    limits:
      memory: 6G
    reservations:
      memory: 512M
```

**For GPU containers (faster-whisper, etc.):** The model loading step uses peak memory higher than steady-state. If the model loads at 4GB but then drops to 500MB, the memory limit must accommodate the PEAK. Rule of thumb: set limit to 3x the model size for GPU whisper models.

### Pitfall: Two-Stage Crash Sequence (OOM → Env Var)

A container that crashes repeatedly may have **two independent bugs** that only surface sequentially. Fixing the first reveals the second.

**Real-world pattern (faster-whisper):**

| Stage | Exit Code | Symptom | After Fix | Next Failure |
|-------|-----------|---------|-----------|--------------|
| 1 | 137 (OOM) | Container killed, memory limit hit | Increase memory | New crash, exit code 1 |
| 2 | 1 (crash) | `ValueError: invalid literal for int() with base 10: ''` | Add `:-default` to env vars | Container stays healthy |

**Root cause chain:**
1. The host OOM killer stops the container during GPU model loading (peak memory > limit)
2. Container restarts with backoff (docker restart policy)
3. When you increase memory, the container gets past OOM — but now a new error surfaces:
   ```python
   BEAM_SIZE = int(os.getenv("FASTER_WHISPER_BEAM_SIZE", "1"))  # ← env var EXISTS but is empty string
   ```
   The compose file has `${FASTER_WHISPER_BEAM_SIZE}` (not `:-1`), which resolves to empty string when the variable isn't in `.env`. `os.getenv` returns `""`, not the fallback `"1"`, because the variable exists.

**How to detect:** After fixing an OOM (exit 137), check the container logs — don't assume it's fixed:
```bash
docker logs container-name --tail 20 | grep -i "error\|traceback\|valueerror"
```

**Fix:** Always use `:-default` syntax in compose.yaml for env vars that have sensible defaults, even if you plan to set them in `.env`:
```yaml
# WRONG — empty string when var is unset
FASTER_WHISPER_BEAM_SIZE: ${FASTER_WHISPER_BEAM_SIZE}
# RIGHT — falls back to "1" when var is unset
FASTER_WHISPER_BEAM_SIZE: ${FASTER_WHISPER_BEAM_SIZE:-1}
```

### Exit Code 1 (App Crash)

Check actual application logs, not just compose warnings:
```bash
docker logs container-name --tail 30
```

Common Python crash: `int(os.getenv("VAR", "default"))` fails when VAR is set but empty (empty string is not a valid int). The env var exists as empty string (from `${VAR}` in compose), so `os.getenv` returns `""` instead of the fallback `"default"`.

**Fix:** Use `:-default` in compose.yaml or check for empty in the application code.
