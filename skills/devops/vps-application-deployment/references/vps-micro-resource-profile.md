# Micro VPS Resource Profile — Hamilton-VPS (Oracle Free Tier)

## Instance Metadata

| Field | Value |
|-------|-------|
| Shape | VM.Standard.E2.1.Micro |
| Region | us-ashburn-1 (iad) |
| OS | Ubuntu 22.04.5 LTS |
| Kernel | x86_64 |
| CPU | 1 OCPU (1 vCPU) |
| RAM | 956 MB (total) |
| Boot Volume | 45 GB (30 GB free as of May 30, 2026) |

## Resource at Idle (May 30, 2026)

| Resource | Usage |
|----------|-------|
| RAM used | ~325 MB |
| RAM free | ~128 MB |
| RAM buff/cache | ~502 MB |
| RAM available | ~448 MB |
| Swap | 2 GB → 8 GB (increased May 30) |
| Load | 0.00 (idle) |
| Uptime | 13 days |

## Running Services

| Container | Purpose | Up Since |
|-----------|---------|----------|
| hbbr | RustDesk relay | 13 days |
| hbbs | RustDesk signal | 14 hours |
| hmac-caddy | Caddy reverse proxy | 13 days |
| mobile-mechanic_postgres_1 | Client app DB | 13 days (healthy) |
| mobile-mechanic_redis_1 | Client app cache | 13 days |

## SSH Access

```bash
ssh -i ~/.ssh/oracle_vps ubuntu@129.153.156.190
```

Key comment: `ubuntu@hamilton-vps`

## Memory Budget for New Deployments

With ~448 MB available at idle and existing services consuming ~325 MB:

| Service | Est. RAM | Strategy |
|---------|----------|----------|
| Spacebar (Node.js) | ~150-200 MB | Run natively, not Docker; share existing PostgreSQL |
| Fermi (Node.js) | ~30-50 MB | Run natively; serve on different port |
| Hermes agent | ~200 MB | Docker (mem_limit), only if Ampere A1 |
| **Total both** | **~180-250 MB** | Feasible with 8 GB swap as OOM safety net |

**Key constraint:** This VPS CANNOT run the full Hermes hybrid stack (agent + gateway + postgres + redis + MCP servers). Target lightweight Node.js services only. Reserve the Ampere A1 shape for the full stack.

## Verified May 30, 2026

- Service discovery: `docker ps` scan across all containers
- Resource baseline: `free -h`, `df -h /`, `nproc`, `uptime`
- Shape confirmation: OCI metadata endpoint (169.254.169.254)
- SSH key validation: `oracle_vps` key works with `ubuntu` user
