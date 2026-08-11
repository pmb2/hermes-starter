---
name: vps-application-deployment
description: "Deploy web applications to VPS instances (Oracle Cloud free tier, AWS EC2, etc.) with Docker + Caddy reverse proxy — standardized stack, SSL, DNS, and security hardening."
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [vps, deployment, docker, caddy, ssl, security]
    related_skills: [static-site-deployment, multi-agent-system-architecture]
    triggers: [vps-deployment, deploy-app-to-vps, oracle-cloud-setup, docker-caddy-deploy, docker-compose-traefik, traefik-deployment, compose-traefik, nextjs-docker-deployment, app-hosting-setup, vps-provisioning, oracle-free-tier, oracle-account-requirements, arm-provisioning, rebrand-deployed-app, customize-deployed-app, deployed-app-logo, post-deployment-customization, vps-git-push, rebuild-restart-app, i18n-rebrand, vps-resource-audit, vps-capacity-planning, zombie-process-detection, oci-out-of-capacity, co-hosting-analysis, broken-avatars, cdn-not-working, spacebar-cdn-issue, avatar-images-broken, static-file-serving-workaround, express-route-undefined, docker-caddy-upstream-down, password-reset, spacebar-user-management, reset-user-password, forgot-password-spacebar, sed-caddyfile-pitfall, caddy-global-replace, android-home-screen-icon, pwa-manifest-update, acme-permissions, letsencrypt-not-working, traefik-default-cert, self-signed-cert-found, nonexistent-certificate-resolver, acme-permissions-777, docker-OOM-container, container-exit-137, faster-whisper-crash, docker-windows-permissions, container-crash-debug, env-var-not-set-compose, docker-env-blank-string, docker-compose-var-defaults, twenty-crm, twenty-crm-setup, twenty-crm-deploy, twenty-crm-config, twenty-crm-redirect, twenty-crm-login, twenty-crm-not-loading, twenty-crm-signin, twenty-crm-nestjs-error, twenty-crm-config-validation, twenty-crm-crash, twenty-crm-multiworkspace, twenty-crm-subdomain, dot-crm-redirect]
---

# VPS Application Deployment

Standardized procedure for deploying web applications to a cloud VPS (Oracle, AWS, etc.) with Docker Compose, Caddy reverse proxy, auto SSL, and security hardening.

## 🔑 Core Principles

