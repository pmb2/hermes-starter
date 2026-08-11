# Docker Post-Restart Exit Detection — Reference

## The Problem: Silent Container Recovery Failures

When Docker daemon restarts (host reboot, Docker service update, docker.sock bounce), it attempts to restart all containers with `--restart unless-stopped` or `--restart always`. **Not all containers succeed.** Some exit immediately after restart with code 137 (`SIGKILL` = 128 + 9) and stay dead until manually detected.

**Why you won't notice automatically:**
- Docker doesn't alert on individual container failures
- `docker ps` (running containers only) hides the exited ones
- The affected service simply disappears — no crash logs, no watchdog triggers
- A pulse check that only checks running containers misses the gap

## Signal: Exit Code 137

| Exit Code | Meaning | Likely Cause |
|-----------|---------|-------------|
| 137 (128+9) | `SIGKILL` | Docker daemon restarted, container didn't init properly, OOM killer |
| 143 (128+15) | `SIGTERM` | Graceful shutdown (expected) |
| 139 (128+11) | `SIGSEGV` | Container process segfaulted |
| 0 | Success | Container exited normally |
| 1+ (non-zero) | Application error | App-specific failure |

**137 specifically** after a daemon restart means: Docker killed the process during shutdown, then failed to properly restart it. Common causes:
- Startup race condition (container depends on a service not yet ready)
- Entrypoint script error in fresh context
- Resource exhaustion during mass recovery (all containers starting simultaneously)
- Volume mount not yet available

## Detection: Find Silently Exited Containers

After any Docker daemon restart event, explicitly check for dead containers:

```bash
# Find recently-exited containers (not the long-dead ones from 2 weeks ago)
docker ps -a --filter "status=exited" --filter "name=<project-prefix>" \
  --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Sort by recency to spot fresh exits
docker ps -a --filter "status=exited" --format "{{.Names}}\t{{.Status}}" | sort -t: -k1
```

**What to look for:** Containers whose exit time matches the daemon restart time. A container that exited 12 hours ago after a daemon restart 12 hours ago is a recovery failure — not intentional downtime.

## Verification Pattern: Full Container Census

After a daemon restart, don't trust `docker ps` alone. Run a full census:

```bash
echo "=== RUNNING ==="
docker ps --format "{{.Names}}"
echo "=== EXITED (recent) ==="
docker ps -a --filter "status=exited" --format "{{.Names}}\t{{.Status}}" | head -20
echo "=== TOTAL ==="
docker ps -a --format "{{.Names}}" | wc -l
```

Cross-reference against your known container inventory. Every container that was `Up` before the restart should be `Up` now. If `docker ps -a` count matches but `docker ps` count is lower, some didn't recover.

## Recovery: docker start (First Line)

Before reaching for `docker run` or compose recreation, try simple restart:

```bash
# Try starting the exited container
docker start <container-name>

# Verify it's truly healthy (not just running)
sleep 5
docker ps --filter "name=<container-name>" --format "{{.Names}}\t{{.Status}}"
```

**Why this works:** Docker retains the full container config (networks, volumes, labels, env vars). `docker start` re-executes the original entrypoint with all original config intact — it's the lowest-risk recovery path.

**When it fails:** If the container exits again immediately, move to `docker logs <container>` to diagnose. Common second-failure causes:
- Entrypoint script references absolute paths that changed
- Dependencies (DB, Redis) aren't ready when this container starts
- Resource limit hit during mass recovery

## Monitoring: Add to Pulse Quick Checks

Include exit-code verification in any Docker health pulse:

```bash
# Quick check: any containers with fresh exit code 137?
docker ps -a --filter "status=exited" --format "{{.Names}}\t{{.Status}}" | grep -E "(137|exited.*ago)" | head -5
```

If this returns results after a known daemon restart, action is needed.

## Concrete Example: plane-mcp

**Symptom:** `plane-mcp` container showed `Exited (137) 12 hours ago` after a Docker daemon restart. All other 49 containers recovered cleanly. Pulse discovered it.

**Root cause:** Container was `Exited (137)` — died during daemon restart, Docker's recovery-thaw missed it. Simple `docker start plane-mcp` resolved it immediately.

**Lesson:** After any Docker daemon restart, explicitly verify ALL containers are running — not just the obvious ones. MCP servers, reverse proxies, and small-footprint containers are the most likely to silently die.
