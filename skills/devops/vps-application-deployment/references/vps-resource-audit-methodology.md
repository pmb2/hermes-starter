# VPS Resource Audit Methodology

> Measured 2026-06-01 on VM.Standard.E2.1.Micro (discy.your-domain.example)
> Oracle Free Tier, US-Ashburn (iad), AMD EPYC 7551 32-Core Processor

## Complete Process Table (sorted by RSS)

| Service | RSS (MB) | CPU% | Type | Notes |
|---------|----------|------|------|-------|
| sb-bundle-3100 (Spacebar) | 241 | 85% | Node.js native | Discord-compatible API server |
| Fermi (dist/start.js) | 96 | 35% | Node.js native | Web client UI |
| Host Caddy (zombie) | 49–96 | 1.5% | Go native | **No listening ports, no config file** |
| Docker Caddy (hmac-caddy) | 47–80 | 9–39% | Docker Go | Serves all 3 domains |
| Docker PostgreSQL | 39 | 29% | Docker | Spacebar DB + mobile-mechanic DB |
| Oracle Cloud Agents (3) | 28 | 0.8% | Native snap | gomon, wlp, agent — required by OCI |
| containerd + dockerd | 27 | 0.5% | Native | Docker infra processes |
| System: systemd, sshd, journald, etc. | 25 | 3% | Native | Base OS services |
| multipathd | 28 | 0% | Native | High for what it does (SAN multipath on a non-SAN box) |
| Docker RustDesk (hbbs/hbbr) | 1.1 | 0.1% | Docker | Remote desktop relay |
| Docker Redis | 1.4 | 1.7% | Docker | Spacebar cache |
| Postgres workers (×10) | 66 (6.6 each) | 25% | Docker PG children | Spacebar connections, idle |
| **Total Used** | **~620** | | | **190 MB free, 330 MB swap used** |

## Commands Used

```bash
# VPS identity
curl -s http://169.254.169.254/opc/v1/instance/ | python3 -c "import sys,json;d=json.load(sys.stdin);print(json.dumps({k:d.get(k) for k in ['shape','region','displayName']},indent=2))"

# Memory + swap
free -m && swapon --show

# Processes sorted by memory
ps aux --sort=-%mem | head -40

# Docker containers with live stats
docker stats --no-stream --no-trunc

# Listening ports (ALL)
sudo ss -tlnp

# Caddy-specific: detect zombie instances
# (running with no listening ports and no config)
ps aux | grep -i caddy | grep -v grep
sudo ss -tlnp | grep caddy
sudo find /etc -name 'Caddyfile*' 2>/dev/null

# Disk usage
df -h

# DNS verification (all domains resolve to same IP)
dig +short domain1.com
dig +short domain2.com
```

## Bot Gateway Profile (from live log)

Extracted from ~/.hermes/logs/spacebar-*.log:

```
[Spacebar] INFO [MEMORY] baseline rss=69MB gc=(591, 8, 4) threads=1 uptime=0s
```

- **69 MB baseline RSS** (after starting, before processing messages)
- **28 plugins loaded** (browser × 3, image_gen × 4, video_gen × 2, web × 7, etc.)
- **~4-6 threads** per process
- **1 persistent WebSocket** connection to Spacebar
- **Log file size**: ~300-600 KB after 2 hours of fleet uptime

## Caddy Zombie Detection Pattern

A Caddy process is a zombie when:

1. **Process exists** (`ps aux | grep caddy`)
2. **No listening ports** (`ss -tlnp` shows docker-proxy owning 80/443, not Caddy itself)
3. **Config file missing or non-functional** (`stat /etc/caddy/Caddyfile` fails)

In this session:
- Host Caddy (PID 2460238) ran since May 30 with `caddy run --config /etc/caddy/Caddyfile`
- But `/etc/caddy/Caddyfile` did not exist (deleted after start?)
- The process had zero TCP listeners
- Wasted 96 MB RSS (peak) — 10% of the VPS's 956 MB RAM
- Docker Caddy was already handling all 3 domains: hamiltonmobileautocare.com, discy.your-domain.example, gc.your-domain.example

**One Docker Caddy handling N domains** is the correct pattern:

```caddyfile
# All domains served by a single Caddy instance
domain1.com {
    reverse_proxy 10.0.0.109:80
}

domain2.com {
    handle @api { reverse_proxy 127.0.0.1:3100 }
    handle { reverse_proxy 127.0.0.1:8081 }
}
```

## Oracle Free Tier Shape Comparison

| Feature | VM.Standard.E2.1.Micro (current) | VM.Standard.A1.Flex (upgrade) |
|---------|----------------------------------|-------------------------------|
| Architecture | x86_64 (AMD EPYC) | aarch64 (Ampere ARM) |
| CPU | 1 OCPU (2 vCPUs) | Up to 4 OCPU (flexible) |
| RAM | 956 MB | Up to 24 GB (flexible) |
| Boot volume | Up to 200 GB | Up to 200 GB |
| Network | Up to 1 Gbps | Up to 4 Gbps (scales with OCPU) |
| Monthly cost (at spec) | $0/mo (always free) | $0/mo (within free tier limits) |

This document saved as reference for future VPS capacity planning sessions.
