# Docker Build Error Reference (Spacebar Multi-Stage)

## Error 1: .dockerignore exclusions

```
#21 [runtime 10/14] COPY config.json ./config.json
#21 ERROR: failed to calculate checksum ... "/config.json": not found

#25 [builder 7/9] COPY tsconfig.json tsconfig.tsbuildinfo ./
#25 ERROR: failed to calculate checksum ... "/tsconfig.tsbuildinfo": not found

#24 [runtime 13/14] COPY locales/ ./locales/
#24 ERROR: failed to calculate checksum ... "/locales": not found
```

**Cause**: `.dockerignore` excludes these files from the build context:
- Line 44: `tsconfig.tsbuildinfo`
- Line 80: `config.json`

While the Dockerfile COPY commands require them at build time.

**Fix**: Remove the exclusion lines from `.dockerignore`.

---

## Error 2: Missing build artifacts

```
#21 [runtime 10/14] COPY config.json ./config.json
#21 ERROR: ... "/config.json": not found
```

Even when `.dockerignore` is fixed, the `locales/` directory and `tsconfig.tsbuildinfo` file may not exist in the source tree:

- `tsconfig.tsbuildinfo` — TypeScript incremental build output, not tracked in git
- `locales/` — localization directory, not included in all forks

**Fix**: 
```bash
touch tsconfig.tsbuildinfo
mkdir -p locales
```

---

## Error 3: Redundant npm ci breaks on postinstall

```
#20 [runtime 7/14] RUN npm ci --omit=dev && npm cache clean --force
sh: patch-package: not found
npm error code 127
```

The runtime stage copies `node_modules` from the builder (`COPY --from=builder /app/node_modules ./node_modules` at line 52), which already includes dev dependencies. The `npm ci --omit=dev` at line 48 is redundant AND fails because `npm` runs the `postinstall` script which calls `patch-package` — a dev dependency the `--omit=dev` flag excludes.

**Fix**: Remove lines 44-48 from the runtime stage:
```dockerfile
# Delete:
COPY package.json package-lock.json ./
COPY patches/ ./patches/
RUN npm ci --omit=dev && npm cache clean --force
```

---

## Error 4: Docker Engine 500 / "no route to host"

```
docker ps --format '{{.Names}} {{.Status}}'
→ request returned 500 Internal Server Error for API route and version
  http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.43/containers/json,
  check if the server supports the requested API version
```

Backend log:
```
[com.docker.backend.exe.apiproxy] still dialing 192.168.65.7:2376
  after 2.13s: connect tcp 192.168.65.7:2376: no route to host
```

**Cause**: Docker Desktop's named pipe proxy cannot reach the Docker engine inside the `docker-desktop` WSL2 VM. The engine (`dockerd`) is running but the networking bridge from Windows to WSL2 fails.

**Fix**: See "Phase 5: Docker Desktop Recovery" in the main skill.

---

## Error 5: Missing `package.json` in runtime stage (module-alias crash)

```
Error: Unable to find package.json in any of:
[/app]
    at init (/app/node_modules/module-alias/index.js:184:11)
```

The Dockerfile's multi-stage build copies `dist/`, `node_modules/`, config, and assets into the runtime stage, but `module-alias` (used in `dist/bundle/start.ts`) reads `package.json` at startup to resolve path aliases. Without it the process exits immediately with a crash loop.

**Fix**: Add `COPY --from=builder /app/package.json ./package.json` in the runtime stage, after copying `node_modules`:

```dockerfile
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json    # ← add this
```

## Error 6: Port already allocated — stale node process

```
Error response from daemon: Bind for 0.0.0.0:3001 failed: port is already allocated
```

When Spacebar was previously started manually (`npm run start`), the `node.exe` process holds port 3001 and survives Docker restarts. Despite `docker ps` showing no spacebar container, the port is busy.

**Fix**:
```bash
# Find the offender
netstat -ano | grep ":3001 " | grep LISTEN
# Get PID from last column

# Kill it
taskkill //F //PID <PID>
```

Then retry `docker compose up -d`.

## Error 7: Port already allocated — Docker proxy holds port after container removal

```
Bind for 0.0.0.0:3001 failed: port is already allocated
```

Even after the occupied port is freed (confirmed by `netstat` showing no LISTEN on 3001), Docker's internal port proxy inside the WSL2 VM can still hold the port reservation from a previous container. This is a Windows Docker Desktop / WSL2 bug.

**Fix**: Remove the `ports:` mapping from `docker-compose.yml` and let Traefik handle routing via the `backend_edge` network:

```yaml
# Comment out the port mapping:
# ports:
#   - "3001:3001"
```

The spacebar container is still reachable at `discy.your-domain.example` (Traefik) and internally on the Docker network. Re-enable the port mapping after a full Docker Desktop restart.