### Account Ownership Model (CRITICAL)
- **Each client/project gets their OWN cloud account** — never share a master account across clients
- The master Oracle account (`<your-email>@gmail.com`) is only for internal/hermes infrastructure
- For every external client (Eric, Cody, Hamilton, etc.), create a **dedicated Oracle Cloud account** with:
  - A **fresh email address** created for the purpose (GMail, Proton, etc.) — you own the credentials
  - Phone verification (use a burner or the client's phone if available)
  - Credit card for identity verification (free tier — not charged, but required by Oracle)
- Client accounts are created by YOU (the agency/operator), not the client. The client doesn't need to lift a finger for infrastructure setup.
- After deployment, if the client wants to own the account: **transfer admin access** to them or give them the credentials you created.
- **Why this model wins:**
  - Avoids Oracle's tenancy-wide resource caps (4 OCPU / 24GB RAM max per account) being exhausted by a single overloaded master account
  - Prevents credential sprawl, billing confusion, and service-hostage optics
  - Each client's infrastructure is isolated — no cross-contamination
  - The agency retains technical admin access for management/maintenance
  - Scales infinitely — each new client gets their own fresh quota

### Alternative: Client-Created Account Handoff

If the operator's master account is already at its Always Free instance limit and the client is able to complete a simple signup, have the client create the Oracle account themselves and hand it back. This avoids waiting for the operator to create a fresh email and provides a clean ownership path.

**When it applies:**

- The master account is at the 2× `VM.Standard.E2.1.Micro` or 4 OCPU Ampere A1 limit.
- The workload fits in one Always Free Micro instance (1 OCPU, 1 GB RAM).
- The client can be trusted with a short checklist and will share the VPS IP and SSH key.

**Client deliverables to the operator:**

- Oracle Cloud account name and username (email).
- VPS public IP address.
- Private SSH key file.
- Confirmation that ports 80 and 443 are open.
- Confirmation that the instance uses `VM.Standard.E2.1.Micro` with Ubuntu 22.04/24.04.

**Operator actions after handoff:**

- Update domain DNS A record to the VPS IP.
- SSH in, install Docker, Caddy, and the application stack.
- Migrate files and database from the local machine.
- Verify HTTPS and site functionality.

See `references/oci-free-tier-client-onboarding.md` for the exact client-facing checklist.

### Standard Stack
| Component | Choice | Notes |
|-----------|--------|-------|
| OS | Ubuntu LTS (24.04 ARM64) | Oracle Ampere A1 is ARM, AMD64 also works |
| Shape | Ampere A1.Flex (2 OCPU / 12GB) | Free forever, 4 OCPU/24GB max per tenancy |
| Container | Docker + Docker Compose | Installed via get.docker.com |
| Proxy | Caddy v2 | Auto Let's Encrypt SSL |
| DNS | Cloudflare or Namecheap default | A record to VPS public IP |
| Security | UFW + Fail2Ban + auto updates | Standard hardening |
| Node | Node.js 22 LTS (ARM64) | Via NodeSource |

### Parallel Multi-Project Deployment
- When deploying to **multiple clients simultaneously** (e.g., Eric + Cody + Hamilton), each gets their own Oracle account, VPS, domain, and stack
- **Batch the work**: 3 concurrent sub-agents via `delegate_task(tasks=[...])`, one per client project
- Each sub-agent handles the full pipeline: email creation → Oracle account signup → VPS provisioning → Docker install → project transfer → env config → Docker deploy → domain DNS → SSL verification
- The parent agent: orchestrates the batch, collects results, reports status per project
- Oracle free tier limits per account: 4 ARM OCPUs / 24GB RAM across up to 4 VMs + 2 AMD micro VMs
- **Sub-agent context must include:** the client's project path, the fresh email credentials, the Oracle signup region (US-ASHBURN-1 is most likely to have ARM availability), and the full `.env` template with generated secrets
- Verify each deployment independently: curl the domain, check SSL, test a page load, then report all results in a single summary table

## 📋 Full Deployment Workflow

### Phase 1: Provision VPS

```python
# OCI Python SDK — launch Ampere A1 instance
from oci.config import from_file
from oci.core import ComputeClient
from oci.core.models import (
    LaunchInstanceDetails, InstanceSourceViaImageDetails,
    LaunchInstanceShapeConfigDetails, CreateVnicDetails
)

config = from_file()
compute = ComputeClient(config)

# Read SSH public key
with open('path/to/id_rsa.pub') as f:
    ssh_key = f.read().strip()

launch = LaunchInstanceDetails(
    compartment_id=config['tenancy'],
    display_name='app-name',
    shape='VM.Standard.A1.Flex',
    shape_config=LaunchInstanceShapeConfigDetails(ocpus=2, memory_in_gbs=12),
    source_details=InstanceSourceViaImageDetails(
        image_id='<ubuntu-24.04-aarch64-oci-image-id>'
    ),
    availability_domain='oRwF:US-ASHBURN-AD-1',
    create_vnic_details=CreateVnicDetails(
        subnet_id='<public-subnet-id>',
        assign_public_ip=True
    ),
    metadata={'ssh_authorized_keys': ssh_key},
    freeform_tags={'Project': 'app-name', 'Environment': 'production'}
)
response = compute.launch_instance(launch)
instance_id = response.data.id
```

**Common OCI images:**
- Canonical Ubuntu 24.04 aarch64: `ocid1.image.oc1.iad.aaaaaaaaioyy7je3vndsccly24frkfptl5lggvyupubg74awcf2gmua7k3ra`

**Get active instance IP:**
```python
vnics = compute.list_vnic_attachments(config['tenancy'], instance_id=instance_id)
vnic = vcn_client.get_vnic(vnics.data[0].vnic_id)
public_ip = vnic.data.public_ip
```

**⚠️ Pitfall: Availability Domain** — OCI instances require `availability_domain` in the launch details (e.g., `'oRwF:US-ASHBURN-AD-1'`). Get available domains via `identity.list_availability_domains()`.

**⚠️ Pitfall: Out of host capacity (Ampere A1)** — Oracle free tier Ampere A1 instances in us-ashburn-1 frequently return "Out of host capacity" across ALL availability domains. This is a demand-driven issue that opens and closes unpredictably. Mitigation strategies:

1. **Try all 3 ADs** — don't stop at AD-1, try AD-2 and AD-3
2. **Reduce OCPU count** — capacity is more likely at 1-2 OCPU than 4. Resize to 4 after provisioning (stop instance, change shape config, start)
3. **Retry loop** — capacity opens at random times. Run a loop that tries all 3 ADs every 5-10 minutes until it succeeds:
   ```bash
   for ad in "oRwF:US-ASHBURN-AD-1" "oRwF:US-ASHBURN-AD-2" "oRwF:US-ASHBURN-AD-3"; do
     oci compute instance launch ... --availability-domain "$ad" ... 2>&1
     if ! grep -q "Out of host capacity"; then break; fi
     sleep 300
   done
   ```
4. **Lower provisioned size first** — even 1 OCPU / 6 GB may succeed when 4/24 doesn't. Resize after the instance is RUNNING.
5. **Different region not possible on free tier** — OCI free tier accounts can only subscribe to 1 region. You cannot switch regions without upgrading to a paid account.
6. **Expected wait time** — can be minutes or days. Set up an unattended retry loop and proceed with other work.
7. **PAYG upgrade trick** — The most effective fix for persistent "Out of host capacity" is upgrading to Pay-As-You-Go. Always Free resources remain $0/mo, but you get access to the paid capacity pool (much more availability) AND can subscribe to additional regions (us-phoenix-1, etc.) with better Ampere A1 capacity. Upgrade via OCI Console: Account Management → Upgrade and Manage Payment.

**⚠️ Pitfall: Single region limit** — Only us-ashburn-1 is subscribed. You cannot subscribe to additional regions on a free tier account (`TenantCapacityExceeded`).

### Phase 2: Install Stack

```bash
# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu

# Caddy
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update && sudo apt-get install caddy

# Node.js 22 (ARM64)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**⚠️ Pitfall: dpkg lock** — On a fresh Ubuntu boot, `apt-get` may block for 10+ min waiting for `unattended-upgrades`. Wait it out or run `sudo systemctl stop unattended-upgrades` first.

### Phase 3: Project Transfer

```bash
# Copy project to VPS (tar over SSH — no rsync needed on Windows)
cd /path/to/project
tar czf - --exclude='node_modules' --exclude='.next' --exclude='.git' --exclude='*.log' --exclude='dist' . | \
  ssh -i ~/.ssh/oracle_vps ubuntu@<IP> "tar xzf - -C /home/ubuntu/<app-name>/"
```

### Phase 4: Dockerfile for Next.js

```dockerfile
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install --legacy-peer-deps    # ⚠️ Many Next.js projects have peer dep conflicts

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV production
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
RUN mkdir .next && chown nextjs:nodejs .next
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
ENV PORT 3000
ENV HOSTNAME "0.0.0.0"
CMD ["node", "server.js"]
```

**Critical: `next.config.mjs` must have** `output: 'standalone'` for the Dockerfile above to work.

**⚠️ Pitfall: Missing dependencies** — If the build fails with `Module not found: Can't resolve 'leaflet'` or similar, check `package.json` for missing deps. The code imports packages that aren't in the manifest. Add them with `npm pkg set`.

### Phase 5: Docker Compose

```yaml
services:
  app:
    build: .
    container_name: myapp
    ports: ["3000:3000"]
    env_file: .env.production
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    # ... standard postgres config with healthcheck
```

### Phase 6: Caddyfile

```caddy
app.example.com {
    reverse_proxy 127.0.0.1:3000    # ⚠️ NOT app:3000 — Caddy runs on HOST
}

www.app.example.com {
    redir https://app.example.com{uri} permanent
}
```

**⚠️ CRITICAL: Caddy proxy target** — When Caddy is installed on the HOST (not in Docker), use `127.0.0.1:3000` or `localhost:3000`, NOT the Docker service name `app:3000`. Docker compose network names only resolve inside the Docker network. Caddy can run inside Docker compose (using Docker service names via `caddy:2` image) OR on the host (using localhost) — pick ONE pattern and stick with it. If you install Caddy natively, you use localhost. If you want Docker service names, run Caddy as a Docker container in the compose stack.

### Phase 7: Security

```bash
# UFW
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Auto security updates
sudo dpkg-reconfigure --priority=low unattended-upgrades

# Fail2Ban
sudo apt-get install -y fail2ban
```

### Phase 8: DNS

- Update the A record on the domain registrar to point to the VPS public IP
- For Namecheap: Dashboard → Domain List → Advanced DNS → Edit A record
- DNS propagation takes 5-30 minutes
- Caddy automatically provisions Let's Encrypt SSL once DNS resolves

## 🔍 VPS Infrastructure Audit (Existing VPS)

When asked to investigate a running VPS, take inventory of an existing deployment, check if it can handle additional services, or diagnose a 502/service-down issue:

### Phase 1: Connect & Take Inventory

One-shot diagnostic that covers the full picture in a single SSH call:

```bash
ssh -i ~/.ssh/oracle_vps -o StrictHostKeyChecking=no ubuntu@<IP> "
  hostname && echo '===UPTIME===' && uptime &&
  echo '===DOCKER PS (running)==' && docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' &&
  echo '===DOCKER PS (all incl stopped)==' && docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' &&
  echo '===DOCKER IMAGES==' && docker images &&
  echo '===DOCKER NETWORKS==' && docker network ls &&
  echo '===PORTS===' && sudo ss -tlnp | grep -E ':(80|443|3000|3001|3004|3100|4000|5000|5432|6379|8000|8080|8081|8443|9000)' &&
  echo '===DISK===' && df -h / &&
  echo '===MEMORY===' && free -h &&
  echo '===CPU===' && nproc &&
  echo '===SWAP===' && swapon --show
" 2>&1
```

**Key things to look for:**
- **Memory**: `free -h` shows total vs available. Oracle free tier AMD has ~956MB; Ampere A1 can have up to 24GB.
- **Disk**: `df -h /` — Docker images can consume 5-10GB; leave at least 5GB headroom for builds.
- **CPU**: `nproc` vs `uptime` load average — if load > core count, the VPS is saturated.
- **Swap**: If `swapon --show` is empty, there's **no swap**. Add it before deploying memory-intensive services.
- **Port clashes**: Look for already-listed ports that your new service needs.

**⚠️ Pitfall — `sudo` from non-TTY SSH:** Some SSH configurations block `sudo` without a TTY. Use `-o RequestTTY=no` sparingly; if sudo commands fail, try them without sudo first or use `ssh -t` for pseudo-TTY allocation.

**⚠️ Pitfall — Git push from VPS without SSH key:** VPS deployments often lack SSH keys for GitHub. When you need to push changes from the VPS (e.g., after modifying a deployed project):

1. Set git identity on the fresh VPS:
   ```bash
   cd /opt/project
   git config user.email 'you@example.com'
   git config user.name 'Your Name'
   ```

2. Use HTTPS with token auth (since SSH keys are on your local machine, not the VPS):
   ```bash
   # Set remote URL with token embedded (one-time push)
   git remote set-url origin https://oauth2:YOUR_GITHUB_TOKEN@github.com/owner/repo.git
   git push origin main
   
   # RESET the URL after push to avoid leaving credentials in config
   git remote set-url origin https://github.com/owner/repo.git
   ```

3. If the remote has diverged (rebase needed):
   ```bash
   git pull --rebase origin main
   # Resolve any conflicts, then:
   git push origin main
   ```

4. Get your token: `gh auth token` on your local machine (where `gh` is authenticated).

**⚠️ Pitfall — Caddy port mismatch:</strong>** When Caddy proxies to a service you're also setting up, the port in Caddy's `reverse_proxy` directive may reference a port that doesn't match the actual running service (e.g., Caddy says `172.17.0.1:3001` but spacebar runs on 3100). Cross-reference every Caddy upstream target against `ss -tlnp` output. This is the single most common cause of "DNS resolves but site returns 502". If you fix a port mismatch, reload Caddy with `sudo docker exec <container> caddy reload --config /etc/caddy/Caddyfile`.

**⚠️ Pitfall — Caddy config location:** Caddy may run as a Docker container with the Caddyfile bind-mounted from a host path (e.g., `docker run -v /home/ubuntu/Caddyfile:/etc/caddy/Caddyfile`). Always check both `cat /etc/caddy/Caddyfile` (inside container) and `cat /home/ubuntu/Caddyfile` (host bind source). Edit the bind source on the host, then reload inside the container. Do not use `sed` inside the container — the bind mount is one-way and changes to the container's file won't persist.

**⚠️ Pitfall — `sed` global replace DESTROYS multi-route configs:** When using `sed 's|OLD|NEW|g'` on a Caddyfile that has multiple `reverse_proxy` directives targeting the same address, the `g` (global) flag replaces EVERY occurrence, not just the intended one. If you run `sed -i 's|172.17.0.1:3100|172.17.0.1:3456|g' /home/ubuntu/Caddyfile` thinking you're only changing the avatar route, you'll also silently rewrite the API, WebSocket, file, and CDN routes — breaking login and all other API-dependent features. **Fix:** Use `sed` without `g` (replaces first occurrence only) or edit the specific block manually. After any `sed` operation on a proxy config, verify EVERY changed line matches what you intended:
   ```bash
   grep -c '3100' /home/ubuntu/Caddyfile  # count of remaining references to old port
   grep -c '3456' /home/ubuntu/Caddyfile  # count of new port references
   # Then inspect every changed line:
   grep -n '3456' /home/ubuntu/Caddyfile
   ```

**⚠️ Pitfall — `ss` vs `netstat`:** Modern Linux ships `ss` instead of `netstat`. Use `ss -tlnp` for listening TCP ports with process info.

### Phase 2: Read Proxy Config

Find and read the reverse proxy configuration to understand routing, domains, and upstream targets:

```bash
# Check both system-level and user-level locations
ssh ... "cat /etc/caddy/Caddyfile 2>/dev/null; echo '---'; cat ~/Caddyfile 2>/dev/null"
ssh ... "sudo cat /etc/nginx/sites-enabled/* 2>/dev/null"
ssh ... "docker inspect <proxy-container> 2>/dev/null | grep -A10 'Networks'"
```

**Key config patterns:**
- **Multi-domain routing**: One Caddyfile may serve multiple domains (`hamilton.com { ... }`, `discy.domain { ... }`) on different backends — this is how co-hosting works
- **handle vs handle_path**: `handle_path` strips the matched prefix before proxying (often unintentional — use `handle` with `@api path /api/*` instead)
- **172.17.0.1 vs 127.0.0.1**: Docker containers use `172.17.0.1` (Docker bridge gateway) to reach the host; `127.0.0.1` inside a Docker container loops back to the container itself
- **Comments reveal purpose**: Caddyfile comments like `# Fermi UI` or `# API` label the purpose of each route

### Phase 3: DNS Audit

When a domain has DNS pointing to the VPS but returns 502/offline:

```bash
# What IPs does the domain resolve to?
dig +short domain.com

# What IP does the VPS actually have?
ssh ... "hostname -I | awk '{print \$1}'"

# Does the domain match any of the VPS's IPs?
```

**⚠️ Multiple A records = round-robin multi-homing.** If DNS returns BOTH a home ISP IP (e.g., Charter, Comcast) AND the VPS IP, traffic splits across both endpoints. One may have the services running while the other doesn't.

**Cross-reference workflow:**
1. Identify all domains configured in the proxy (from Phase 2)
2. Resolve each domain via `dig +short`
3. Match resolved IPs against the VPS IP
4. For domains that DO resolve to the VPS, check if they actually respond:
   ```bash
   curl -sI https://domain.com 2>&1 | head -5
   # → HTTP 200 = service up
   # → HTTP 502 = Caddy/nginx up but backend down
   # → timeout = proxy not responding to that domain
   ```

### Phase 4: Detect "Configured But Not Running" Services

Cross-reference the proxy config against running Docker containers and listening ports:

1. **Extract all upstream targets** from the proxy config (e.g., `reverse_proxy 172.17.0.1:3001` → target port `3001`)
2. **Check each target**: `ssh ... "ss -tlnp | grep :3001"`
3. **If a port has no listener** but IS configured in the proxy → **configured but not running** → returns 502 Bad Gateway
4. **Check for stopped/exited containers** that match the configured services:
   ```bash
   docker ps -a --filter 'status=exited' --format '{{.Names}} {{.Image}} {{.Status}}'
   ```

This is the most common deployment gap: DNS + proxy config are in place, but the backend services were never deployed or crashed.

### Phase 4b: Detect Zombie Processes (Running but Serving Nothing)

A process can be alive and consuming memory but bound to **no listening ports** — it's a zombie that wastes resources. Common case: **duplicate Caddy instances** where one Docker Caddy handles all traffic while a host-level Caddy runs with no config file and no listening sockets.

Detection pattern — cross-reference process list against listening ports:

```bash
# 1. List all listening ports with PIDs
ss -tlnp

# 2. Check which processes handle ports 80/443
ss -tlnp | grep -E ':80 |:443 '

# 3. List all Caddy/nginx processes
ps aux | grep -E 'caddy|nginx' | grep -v grep

# 4. If docker-proxy holds 80/443 AND a native caddy has no listening ports → zombie
# Kill confirmed zombie (after verifying it serves no traffic):
sudo kill <PID>
# Confirm RSS freed via free -m or ps
```

**Zombie Caddy litmus test:**
```bash
# Does the host Caddy actually serve anything?
sudo ss -tlnp | grep caddy
# Empty output = zombie (no listening ports)

# Does docker-proxy hold all public ports?
sudo ss -tlnp | grep -E ':80 |:443 '
# Should show docker-proxy PID(s)
```

**Expected resource savings:** Killing one zombie Caddy typically frees ~50-96 MB RSS and ~1-2% CPU.

### Phase 5: Co-Hosting Resource Analysis

Before adding a new service to an existing VPS, determine whether it fits:

**Step 1 — Estimate current memory usage per running component:**

| Component | Est. Memory |
|-----------|-------------|
| Caddy/nginx reverse proxy | ~20MB |
| PostgreSQL 16-alpine | ~100-150MB |
| Redis 7-alpine | ~10-20MB |
| Node.js app (Spacebar, Next.js) | ~100-200MB |
| Node.js static frontend server | ~20-50MB |
| RustDesk hbbs/hbbr | ~15MB each |
| Python web app (FastAPI, Flask) | ~50-100MB |
| Hermes bot gateway (discord.py + Hermes) | ~70MB each (baseline) |

**Fleet planning formula:** `N bots × 70MB = total gateway RAM`
- 39 bots = ~2.7 GB RAM on the local machine (trivial for a 64GB desktop)
- Each bot adds ~50-100KB RSS to Spacebar's Node.js process (WSS connection overhead) — negligible
- **CPU impact on VPS from bot fleet:** WSS connections + heartbeats from 39 bots can push a 1-OCPU VPS over its limit. The bottleneck is VPS CPU, not RAM. Bots should run locally and connect to VPS via WSS only.

**Step 2 — Calculate headroom:**
```
Headroom = MemAvailable (from free -h) - Estimated new service memory
```

**Step 3 — Decision guide:**
- **Headroom > 300MB**: Deploy freely with docker memory limits
- **Headroom 100-300MB**: Deploy but ADD SWAP (2GB) first, pin container memory limits
- **Headroom < 100MB**: Too tight — upgrade VPS, reduce existing footprint, or don't deploy
**Step 4 — Add swap as safety net:**

```bash
# 2GB swap file (safe for Oracle free tier with small boot volume)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

**For Node.js apps on the OCI Micro tier (956MB RAM, 45GB disk), increase swap to 8GB:**
```bash
sudo swapoff -a
sudo dd if=/dev/zero of=/swapfile bs=1M count=8192 status=progress
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```
This uses ~8GB of disk, leaving ~22GB free on a 45GB boot volume with 16GB used. The 8GB swap provides a large safety net for Node.js memory spikes (TypeScript builds, schema generation, heavy GC) and allows co-hosting multiple services (Spacebar ~120MB + Fermi ~50MB + existing ~180MB) comfortably.

**⚠️ Pitfall — Boot volume size:** Oracle free tier boot volumes can be as small as 40-45GB. A 2GB swapfile on a 45GB disk with 16GB used leaves ~27GB — fine. But on a 40GB disk with heavy Docker usage, swap + images + volumes can fill the disk. Check `df -h /` before allocating.

**Step 5 — Set container memory limits:**
```yaml
services:
  spacebar:
    deploy:
      resources:
        limits:
          memory: 256M
    # or in plain docker compose without deploy:
    # mem_limit: 256m
```

This prevents any single container from OOM-killing the host.

**Shared PostgreSQL pattern:** If the VPS already runs PostgreSQL for another app, create a new database/schema for the new service instead of running a second PG container. Saves ~100-150MB per avoided container.

### Phase 6: Report

Structure the report as a table:

| Aspect | Finding |
|--------|---------|
| VPS hostname, OS, CPU, RAM, Disk | From Phase 1 |
| Existing services (running) | Phase 1 output |
| Services configured but not running | Phase 4 |
| DNS status | Phase 3 |
| Resource availability | Phase 5 |
| Recommendation | Go/No-go with conditions |

## 🔁 Subagent Delegation for Deployments

When delegating VPS deployment work to subagents, use **sequential direct SSH commands**, not a single long-running `docker compose up -d --build` call. Subagents have a 600s timeout and a single long Docker build may exceed it.

**Preferred pattern:**
```python
# Step 1: Install deps (in foreground)
# Step 2: Build Docker (background with notify)
# Step 3: Verify (after build completes)
```

**Never** pass a `docker compose up -d --build` into a single terminal call inside a delegatation — split it into `build` then `up -d` phases so you can wait between them.

## 🚨 Spacebar Server Recovery

When Spacebar (sb-bundle) stops responding to REST API requests but the port is still listening:

| Symptom | Likely Cause |
|---------|-------------|
| Gateway endpoint (200) fast but login/auth times out | Main API thread stuck |
| `ss -tlnp` shows port 3100 listening | Process alive but non-responsive |

```bash
# Recovery: kill ALL sb-bundle processes, then restart
kill -9 $(pgrep -f 'sb-bundle') 2>/dev/null
sleep 2
ss -tlnp | grep 3100 || echo 'Port free'
cd /opt/spacebar
nohup node --enable-source-maps dist/bundle/start.js >> spacebar.log 2>&1 &
sleep 10
curl -s --max-time 10 http://localhost:3100/api/v9/gateway
```

**Pitfall — EADDRINUSE:** Old sb-bundle may survive `kill -9`. Check `ss -tlnp` for the exact PID, kill it specifically.

**Pitfall — Cron watchdog:** Cron restarts Spacebar every 5min if `pgrep -f "dist/bundle/start"` fails. Verify the living PID matches after manual restart.

### VPS Resource Table (Oracle E2.1.Micro — 956MB, 1 OCPU)

Live-measured example from an actual the operator deployment:

| Component | RSS | %RAM | Note |
|-----------|-----|------|------|
| Spacebar (sb-bundle-3100) | ~241 MB | 25.2% | 85% CPU — Node.js |
| Docker Caddy (hmac-caddy) | ~80 MB | 8.3% | 9-39% CPU anomaly — serves all 3 domains |
| **Host Caddy (zombie)** | **~50-96 MB** | **5-10%** | **Zero listening ports — no Caddyfile — free kill** |
| Fermi (Node.js web client) | ~96 MB | 10% | 35% CPU |
| Docker PostgreSQL | ~39 MB | 4.0% | 29% CPU — ~10 connections |
| Docker Redis | ~1 MB | 0.1% | |
| Docker RustDesk (hbbs/hbbr) | ~1 MB | 0.1% | |
| Oracle cloud agents (3) | ~28 MB | 3% | Cannot remove |
| containerd + dockerd | ~27 MB | 3% | Docker infrastructure |
| System services | ~25 MB | 3% | systemd, sshd, journald |
| **Total used** | **~620 MB** | **65%** | **~190 MB free, 330 MB swap in use** |

**Key insight — Two Caddys found:** The Docker Caddy already serves ALL 3 domains (discy.your-domain.example, gc.your-domain.example, hamiltonmobileautocare.com). The native host Caddy had no listening ports and no Caddyfile — pure zombie. One Caddy is sufficient for unlimited domains.

**Bot capacity:** 0-3 max on this tier. CPU is the bottleneck (1 OCPU at 85%), not RAM. Bots run on local machine, connect to VPS via WSS only.

**Always check for zombie processes** when auditing a VPS — look for long-running processes with no listening ports. They waste memory for zero benefit.

## 🔧 Post-Deployment App Customization

Workflow for modifying an **already-deployed** web application's source code on the VPS — rebranding, changing behavior, or fixing issues after initial deployment.

### Locating the Deployed App's Source

When the user says "customize X" and X is already running on the VPS:

```bash
# 1. Find the running process
ps aux | grep node | grep -v grep

# 2. Get the source directory (real path, not symlink)
readlink -f /proc/<PID>/cwd

# 3. Check the executable/startup command
cat /proc/<PID>/cmdline | tr '\0' ' '

# 4. Verify you're in the right place
ls dist/package.json src/ 2>/dev/null
```

Common patterns for where apps live:
- Next.js apps: `/home/ubuntu/<app-name>/` or `/var/www/<app-name>/`
- Node.js services: `/opt/<app-name>/` or `/home/ubuntu/<app-name>/`
- Dockerized: inside `docker exec` or via bind mount paths in `docker inspect`

### ⚠️ CRITICAL: Editing JSON Files via SSH

**DO NOT use shell heredocs for JSON.** The shell strips double quotes from JSON property names and string values, producing invalid JavaScript object literals instead of valid JSON:

```bash
# ❌ WRONG — shell heredoc strips quotes
cat > file.json << 'EOF'
{"name": "My App"}   # becomes {name: My App}
EOF

# ✅ RIGHT — Python json.dump on the remote
ssh user@host "python3 << 'PYEOF'
import json
with open('/opt/app/config.json', 'w') as f:
    json.dump({'name': 'My App'}, f, indent=2)
PYEOF"

# ✅ ALSO WORKS — write to a temp Python script file first
ssh user@host "cat > /tmp/fix.py << 'XYZ'
import json
... json.dump ...
XYZ
python3 /tmp/fix.py && rm /tmp/fix.py"
```

**Why it happens:** The SSH layer's quote handling respects single-quote heredoc delimiters (`'EOF'`) for shell variables but double quotes inside JSON values (`"key"`) are still consumed by the shell's string parsing before reaching Python or the file. Python's `json.dump` is immune because it generates the quotes itself.

### Branding Customization Checklist

When rebranding an existing web app:

| Element | Typical Location | What to Change |
|---------|----------------|----------------|
| Logo | `logo.svg` or `logo.webp` | Replace SVG content entirely |
| Favicon | `favicon.ico` + `<link rel="icon">` | Upload new binary, update `<link>` if needed |
| HTML Title | `<title>` in main HTML files | Update per page (app.html, index.html, etc.) |
| Loading text | Translation file (`en.json`) or inline HTML | Update the string value |
| Theme color | `<meta name="theme-color">` | Change to brand primary color |
| App/Manifest name | `manifest.json` | Update `name`, `short_name`, `description` |
| OG meta tags | `<meta property="og:title">` etc. | Update for link previews |
| Server/instance list | Config JSON (e.g., `instances.json`) | Update display name, add `image` field |
| Favicon | `manifest.json` icons array + HTML | Ensure favicon is referenced correctly |

**Finding all "old brand" references across the codebase:**
```bash
grep -rn 'OldBrand' src/ --include='*.html' --include='*.json' --include='*.ts' --include='*.js'
# Then repeat for translations directory
grep -rn 'OldBrand' translations/ --include='*.json'
```

### Translation/String Customization (i18n)

For i18n-enabled apps, user-facing strings live in translation files:

1. **Find the translation file:** usually `translations/en.json`, `locales/en.json`, `src/webpage/translations/en.json`
2. **Identify visible strings** — the loading screen text, titles, install prompts are the most user-facing:
   - `loadingText`: "App is loading" → brand name
   - Blog/contribute/translate section titles
   - "sent via" / "powered by" footers
3. **Edit technique:** Read with `json.load`, modify dict values, write with `json.dump` — never sed/heredoc
4. **Rebuild** after editing: `npm run build` (build process copies translations to dist)

### Rebuild & Restart Workflow

After modifying source files (HTML, TS, translations, images):

```bash
# 1. Rebuild the project
cd /opt/<app> && npm run build

# 2. If any config files aren't bundled by the build script, copy manually
cp src/webpage/config.json dist/webpage/

# 3. Find and kill the old process
kill $(ps aux | grep 'node dist/index' | grep -v grep | awk '{print $2}')

# 4. Start the new process (matching the original port)
cd /opt/<app> && PORT=<original-port> node dist/index.js > /dev/null 2>&1 &

# 5. Verify it's running
sleep 2
curl -s -o /dev/null -w '%{http_code}' http://localhost:<port>/
```

**Key verification:** The first request to a Node.js server should return HTTP 200 or 302 (if it redirects). If you get `000` (curl exit code 7), the process crashed. Check logs with `tail -20 /proc/<PID>/fd/1` or redirect output.

### Git Push from Headless VPS

Deployed VPS instances rarely have SSH keys for GitHub. Use this pattern:

```bash
# 1. Set git identity (only needed once per VPS)
git config user.email '<email>'
git config user.name '<name>'

# 2. Pull latest upstream changes before committing
git fetch origin main
git pull --rebase origin main
# If conflicts: fix them, git add, git rebase --continue

# 3. Push with HTTPS + token auth
# Get token from local machine: gh auth token
git remote set-url origin https://oauth2:<TOKEN>@github.com/<owner>/<repo>.git
git push origin main
# ⚠️ RESET the URL to clean HTTPS after push
git remote set-url origin https://github.com/<owner>/<repo>.git
```

**Pitfall — upstream advanced:** If the remote has commits you don't have locally, rebase (not merge) to keep history clean. The rebase may reapply your commit on top of the new remote state.

### Deploy Pitfall: Dist Overwrite Destroys Custom Branding/Config

**WHEN the project build outputs to `dist/` and custom files (branding images, `instances.json`, HTML templates) exist only in the source directory or were manually added to `dist/` in a previous deploy:**

1. **`npm run build` regenerates `dist/` from scratch.** Any custom files that were manually copied into a previously deployed `dist/` are wiped. The only thing the build knows about is what's in `src/` and tracked by git.

2. **Always diff old vs new dist BEFORE deploying:**
   ```bash
   cd /opt/<app>
   mv dist dist-old
   npm run build
   diff <(cd dist-old && find . -type f | sort) <(cd dist && find . -type f | sort)
   ```
   Any files in the left column (old dist only) that aren't build artifacts — branding images, instance config, custom HTML — must be manually copied into the new dist.

3. **Files most commonly lost:**
   - `backus-*.webp`, `backus-*.png` — custom logos/avatars
   - `instances.json` — correct API URL, display name, instance config
   - Custom HTML files with brand-specific `<title>`, meta tags
   - `manifest.json` — app name, icons, short name

4. **To prevent permanently**, either:
   - **Commit branding files to the repo** so they're part of the build (best for single-instance deployments)
   - **Use a post-deploy script** that copies branding from `/opt/<app>/branding/` (a directory outside the build tree, not tracked by git) after each rebuild
   - **Wrap the build in a shell script** that saves, builds, then restores custom files

5. **Always restart the service after a dist update.** Node.js caches required modules — just replacing files doesn't take effect until the process restarts.

### Subagent Pattern for Customization Tasks

For complex multi-file customization work, delegate independent workstreams in parallel:

```python
tasks=[
    {"goal": "Fix server routing (redirect / to /app endpoint)",
     "context": "Edit src/index.ts, change route handler"},
    {"goal": "Create custom logo and update favicon",
     "context": "Replace SVG logo, update favicon"},
    {"goal": "Rebrand all HTML templates and translation files",
     "context": "Replace brand name throughout"},
    {"goal": "Rebuild dist and restart server",
     "context": "npm run build, kill old process, start new one"},
]
for result in delegate_task(tasks=tasks):
    ...
```

Each sub-agent should be fully self-contained with: app path, port, file paths, the exact changes to make. Chain them if the build step depends on source changes.

## Hybrid VPS + Local GPU Architecture

When deploying an AI agent stack where the VPS handles 24/7 text services and the local machine handles GPU workloads (LLM inference, STT, TTS), use this hybrid pattern.

### Architecture

```
┌─────────────────────────────────────┐       Tailscale VPN       ┌──────────────────────────────┐
│   Oracle Cloud Ampere A1            │◄──────────────────────────►│   Local Windows Machine       │
│   4 ARM cores · 24 GB RAM           │                            │   RTX 3090 · 47 GB RAM       │
│   200 GB storage · $0/mo            │                            │                              │
│                                     │                            │   ┌──────────────────────┐   │
│   ┌─────────────────────────┐       │                            │   │ llama.cpp / ollama   │   │
│   │ Hermes Agent (Python)   │       │   HTTP API calls           │   │ whisper / TTS        │   │
│   │ Gateway (Discord/Tele)  │       │◄──────────────────────────►│   │ Docker stack (CRM)   │   │
│   │ Postgres / Redis        │       │                            │   └──────────────────────┘   │
│   │ MemPalace               │       │                            │                              │
│   │ MCP Servers (non-GPU)   │       │                            │                              │
│   └─────────────────────────┘       │                            └──────────────────────────────┘
└─────────────────────────────────────┘
```

### What Goes Where

**VPS (Always-On):**
| Service | Est. RAM | Notes |
|---------|----------|-------|
| Hermes Agent | ~200 MB | Core conversation loop |
| Hermes Gateway | ~100 MB | Discord/Telegram 24/7 bridge |
| Postgres | ~50 MB | Session DB + structured storage |
| MemPalace MCP | ~100 MB | Persistent memory |
| MCP servers | ~50-100 MB | Non-GPU MCP servers |
| Traefik reverse proxy | ~70 MB | Route traffic |

**Local GPU Machine:**
| Service | Why Local |
|---------|-----------|
| LLM inference (llama.cpp, ollama) | GPU required |
| Whisper STT | GPU preferred |
| TTS | Heavy CPU/GPU |
| Docker business stack | CRM, n8n, Budibase |

### Tailscale VPN Setup

```bash
# On VPS:
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# On local Windows machine — install from https://tailscale.com/download
# Both join the same Tailscale network
# Note the Tailscale IPs (100.x.x.x) for service connections
```

### Alternative: SSH Reverse Tunnel (if Tailscale unavailable)

```bash
# On local machine:
ssh -N -R 8081:localhost:8080 ubuntu@<vps-ip> -i ~/.ssh/vps_key
```

Then configure Caddy on VPS to proxy `your-domain.com → 127.0.0.1:8081`. Requires `GatewayPorts yes` in sshd_config on VPS.

For a persistent tunnel with auto-reconnect:
```bash
#!/bin/bash
while true; do
  ssh -i "$KEY" -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
    -o ExitOnForwardFailure=yes \
    -N -R 0.0.0.0:3001:localhost:3001 user@vps &
  wait -n
  kill $(jobs -p) 2>/dev/null
  sleep 3
done
```

### Connecting Local GPU to VPS Agents

In the VPS Hermes config.yaml, point LLM endpoints to the local machine's Tailscale IP:

```yaml
mcp_servers:
  local-llm:
    url: http://100.XX.XX.XX:11434  # Ollama on local machine
  local-whisper:
    url: http://100.XX.XX.XX:9000   # Whisper on local machine
```

### VPS Resource Profiling

Before deploying any service, profile the VPS:

```bash
shape=$(curl -s http://169.254.169.254/opc/v1/instance/ | python3 -c \
  "import sys,json; print(json.load(sys.stdin).get('shape','?'))" 2>&1)
echo "Shape: $shape"
echo "RAM: $(free -h | awk '/Mem:/{print $2}')"
echo "Disk: $(df -h / | awk 'NR==2{print $2, $4 \" free\"}')"
echo "Swap: $(swapon --show | awk 'NR==2{print $3}' || echo 'none')"
```

**Two Oracle Free Tier shapes co-exist:**
- **Micro** (VM.Standard.E2.1.Micro, ~956 MB RAM, 1 x86 core) — very constrained; increase swap to 8GB, use memory limits
- **Ampere A1** (VM.Standard.A1.Flex, up to 24 GB RAM, 4 ARM cores) — ample resources

See `references/vps-resource-audit-methodology.md` for complete per-process breakdown.

### Bot Fleet Capacity on VPS

**Key insight from live measurement:** Each Hermes gateway process loads discord.py + all 28+ plugins (~70 MB baseline). On a 956 MB Micro VPS, Spacebar itself uses 241 MB + 85% CPU — no room for gateways. On an Ampere A1 with 24 GB, the fleet runs fine.

| Metric | Per Bot | 39 Bots | Micro VPS | A1 4/24 |
|--------|---------|---------|-----------|---------|
| Baseline RSS | ~70 MB | ~2.7 GB | ❌ Exceeds RAM | ✅ 11% |
| Idle CPU | ~0.5% | ~20% | ❌ 20% on 1 core | ✅ Fine on 4 cores |

**Rule:** Bots run on local machine, connect to VPS via WSS only. The VPS bottleneck is Spacebar's single-core Node.js event loop.

### Swap Sizing for Micro VPS

```bash
sudo swapoff -a
sudo dd if=/dev/zero of=/swapfile bs=1M count=8192 status=progress
sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Console Window Suppression (Windows bot fleet)

```python
# Swap to pythonw.exe (no console) for gateway processes:
HERMES_VENV_PYTHON = os.path.expanduser(
    "~/AppData/Local/hermes/hermes-agent/venv/Scripts/pythonw.exe"
)
```

### Oracle Cloud Two-Layer Firewall

Oracle has two independent firewalls: VCN security lists AND instance iptables. Opening ports in iptables alone is not enough:

```bash
# SSH into VPS and add iptables rules (inserted BEFORE the REJECT rule):
sudo iptables -I INPUT 7 -i docker0 -p tcp --dport 3001 -j ACCEPT
# Then persist:
sudo iptables-save | sudo tee /etc/iptables/rules.v4

# Also add VCN ingress rules via OCI Console or CLI
oci network security-list update \
  --security-list-id <sl-id> \
  --ingress-security-rules file:///rules.json \
  --force
```

See `references/oci-firewall-two-layer.md` for the complete CLI workflow.

### Migration: Micro → Ampere A1 (Zero Downtime)

When upgrading from Micro shape to Ampere A1:

**Phase 1 — Backup on old VPS:**
```bash
# Dump PostgreSQL
docker exec <pg> pg_dump -U user -d db --clean --if-exists -f /tmp/dump.sql
docker cp <pg>:/tmp/dump.sql /home/ubuntu/dump.sql
gzip /home/ubuntu/dump.sql

# Backup configs
cp /opt/spacebar/config.production.json /home/ubuntu/config.json.bak
cp /home/ubuntu/Caddyfile /home/ubuntu/Caddyfile.bak
```

**Phase 2 — Provision Ampere A1** (see Phase 1 above for OCI SDK patterns)

**Phase 3 — Deploy stack on Ampere:**
```bash
# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu

# Clone projects
git clone https://github.com/pmb2/spacebar.git /opt/spacebar
git clone https://github.com/pmb2/Fermi.git /opt/fermi

# Restore PostgreSQL
gunzip -c dump.sql.gz | docker exec -i <pg> psql -U user -d db
```

**Phase 4 — Cut over:**
1. Test new VPS independently (old still live)
2. Update DNS A record
3. Verify external access
4. Gracefully stop old VPS

### References

- `references/vps-resource-audit-methodology.md` — Complete per-process memory breakdown and bot fleet profiling
- `references/docker-engine-crash-recovery.md` — Docker engine crash (500 Error) full WSL recovery
- `references/expose-local-service-via-ssh-tunnel.md` — SSH tunnel + Caddy config for local→VPS exposure
- `references/oci-firewall-two-layer.md` — Oracle VCN security list + iptables combined setup

## 📦 Key References

- See `references/oci-cli-setup.md` for OCI CLI installation, API key config, and verification
- See `references/oci-provisioning.md` for full OCI SDK patterns
- See `references/oci-ammpere-retry-patterns.md` for OCI CLI setup, capacity retry loops, subscribed region limits, and instance launch commands (fire-and-forget pattern)
- See `references/oci-free-tier-client-onboarding.md` for the non-technical client handoff workflow — gives Cody-style users exact steps to create their own Oracle Free Tier account and VPS and send the operator the credentials/IP
- See `references/docker-nextjs.md` for Dockerfile patterns and peer dep resolution
- See `references/namecheap-dns-setup.md` for Namecheap DNS configuration (A records, CAA, propagation verification)
- See `scripts/setup-vps.sh` — idempotent VPS provisioning script (Docker, Caddy, UFW, Fail2Ban, swap, auto-updates, SSH hardening) — copy to VPS and run after provisioning
- See `references/client-onboarding-system.md` for the agency SOP system — client pipeline, SOP templates, and the client-owned accounts model
- See `templates/Dockerfile.nextjs` — ready-to-use Next.js Dockerfile
- See `templates/docker-compose.yml` — standard compose template
- See `templates/caddyfile` — standard Caddy reverse proxy config (host-mode, points to 127.0.0.1:PORT)
- See `references/spacebar-deployment.md` for Spacebar (Discord-compatible backend) + Fermi UI deployment — non-Next.js Node.js app with Docker Compose, SSH tunnel pattern, and migration path from local to VPS
- See `references/fermi-client-customization.md` for the complete Fermi (Harmony) web chat client rebrand — logo, favicon, i18n, instances.json, login/login page changes
- See `references/fermi-loading-screen-logo.md` for loading screen avatar, instance selector logo, SVG vs WebP conversion, missing file symptoms, and file inventory
- See `references/spacebar-cdn-avatar-serving.md` for the Spacebar CDN route bug and standalone avatar server workaround (broken avatars fix via Node.js static file server + Caddy proxy + iptables + systemd unit)
- See `references/spacebar-admin-tasks.md` for resetting user passwords via DB, managing Spacebar user accounts, and other administrative database operations
- See `references/docker-compose-traefik-deployment.md` for deploying multi-service stacks behind Traefik with Let's Encrypt TLS — env var interpolation traps, FRONTEND_ORIGIN malformation bug (`https://.domain`), ACME provisioning, and Docker build caching pitfalls
- See `references/twenty-crm-deployment.md` for Twenty CRM-specific configuration — env vars that MUST be set (TWENTY_DB_*, booleans, REDIS_URL, APP_SECRET), multi-workspace vs single-workspace routing, the `.crm.your-domain.example` redirect fix, entrypoint CRLF issues, image rebuilding, and startup verification
