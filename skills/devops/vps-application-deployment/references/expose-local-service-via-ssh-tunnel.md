# Expose Local Service via SSH Reverse Tunnel + VPS Caddy

Alternative to Tailscale for making a local Windows service accessible at a public domain via a cloud VPS.

## Architecture

```
User → discy.example.com → VPS (Caddy in Docker) → iptables → SSH tunnel → Local (Windows) :8080
                                                               ↑
                                                     SSH reverse tunnel (-R flag)
                                                     binds VPS:8081 → localhost:8080
```

## Prerequisites

- A VPS with Caddy reverse proxy (Docker or native) — ports 80/443 open
- SSH access from local machine to VPS (private key + public IP)
- A domain/subdomain with A record pointing to the VPS public IP
- Local service already running (e.g., listening on 0.0.0.0:8080)

## Full Setup

### 1. Enable GatewayPorts on VPS SSH Server

This is required when Caddy runs inside Docker because the reverse tunnel needs to bind to `0.0.0.0` (all interfaces) instead of only `127.0.0.1`. Without this, Docker containers cannot reach the tunnel port.

```bash
# On the VPS:
sudo sed -i 's/^#GatewayPorts no/GatewayPorts yes/' /etc/ssh/sshd_config
sudo sed -i 's/^GatewayPorts no/GatewayPorts yes/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# Verify:
sudo sshd -T | grep gatewayports
# Output: gatewayports yes
```

### 2. Add Caddy Route

If Caddy runs in Docker with a bind-mounted Caddyfile (common on this stack):

```bash
# On the VPS:
cat > /home/ubuntu/Caddyfile << 'CADDYEOF'
{
  email admin@example.com
}

existingdomain.com {
  encode gzip
  reverse_proxy 10.0.0.109:80
}

discy.example.com {
  encode gzip
  reverse_proxy 172.17.0.1:8081
}
CADDYEOF

# The proxy target uses Docker bridge gateway IP (172.17.0.1)
# NOT 127.0.0.1 — because Caddy runs inside Docker and localhost
# inside a container is the container itself, not the host.

# Reload Caddy:
docker exec hmac-caddy caddy fmt --overwrite /etc/caddy/Caddyfile
docker exec hmac-caddy caddy reload --config /etc/caddy/Caddyfile
```

**If Caddy serves BOTH a web UI AND an API** (e.g., Fermi + Spacebar), use path-based routing:

```caddy
discy.example.com {
  encode gzip
  route /api/* {
    reverse_proxy 172.17.0.1:3001
  }
  reverse_proxy 172.17.0.1:8081
}
```

This routes `/api/*` to the API backend and everything else to the web UI.

### 3. Add iptables Rule for Docker Bridge Access

This is the critical step that's easy to miss. Docker containers CANNOT reach SSH reverse tunnel ports on the host by default — iptables blocks them. The ACCEPT rule must be inserted **BEFORE** the REJECT rule in the INPUT chain.

```bash
# On the VPS:
# Find the line number of the REJECT rule
sudo iptables -L INPUT -n -v --line-numbers

# Insert ACCEPT rule at the position just before REJECT (typically line 7-8)
sudo iptables -I INPUT 7 -i docker0 -p tcp --dport 8081 -j ACCEPT
sudo iptables -I INPUT 7 -i docker0 -p tcp --dport 3001 -j ACCEPT

# On Ubuntu 24.04+, nftables may also need a rule:
sudo nft insert rule inet filter input position 7 \
  iifname docker0 meta l4proto tcp tcp dport 8081 counter accept

# ⚠️ Do NOT use -A (append) — it adds after the REJECT rule and has no effect.
# Always use -I (insert) with the correct position number.
```

### 4. Persist iptables Rules

```bash
# On the VPS:
# Save rules — they survive reboot:
sudo apt-get install -y iptables-persistent
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

### 5. Create SSH Reverse Tunnel

From the local Windows machine (MSYS/bash):

```bash
# Single tunnel:
ssh -N -R 0.0.0.0:8081:localhost:8080 ubuntu@<vps-ip> -i ~/.ssh/vps_key

# Multiple tunnels (e.g., web UI + API):
ssh -N \
  -R 0.0.0.0:8081:localhost:8080 \
  -R 0.0.0.0:3001:localhost:3001 \
  ubuntu@<vps-ip> -i ~/.ssh/vps_key
