# Docker Compose Production Hardening Patterns

> Phase 0 patterns for `infrastructure-technology-evaluation`. These are the exact YAML blocks to add to every service in a Docker Compose stack before considering orchestration migration.

## The Four-Modifier Pattern

Every service across every stack should gain these four blocks. Apply them together in a single pass per compose file:

```yaml
services:
  any-service:
    # 1. RESOURCE LIMITS — prevents OOM cascade
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 128M

    # 2. HEALTHCHECK — enables depends_on with condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:PORT/"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 30s

    # 3. LOGGING — prevents disk fill from verbose containers
    logging:
      driver: local
      options:
        max-size: "10m"
        max-file: "3"

    # 4. PROFILES — tiered operation, don't run everything 24/7
    profiles:
      - "full"
```

## Per-Service Override Tables

### Resource Limits by Service Type

| Service Type | CPU Limit | Memory Limit | Notes |
|-------------|-----------|-------------|-------|
| **Postgres** | '2' | 2G-4G | pg_isready healthcheck |
| **Redis** | '0.5' | 256M | redis-cli ping healthcheck |
| **GPU model (Qwen 35B)** | '8' | 28G | 23GB model needs headroom |
| **GPU model (Qwen 14B)** | '4' | 16G | |
| **Ollama** | '2' | 4G-8G | curl /api/tags healthcheck |
| **ComfyUI** | '4' | 8G | GPU, heavy inference |
| **n8n** | '2' | 2G | wget healthcheck on HTTP port |
| **Twenty/Cal.com** | '2' | 2G | Web app healthcheck |
| **LiveKit Agent** | '2' | 4G | Runs ML models |
| **Fonoster services** | '1' | 1G each | Many small services |
| **Auth service** | '1' | 1G | |
| **Web frontend** | '1' | 512M | |
| **Reverse proxy** | '1' | 256M | |
| **MinIO** | '1' | 512M | curl /minio/health/live |
| **Static site** | '0.5' | 256M | |
| **Default** | '1' | 512M | Use for anything not listed |

### Healthcheck Patterns by Service

```yaml
# PostgreSQL
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER || exit 1"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 30s

# Redis
redis:
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 3s
    retries: 5

# MariaDB/MySQL
mariadb:
  healthcheck:
    test: ["CMD-SHELL", "mysqladmin ping -h localhost"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 30s

# n8n
n8n:
  healthcheck:
    test: ["CMD", "wget", "--spider", "http://localhost:5678/healthz"]
    interval: 15s
    timeout: 5s
    retries: 3
    start_period: 30s

# Nextcloud
nextcloud:
  healthcheck:
    test: ["CMD-SHELL", "php -f /var/www/html/occ status | grep 'installed: true'"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s

# Generic web app (Next.js, Fastify, etc)
web-app:
  healthcheck:
    test: ["CMD", "wget", "--spider", "http://localhost:PORT/health"]
    interval: 15s
    timeout: 5s
    retries: 3
    start_period: 30s

# MinIO S3
minio:
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:9000/minio/health/live || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s

# Ollama LLM
ollama:
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:11434/api/tags || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s

# Traefik (already has API health)
traefik:
  healthcheck:
    test: ["CMD-SHELL", "wget --spider http://localhost:8080/api/version || exit 1"]
    interval: 15s
    timeout: 5s
    retries: 3

# Vaultwarden
vaultwarden:
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:80/alive || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 3

# Nginx
nginx:
  healthcheck:
    test: ["CMD-SHELL", "nginx -t 2>/dev/null || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### Profile Strategy

```yaml
# Three tiers:
# light   = always-running core (proxy, DB, workflow engine) — ~20 containers
# gpu     = AI/ML models added to light — ~30 containers  
# full    = everything including agency, business apps — ~101+ containers

# Core infrastructure — always available
traefik:
  profiles: ["light", "gpu", "full"]

postgres:
  profiles: ["light", "gpu", "full"]

redis:
  profiles: ["light", "gpu", "full"]

# GPU/AI workloads — only when doing AI work
qwen-main:
  profiles: ["gpu", "full"]

comfyui:
  profiles: ["gpu", "full"]

# Business apps — only when running full stack
agency-app:
  profiles: ["full"]

client-website:
  profiles: ["full"]
```

Usage:
```bash
docker compose --profile light up -d   # Core only
docker compose --profile gpu up -d     # Add AI models
docker compose --profile full up -d    # Everything
```

### GPU Device Reservations

```yaml
services:
  gpu-model:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 16G
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## Centralized Orchestrator Pattern

After hardening individual stacks, create a root `docker-compose.yml` that includes them all:

```yaml
name: infrastructure

include:
  - path: ./stack-a/docker-compose.yml
    env_file: ./stack-a/.env
  - path: ./stack-b/docker-compose.yml
  # ... all stacks

# Controls everything from one directory:
# docker compose --profile light ps
# docker compose --profile full logs -f
```

## Application Ordering

```bash
# 1. Apply to the largest, most complex stack first (proves the pattern)
# 2. Apply to stack with GPU workloads next (most critical resource limits)
# 3. Apply to the remaining stacks (smallest last)
# 4. Create centralized docker-compose.yml
# 5. Run port_inventory.sh to detect conflicts
# 6. Run backup_pipeline.sh to verify DB backups work
```

## Status Tracking Spreadsheet

Use a simple markdown table to track completion across stacks:

| Stack | Compose File | Services | Limits | Healthcheck | Logging | Profiles | Status |
|-------|-------------|----------|--------|-------------|---------|----------|--------|
| Agency | `ghl/compose.yaml` | 53 | ✅ | ✅ | ✅ | ✅ | Done |
| Backend | `n8n/docker-compose.yml` | 47 | ✅ | ✅ | ✅ | ✅ | Done |
| AI Gateway | `model-gateway/...` | 7 | ✅ | ✅ | ✅ | ✅ | Done |
| ... | ... | ... | ... | ... | ... | ... | ... |

## Verification

After applying to all stacks:

```bash
# YAML validity
for f in $(find /path/to/stacks -name "docker-compose*.yml" -o -name "compose.yaml"); do
  python -c "import yaml; yaml.safe_load(open('$f')); print('OK: $f')" 2>&1
done

# Profile isolation test
docker compose --profile light up -d
docker ps | wc -l   # Should show ~20 containers, not 101

# Resource limits exist
docker inspect $(docker ps -q) --format '{{.Name}} {{.HostConfig.Memory}}' | head -10

# Healthcheck exists
docker inspect $(docker ps -q) --format '{{.Name}} {{.State.Health.Status}}' | head -10
```

## Companion Scripts

After hardening, create these alongside the compose files:

- `backup_pipeline.sh` — pg_dump all databases with compression + retention
- `port_inventory.sh` — scan published ports, detect conflicts, output table/CSV
- `image_cleanup.sh` — prune stale images, report reclaimable space
