#!/bin/bash
# spacebar-tunnel.sh — Maintain SSH reverse tunnels for Spacebar/Fermi
# Forwards local ports to the VPS so Caddy can proxy
#
# Tunnels:
#   3001 → localhost:3001 (Spacebar API)
#   8081 → localhost:8080 (Fermi web UI)
#
# Requires GatewayPorts yes on VPS sshd (so -R 0.0.0.0:PORT binds to all interfaces)
# Requires iptables rules on VPS allowing docker0 to reach ports 3001, 8081

VPS="your.vps.ip"
KEY="$HOME/.ssh/your_key"
USER="ubuntu"

cleanup() {
    echo "Shutting down tunnels..."
    kill $(jobs -p) 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

SSH_OPTS=(
    -i "$KEY"
    -o StrictHostKeyChecking=no
    -o ServerAliveInterval=30
    -o ServerAliveCountMax=3
    -o ExitOnForwardFailure=yes
)

while true; do
    # Tunnel 1: Spacebar API
    ssh "${SSH_OPTS[@]}" -N -R 0.0.0.0:3001:localhost:3001 "${USER}@${VPS}" &

    # Tunnel 2: Fermi UI
    ssh "${SSH_OPTS[@]}" -N -R 0.0.0.0:8081:localhost:8080 "${USER}@${VPS}" &

    # Wait for any tunnel to exit (then restart both)
    wait -n
    echo "Tunnel died, restarting in 3s..."
    kill $(jobs -p) 2>/dev/null
    sleep 3
done