```

Key flags:
- `-N` = no remote command (tunnel only)
- `-R 0.0.0.0:PORT:localhost:PORT` = binds to all interfaces on VPS (requires GatewayPorts yes)
- `-o ServerAliveInterval=30` = keepalive ping every 30s
- `-o ExitOnForwardFailure=yes` = abort if port can't be claimed

### 6. Update DNS

Point the subdomain to the VPS's public IP:

| Type | Name | Value |
|------|------|-------|
| A | discy.example.com | <VPS-public-IP> |

## Replacing a VPS Server with a Local Instance (Same-Port Swap)

When you want to replace a running server on the VPS (e.g., Spacebar on port 3100) with a local instance accessible through the same domain, use same-port reverse tunneling. The key difference from the standard tunnel: you must **kill the VPS service first** so the tunnel can claim the port.

### 1. Stop the VPS Server

```bash
# Find and kill the process on the target port
ssh ubuntu@<vps-ip> "lsof -i :3100 | grep LISTEN"
# → node  ...  TCP *:3100 (LISTEN)
ssh ubuntu@<vps-ip> "kill <PID>"

# Verify port is free
ssh ubuntu@<vps-ip> "lsof -i :3100 2>/dev/null || echo 'Port free'"
```

### 2. Start the SSH Reverse Tunnel (Same Port)

```bash
# From local machine:
ssh -i ~/.ssh/vps_key -N -R 3100:localhost:3100 ubuntu@<vps-ip>
```

This binds the VPS's `127.0.0.1:3100` to `localhost:3100` on your local machine. Note: without `0.0.0.0:` prefix, the tunnel binds to `127.0.0.1` only (loopback), NOT all interfaces. Caddy inside Docker accesses the host via `172.17.0.1` (Docker bridge gateway), not `127.0.0.1`.

**If Caddy runs in Docker** and proxies to `172.17.0.1:3100`, you have two options:

- **Option A — GatewayPorts on VPS** (requires SSH config change):
  ```bash
  # On VPS:
  sudo sed -i 's/^#GatewayPorts no/GatewayPorts yes/' /etc/ssh/sshd_config
  sudo systemctl restart sshd
  
  # On local, use 0.0.0.0 to bind all interfaces:
  ssh -N -R 0.0.0.0:3100:localhost:3100 ubuntu@<vps-ip>
  ```

- **Option B — Same-port bind (no config change, may work without GatewayPorts)**:
  If the VPS service was previously listening on `0.0.0.0:3100`, Docker Caddy proxying to `172.17.0.1:3100` may continue working even after the service is killed and replaced by a `127.0.0.1`-bound tunnel. This is because Docker's bridge network can route `172.17.0.1` traffic through the host's loopback. **Test it:**
  ```bash
  # From the VPS (Caddy's perspective via Docker bridge):
  docker exec hmac-caddy curl -sI http://172.17.0.1:3100
  
  # If this returns 200 → Option B works, no iptables GatewayPorts needed.
  # If it hangs or connection refused → use Option A with GatewayPorts.
  ```

### 3. Verify Full Chain

```bash
# From VPS host:  → should return 200
ssh ubuntu@<vps-ip> "curl -sI http://localhost:3100 | head -1"

# From public URL through Caddy:  → should return 200/302
curl -sI https://gc.your-domain.example | head -1
# → HTTP/2 302 → redirect to /channels/@me = Spacebar is alive

# From inside Docker Caddy container:
docker exec hmac-caddy curl -sI http://172.17.0.1:3100 | head -1
```

### 4. Set Up Watchdog

After the tunnel is verified, set up persistence (see Auto-Reconnect section below). The watchdog will keep the tunnel alive and auto-restore it when the local machine reboots or the tunnel drops.

**Key difference from standard tunnel:** No Caddyfile changes needed. The Caddyfile already proxies to `172.17.0.1:3100`. You're swapping the server behind that address from the VPS Spacebar to the local one through the tunnel.

## Auto-Reconnect (Tunnel Maintenance)

### Bash retry loop (no extra tools)

Save as a script on the local machine:

```bash
#!/bin/bash
# tunnel.sh — SSH reverse tunnels with auto-reconnect
VPS="<vps-ip>"
KEY="$HOME/.ssh/vps_key"

while true; do
  ssh -i "$KEY" -o StrictHostKeyChecking=no \
    -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
    -o ExitOnForwardFailure=yes \
    -N -R 0.0.0.0:8081:localhost:8080 \
    -R 0.0.0.0:3001:localhost:3001 \
    ubuntu@$VPS
  echo "Tunnel died, restarting in 5s..."
  sleep 5
done
```

### autossh (if available)

```bash
# Install via chocolatey on Windows
choco install autossh

autossh -M 0 -N \
  -R 0.0.0.0:8081:localhost:8080 \
  -o ServerAliveInterval=30 \
  ubuntu@<vps-ip> -i ~/.ssh/vps_key
