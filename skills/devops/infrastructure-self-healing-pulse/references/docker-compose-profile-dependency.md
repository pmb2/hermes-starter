# Docker Compose Profile Dependency Quirk

When a Docker Compose project uses the `profiles:` key on services, those
services are **invisible to `depends_on`** from non-profiled services unless
`--profile <name>` is passed.

## The Problem

```yaml
services:
  postgres:
    image: postgres:17
    profiles: ['light', 'full']          # ← only active with --profile

  postgres-init:
    image: postgres:17
    depends_on:
      postgres:
        condition: service_healthy       # ← FAILS without --profile
    # NO profile — always active
```

Running `docker compose up -d` without `--profile light` produces:
```
service "postgres-init" depends on undefined service "postgres":
invalid compose project
```

Docker Compose treats profiled services as non-existent when the profile
is not selected, which includes dependency resolution. This is not an
error in the compose file — it is expected behavior.

## The Fix

Always pass `--profile light` (or whichever profile covers the base
infrastructure) when starting the stack:

```bash
docker compose --profile light up -d --remove-orphans
```

With `--profile light`, profiled services are included in the project,
dependencies resolve, and `docker compose config --services` returns
a complete list.

## Multi-Profile Stacks

| Profile | Includes | Used For |
|---------|----------|----------|
| `light` | postgres, redis | Core infrastructure, always needed |
| `full` | All services + apps | Full production stack |

Start light first, then add full:

```bash
docker compose --profile light up -d
docker compose --profile full up -d --no-build
```

## Build Commands Also Need Profiles

`docker compose build` fails with the same dependency error if build
dependencies reference profiled services. Always pass `--profile`:

```bash
docker compose --profile light build <service-name>
docker compose --profile full build          # builds everything
```

## Detection Script

```bash
# Check if profiles exist in the compose file
grep -n "profiles:" compose.yaml | head -5

# List services without profiling
docker compose config --services
# vs with profiling
docker compose --profile light config --services
```

## Startup Script Fix

Powershell startup scripts that call `docker compose up -d` without
`--profile` will fail silently (the compose runs but profiled services
are missing, causing dependency errors). Fix:

```powershell
# Before (broken for profiled stacks):
docker compose up -d --remove-orphans

# After (includes light profile services):
docker compose --profile light up -d --remove-orphans
```

## Related: Missing Image Error

Another startup failure mode: if a service's `image:` value references a
Docker Hub repo that doesn't exist (e.g. `backus/authentik-server-patched`),
`docker compose up` fails with "pull access denied." **Check `.env` for
incorrect image references** before debugging deeper — often the fix is
switching to the canonical upstream image (`ghcr.io/goauthentik/server` vs
a custom one that was never pushed).
