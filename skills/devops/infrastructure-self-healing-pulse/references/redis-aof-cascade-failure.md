# Redis AOF Corruption → Cascade Failure Pattern

Observed June 3, 2026. A single component failure cascaded into a systemic auth+LiveKit outage.

## Pattern

```
Redis AOF corruption (bad file format in .incr.aof)
  → agency-stack-redis-1 crash-looping (restart: unhealthy)
    → all services depending on Redis lose connectivity
      → LiveKit (egress, sip, server): connection refused
      → Authentik: cannot reach Redis for session cache
      → oauth2-proxy-mic: 502 on OIDC discovery (can't reach Authentik)
      → oauth2-proxy-noco: same cascade
      → n8n, NocoDB, Twenty: dependency ordering issue on restart
```

## Detection Signals

The Self-Healing Pulse detects this via:
- Container restart loops with `unhealthy` status on Redis, LiveKit, Authentik
- Health check failures propagating across the agency stack
- Redis container logs showing `Bad file format` or `Can't open AOF`
- Multiple related services failing in a short window (minutes)

## Root Cause

Redis AOF (Append-Only File) corruption from a prior unclean shutdown. The `.incr.aof` file has a bad format entry. Redis refuses to start with corrupt AOF.

## Fix

```bash
docker exec agency-stack-redis-1 redis-check-aof --fix /data/appendonly.aof
# Or if container won't start:
# Copy AOF file, fix it, replace, restart
```

This rewrites the AOF file, discarding the corrupted portion. Redis then starts normally. All dependent services recover on their own after Redis becomes healthy.

## Implications for Pulse Monitoring

- **DON'T** flag each dependent service individually — they're all symptoms of the root cause
- **DO** trace the cascade: find the first container that failed (usually Redis or DB), that's the root
- Redis AOF corruption can happen on any unclean shutdown (host reboot, Docker daemon restart, OOM kill)
- The cascade can take 30-60 minutes to fully recover as services restart and retry in dependency order
- Services may appear "healthy?" (starting for 5s then die) during the cascade — this is the dependency retry window

## Surface in Daily Brief

When this pattern appears in the Self-Healing Pulse output for the current day, surface it in Section 5 (Risks) as:

```
🔴 agency-stack-redis AOF corruption → LiveKit/Authentik/oauth2 cascade failure
   Entire auth+LiveKit layer down. Redis-check-aof --fix needed.
```