```

### Hermes Cron Watchdog (Windows, no extra tools)

When running from a Windows machine with Hermes, use a `no_agent=True` cron script as autossh replacement. The script checks tunnel health every N minutes and restarts on failure.

**The watchdog script** — save to `~/AppData/Local/hermes/scripts/spacebar-tunnel.sh`:

```bash
#!/usr/bin/env bash
# Spacebar reverse tunnel watchdog — Hermes cron no_agent=True
# Health-check + restart loop. Run every 5 minutes via cron.

TUNNEL_PID_FILE="/tmp/spacebar-tunnel.pid"
SSH_KEY="$HOME/.ssh/vps_key"
SSH_USER="ubuntu"
SSH_HOST="<vps-ip>"
LOCAL_PORT="3100"
REMOTE_PORT="3100"

# Kill any stale tunnel
if [ -f "$TUNNEL_PID_FILE" ]; then
    OLD_PID=$(cat "$TUNNEL_PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        # Check if tunnel actually works
        if ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
            "$SSH_USER@$SSH_HOST" \
            "curl -sI http://localhost:$REMOTE_PORT 2>&1 | head -1 | grep -q '200'" 2>/dev/null; then
            # Tunnel is healthy
            exit 0
        fi
        # Tunnel process exists but doesn't work — kill it
        kill "$OLD_PID" 2>/dev/null
        sleep 1
    fi
fi

# Start fresh tunnel
nohup ssh -i "$SSH_KEY" \
    -o StrictHostKeyChecking=no \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    -o ExitOnForwardFailure=yes \
    -N -R "$REMOTE_PORT:localhost:$LOCAL_PORT" \
    "$SSH_USER@$SSH_HOST" > /dev/null 2>&1 &

TUNNEL_PID=$!
echo $TUNNEL_PID > "$TUNNEL_PID_FILE"

# Verify tunnel came up
sleep 2
if kill -0 "$TUNNEL_PID" 2>/dev/null; then
    echo "Spacebar tunnel started (PID $TUNNEL_PID)"
    exit 0
else
    echo "FAILED to start tunnel"
    exit 1
fi
```

**Cron job creation:**

```bash
# Create the cron job via Hermes:
cronjob action=create \
  name="Tunnel Watchdog" \
  schedule="every 5m" \
  script="spacebar-tunnel.sh" \
  no_agent=True \
  deliver=local
```

The `no_agent=True` flag runs the script directly without LLM overhead. The script outputs only when something changed (tunnel restarted or failed) — stays silent on healthy runs per the `no_agent` empty-stdout convention.

## Verifying

```bash
# From VPS host:
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8081/
# Should return HTTP 200

# From inside Docker:
docker exec hmac-caddy curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://172.17.0.1:8081/
# Should return HTTP 200

# From anywhere (full chain):
curl -s -o /dev/null -w 'HTTP %{http_code}\n' https://discy.example.com/
# Should return HTTP 200
```

## Pitfalls

- **iptables rule ORDER matters**: `-A` (append) puts the rule AFTER the REJECT rule, silently doing nothing. Always use `-I N` to insert before REJECT.

- **Docker Caddy cannot reach 127.0.0.1**: Inside a Docker container, `127.0.0.1` is the container, not the host. Use the Docker bridge gateway (`172.17.0.1`, found via `docker inspect container --format '{{.NetworkSettings.Networks.bridge.Gateway}}'`), or `host.docker.internal` if the `--add-host host.docker.internal:host-gateway` flag was used when creating the container.

- **Caddy reload without restart**: Use `docker exec <name> caddy reload --config /etc/caddy/Caddyfile` not `caddy restart`. Reload picks up config changes without dropping active connections.

- **Windows SSH key passphrase**: If your SSH key has a passphrase, the tunnel script won't work on reboot without agent forwarding or keychain. Either remove the passphrase on the tunnel key, or use Pageant (PuTTY agent).

- **SSH keepalive**: Always use `ServerAliveInterval=30 ServerAliveCountMax=3`. Without these, SSH may not detect a broken tunnel for hours, and Caddy will return 502 errors to users.

- **Prefer Tailscale when possible**: SSH reverse tunnels are single-direction and less reliable than Tailscale (which handles reconnection, NAT traversal, and multi-directional routing automatically). Use SSH tunnels only when Tailscale can't be installed on the local machine.

- **nftables on Ubuntu 24.04+**: Newer Ubuntu uses nftables as the backend. Adding rules via `iptables` commands works (they're translated to nftables), but for persistent rules, you may need to add them directly with `nft` commands or install `iptables-persistent` which saves the translated rules.
