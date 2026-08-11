# Windows Docker Desktop Port Conflicts

On Windows, Docker Desktop's internal networking (`com.docker.backend.exe` and `wslrelay.exe`) binds ports 80 and 443 on `0.0.0.0`. This blocks any other process (including Docker Compose port mappings) from binding these ports:

```
TCP    0.0.0.0:80             0.0.0.0:0              LISTENING       16464   # com.docker.backend.exe
TCP    0.0.0.0:443            0.0.0.0:0              LISTENING       16464   # com.docker.backend.exe
```

## Symptoms
- `docker compose up` fails with: `Bind for 0.0.0.0:80 failed: port is already allocated`
- Cannot run Caddy/nginx/Traefik on standard HTTPS port 443
- Cannot run Let's Encrypt HTTP-01 challenge (needs port 80)

## Workarounds

### Option 1: Non-Standard Port
Map the reverse proxy to a high port (e.g., 8443 for HTTPS):

```yaml
ports:
  - "8443:443"
```

Update your app's URL config to include the port: `https://app.example.com:8443`

**Limitation:** OAuth providers often don't accept non-standard ports in redirect URIs. Google accepts any port; others may not.

### Option 2: Bind to Specific IP
Bind to the machine's public IP or localhost instead of `0.0.0.0`:

```yaml
ports:
  - "127.0.0.1:80:80"
  - "74.76.35.96:80:80"
```

This bypasses the `0.0.0.0:80` conflict. But port 80 on the public IP must still be reachable from the internet for Let's Encrypt.

### Option 3: Cloudflare Tunnel (Recommended)
No open ports needed. Cloudflare Tunnel creates an outbound-only HTTPS tunnel:

```bash
# Install cloudflared
winget install cloudflare.cloudflared

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create postiz

# Route DNS
cloudflared tunnel route dns postiz sg.your-domain.example

# Run tunnel (pointing to your local port)
cloudflared tunnel run postiz --url http://localhost:4007
```

Add as a Docker Compose service:

```yaml
cloudflared:
    image: cloudflare/cloudflared:latest
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${TUNNEL_TOKEN}
    networks:
      - app-network
```

### Option 4: Stop Docker Desktop's Port Binding
Edit Docker Desktop's `settings.json` to release port 80/443:

1. Open Docker Desktop → Settings → General
2. Uncheck "Expose daemon on tcp://localhost:2375 without TLS"
3. Restart Docker Desktop

If still bound, check WSL2 networking: `wsl --shutdown` then restart Docker.

### Option 5: Self-Signed Cert + Direct Access
Use Caddy with `tls internal` for a self-signed cert. Works for development/testing but browsers show a security warning.

```caddyfile
:443 {
    tls internal
    reverse_proxy app:3000
}
```

## Let's Encrypt on Windows
The HTTP-01 challenge requires port 80 reachable from the internet. Options:
- Use DNS-01 challenge (requires DNS provider API key)
- Use Cloudflare Tunnel (option 3 above)
- Use a VPS-based reverse proxy that tunnels back to the Windows machine

## Verification
```bash
# Check what's on port 80/443
netstat -ano | findstr ":80 "
netstat -ano | findstr ":443 "

# Check for docker-proxy processes
tasklist | findstr "com.docker.backend"
tasklist | findstr "wslrelay"
```
