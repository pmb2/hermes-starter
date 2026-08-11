# Docker Desktop WSL Wedge Recovery — Session Detail

Date: 2026-05-30
Setup: Windows 10, git-bash, Docker Desktop 29.5.2 (WSL2 backend)

## Trigger

The `spacebar` Docker container crash-looped due to TypeORM migration error (relation "security_keys" already exists). After ~2-3 restart cycles, Docker Desktop's WSL2 backend wedged — all `docker` CLI commands hung indefinitely.

## Diagnosis

```bash
# Step 1: Docker commands hang (timeout after 5-15s)
timeout 10 docker ps -a       # HUNG — never returns
timeout 10 docker info        # HUNG — never returns

# Step 2: Docker Desktop processes ARE running (Docker isn't "down", it's wedged)
tasklist | grep -iE "docker|com\.docker"
# → Docker Desktop.exe, com.docker.backend.exe, docker-sandbox.exe all present

# Step 3: docker-desktop WSL distro is "Running" but unresponsive
wsl -l -v                     # docker-desktop shows "Running"
wsl -d docker-desktop -- ps aux  # → dockerd IS running inside (PID 163)
                                  # → containerd IS running (PID 127)
                                  # → containerd-shim active (containers alive)
# But the Windows→WSL named pipe is broken

# Step 4: Check Docker contexts
docker context ls
# → desktop-linux * (npipe:////./pipe/dockerDesktopLinuxEngine) - hangs
# → default (npipe:////./pipe/docker_engine) - may also hang

# Step 5: Find crash-looping containers that caused the wedge
docker ps -a --filter "status=restarting" --format '{{.Names}} {{.RestartCount}}'
# → spacebar (RestartCount: 2+)
# → oauth2-proxy-n8n (RestartCount: 9)
# → oauth2-proxy-agent (RestartCount: 9)
```

### Variant: WSL VM = "Stopped" (Engine Died During Init)

A different presentation observed on 2026-05-30: `wsl -l -v` shows `docker-desktop` as **Stopped** (not Running), yet Docker Desktop processes are alive and `docker ps`/`docker info` all hang with timeouts.

**Key signal in backend logs:**

```bash
tail -20 "$LOCALAPPDATA/Docker/log/host/com.docker.backend.exe.log"
# → [com.docker.backend.exe.enginedependencies] still waiting for init control API
#   to respond after 17m42.6028301s
# → [com.docker.backend.exe.apiproxy] still waiting for the engine to respond to
#   _ping after 17m40.9114698s: HTTP 500:
# → Repeated every second — engine never initializes
```

The init control API returns HTTP 500 or never responds, and the WSL distro was terminated (or failed to boot) before it could serve requests. Since the WSL VM is already Stopped, `wsl -t docker-desktop` is a no-op — the recovery sequence simplifies.

**Simplified recovery for this variant:**

```bash
# 1. Kill Docker Desktop processes
taskkill //F //IM "Docker Desktop.exe"
taskkill //F //IM com.docker.backend.exe
sleep 2

# 2. Ensure WSL is clean (already Stopped, but shutdown for good measure)
wsl --shutdown
sleep 3

# 3. Restart Docker Desktop
"/c/Program Files/Docker/Docker/Docker Desktop.exe" &

# 4. Wait for WSL VM to boot (60s on first init after shutdown)
sleep 60

# 5. Verify containers came back
docker ps --format '{{.Names}} {{.Status}}'
```

No need for crash-looper containment in this variant since no containers were running before the restart. But still check and contain any crash-loopers after recovery.

## The Fix (Nuclear Recovery)

The `docker -t docker-desktop` and `wsl --shutdown` appear to succeed but don't fully work because Docker Desktop's watchdog process (`com.docker.backend.exe`) keeps respawning the WSL distro.

### Correct sequence (from actual session):

```bash
# Phase 1 — Kill ALL Docker processes (repeat until clean)
taskkill //F //IM "Docker Desktop.exe"
taskkill //F //IM com.docker.backend.exe
taskkill //F //IM com.docker.build.exe
taskkill //F //IM docker-sandbox.exe
taskkill //F //IM docker.exe
sleep 2
# Kill respawns
taskkill //F //IM "Docker Desktop.exe"
taskkill //F //IM com.docker.backend.exe
sleep 1

# Phase 2 — Verify clean
tasklist | grep -i docker  # → CLEAN (no output)

# Phase 3 — Clear stale lock files
rm -f "$LOCALAPPDATA/Docker/backend.lock" "$LOCALAPPDATA/Docker/frontend.lock" "$LOCALAPPDATA/Docker/launcher.lock"

# Phase 4 — NOW terminate WSL (no Docker processes to respawn it)
wsl -t docker-desktop
sleep 3
wsl -l -v  # docker-desktop should be Stopped ✓

# Phase 5 — Launch Docker Desktop fresh
"/c/Program Files/Docker/Docker/Docker Desktop.exe" &
# Wait 45-60s for first boot

# Phase 6 — Verify responsiveness
timeout 15 docker ps -a
# If still hanging, repeat from Phase 1

# Phase 7 — IMMEDIATELY contain crash-loopers (before they re-wedge)
docker ps -a --filter "status=restarting" --format '{{.Names}}'
docker stop spacebar 2>/dev/null || true
docker update --restart=no spacebar 2>/dev/null || true
# Repeat for any other crash-looping containers
```

### Post-recovery verification:

```bash
# All 50+ containers came back up (healthy) on this machine
docker ps -a --format 'table {{.Names}}\t{{.Status}}'
# → spacebar: "Up 21 seconds (health: starting)" — soon crashes
# → spacebar-postgres: "Up 21 seconds (healthy)" — fine
# → All supabase/bookends/agency containers: "Up ... (healthy)" — fine
# → oauth2-proxy-*: "Restarting (1) ..." — still crash-looping
```

## The Crash-Looping Triggers

### 1. Spacebar (TypeORM migration)

After the database is seeded, any restart hits:
```
error: relation "security_keys" already exists
    at PostgresQueryRunner.query
    at webauthn1675044825710.up
```

**Fix:** Set `APPLY_DB_MIGRATIONS=false` in the Spacebar environment, or run Spacebar natively (non-Docker) on port 3100.

### 2. oauth2-proxy containers (config issues)

`oauth2-proxy-n8n` and `oauth2-proxy-agent`: Exit code 1, RestartCount 9. Configuration issue in oauth2-proxy setup. Need proper config file or env vars.
