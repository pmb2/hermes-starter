# RustDesk Server Deployment (Oracle VPS)

Example of deploying a non-Hermes service on the Oracle Cloud free-tier VPS alongside the Hermes stack.

## Architecture

RustDesk uses two server processes:
- **hbbs** — ID/Rendezvous server (manages peer discovery, NAT traversal)
- **hbbr** — Relay server (forwards traffic when direct P2P fails)

Both run inside Docker with `network_mode: host` because hbbs needs UDP.

## Ports

| Port | Protocol | Purpose |
|------|----------|---------|
| 21115 | TCP | NAT type test |
| 21116 | TCP+UDP | ID registration, heartbeat, hole punching |
| 21117 | TCP | Relay session |
| 21118 | TCP | WebSocket (optional, web client) |
| 21119 | TCP | WebSocket relay (optional, web client) |

## Deployment

```bash
# Create project directory
mkdir -p ~/rustdesk/data

# docker-compose.yml
cat > ~/rustdesk/docker-compose.yml << 'EOF'
services:
  hbbs:
    image: rustdesk/rustdesk-server:latest
    command: hbbs
    volumes: ["./data:/root"]
    network_mode: "host"
    restart: unless-stopped

  hbbr:
    image: rustdesk/rustdesk-server:latest
    command: hbbr
    volumes: ["./data:/root"]
    network_mode: "host"
    depends_on: [hbbs]
    restart: unless-stopped
EOF

# Start
docker-compose up -d  # or: docker compose up -d

# Check key (auto-generated on first run)
cat ~/rustdesk/data/id_ed25519.pub
# hbbs logs show: Key: <base64-key>
```

## Prerequisite: Verify Server Ownership

Before deploying on any VPS, confirm the machine belongs to the right project/person — especially when multiple VPS exist in the same tenancy:

```bash
# SSH and check the hostname — cross-reference with the user
ssh ubuntu@<candidate-ip> "hostname && cat /etc/hostname"
# If the user says "that's a client's VPS", find a different one
```

## Firewall Configuration

Two layers on Oracle Cloud VPS:

### Layer 1: Instance iptables
```bash
# Add rules before the REJECT all rule (insert at position 5 or above)
sudo iptables -I INPUT 5 -p tcp --dport 21115:21119 -j ACCEPT
sudo iptables -I INPUT 5 -p udp --dport 21116 -j ACCEPT

# Persist across reboots
sudo apt-get install -y iptables-persistent
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

### Layer 2: OCI Security List

**Method A — OCI Console** (no API permissions needed):
OCI Console → Networking → Virtual Cloud Networks → your VCN → Security List

| Source | Protocol | Port | Description |
|--------|----------|------|-------------|
| 0.0.0.0/0 | TCP | 21115-21119 | RustDesk services |
| 0.0.0.0/0 | UDP | 21116 | RustDesk hole punching |

**Method B — OCI CLI** (requires API user with `manage security-lists` permissions):
```bash
# 1. Get the VCN and security list IDs
TENANCY="ocid1.tenancy.oc1..<your-tenancy-ocid>"
VCN_ID="ocid1.vcn.oc1.<region>.<vcn-ocid>"
oci network security-list list --compartment-id "$TENANCY" --vcn-id "$VCN_ID"

# 2. Build a JSON file with ALL current rules + the new RustDesk rules
#    (OCI uses PUT — the entire rule set must be provided)
#    Write to e.g. /tmp/rustdesk_ingress.json

# 3. Update the security list
oci network security-list update \
  --security-list-id "<security-list-ocid>" \
  --ingress-security-rules file:///path/to/rustdesk_ingress.json \
  --force
```

### Layer 3: Verify Ports Are Open

From an external machine (NOT the VPS itself):

```bash
# TCP port check via bash /dev/tcp/ (works on git-bash, Linux, macOS)
timeout 3 bash -c 'echo > /dev/tcp/<vps-ip>/21116' 2>&1 && echo "REACHABLE" || echo "BLOCKED"
timeout 3 bash -c 'echo > /dev/tcp/<vps-ip>/21117' 2>&1 && echo "REACHABLE" || echo "BLOCKED"
```

If BLOCKED, check both firewall layers:
1. Instance: `ssh ubuntu@<vps-ip> "sudo iptables -L INPUT -n | grep 2111"`
2. Cloud: Verify OCI security list ingress rules include the RustDesk ports

## Windows Client Configuration (Remote — Config File Edit)

When the RustDesk UI can't be interacted with (e.g. via remote desktop with input capture issues), the config can be modified on disk:

**Config file location:**
```
%APPDATA%/RustDesk/config/RustDesk2.toml
# e.g. C:\Users\<user>\AppData\Roaming\RustDesk\config\RustDesk2.toml
```

**Relevant fields:**
```toml
rendezvous_server = '129.153.156.190:21116'   # ID server IP:port
key = 'base64key'                              # Encryption key from server's id_ed25519.pub
relay_server = ''                              # Leave blank for auto-assign by hbbs
```

Other config files in the same directory:
- `RustDesk.toml` — identity keypair (DO NOT modify — changing this changes the machine's ID)
- `RustDesk_local.toml` — local UI window positions, favorites (safe to modify)
- `RustDesk_hwcodec.toml` — hardware codec settings

**⚠️ Config changes require service restart.** RustDesk runs as a SYSTEM service on Windows. The config file is read on service start. From a non-admin shell you cannot:
- `taskkill //F //IM rustdesk.exe` → Access denied
- `Stop-Service rustdesk` → Cannot open service
- `sc stop rustdesk` → Access denied
- `schtasks //create //ru SYSTEM` → Access denied (can only run as current user, which can't kill the service)

The RustDesk service auto-restarts killed GUI processes, so even WMI `Win32_Process.Terminate()` on the console process doesn't help — it respawns immediately.

**To apply config changes, you need one of:**
1. **Reboot** the machine — cleanest approach. Schedule with the user first.
2. **Elevated command prompt** — right-click → Run as Administrator, then `net stop rustdesk && net start rustdesk`
3. **UAC elevation** — `powershell Start-Process -Verb RunAs` (shows a dialog the user must click)
4. **Wait for next boot** — config change is saved, takes effect on next automatic restart

## Client Configuration (Mac/Linux)

The same three fields apply. On Mac, the config is at `~/Library/Application Support/RustDesk/config/RustDesk2.toml`. Editing the file and restarting the app is straightforward — no SYSTEM service layer.

## Testing Connectivity

From an external machine (NOT the VPS itself):

```bash
# TCP port check via bash /dev/tcp/ (works on git-bash, Linux, macOS)
timeout 3 bash -c 'echo > /dev/tcp/<vps-ip>/21116' 2>&1 && echo "REACHABLE" || echo "BLOCKED"
timeout 3 bash -c 'echo > /dev/tcp/<vps-ip>/21117' 2>&1 && echo "REACHABLE" || echo "BLOCKED"
```

## Notes

- The `-k _` flag on hbbs/hbbr disables key verification (not recommended for production).
- Without `-k _`, a keypair is auto-generated in `./data/id_ed25519` and `./data/id_ed25519.pub`.
- The server database is at `./data/db_v2.sqlite3` — backed up with the data volume.
- `network_mode: host` is simplest but skips Docker port mapping — the containers share the host's network stack directly.
