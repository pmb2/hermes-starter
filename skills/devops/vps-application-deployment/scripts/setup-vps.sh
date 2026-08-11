#!/usr/bin/env bash
# =============================================================================
# setup-vps.sh — Idempotent VPS Provisioning Script
# Run ON the VPS after Oracle/cloud instance is provisioned.
# Installs Docker, Caddy, UFW, Fail2Ban, auto-updates, swap, and basic tooling.
# Safe to run multiple times.
# =============================================================================
set -euo pipefail

# --- Configuration ---
APP_DIR="${APP_DIR:-/home/ubuntu/constructmanage}"
CADDY_DOMAIN="${CADDY_DOMAIN:-doghouse.your-domain.example}"
SWAP_SIZE="${SWAP_SIZE:-2G}"

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    OS_VERSION=$VERSION_ID
else
    OS=$(uname -s)
fi

echo "=== VPS Setup: $(hostname) ==="
echo "OS: $OS $OS_VERSION"
echo "Arch: $(uname -m)"
echo "Date: $(date)"
echo "App Dir: $APP_DIR"

# --- Self-elevate if not root ---
if [ "$(id -u)" -ne 0 ]; then
    echo "Re-running as root..."
    exec sudo "$0" "$@"
fi

# --- Swap (if not already configured) ---
if ! swapon --show | grep -q .; then
    echo ">>> Setting up ${SWAP_SIZE} swap..."
    fallocate -l "$SWAP_SIZE" /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "Swap created."
else
    echo "Swap already configured."
    swapon --show
fi

# --- System packages ---
echo ">>> Updating packages..."
apt-get update -qq

echo ">>> Installing base packages..."
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    ca-certificates curl gnupg lsb-release \
    ufw fail2ban unattended-upgrades \
    htop iotop net-tools dnsutils rsync \
    git unzip jq

# --- Docker ---
if ! command -v docker &>/dev/null; then
    echo ">>> Installing Docker..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh
    echo "Docker installed: $(docker --version)"
else
    echo "Docker already installed: $(docker --version)"
fi

# Enable Docker on boot
systemctl enable docker

# Add ubuntu user to docker group
if id "ubuntu" &>/dev/null; then
    usermod -aG docker ubuntu
    echo "User 'ubuntu' added to docker group."
fi

# Docker Compose plugin check
if ! docker compose version &>/dev/null; then
    echo ">>> Installing Docker Compose plugin..."
    apt-get install -y -qq docker-compose-plugin
fi
echo "Docker Compose: $(docker compose version)"

# --- Caddy ---
if ! command -v caddy &>/dev/null; then
    echo ">>> Installing Caddy..."
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
        gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
        tee /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq caddy
    echo "Caddy installed: $(caddy version)"
else
    echo "Caddy already installed: $(caddy version)"
fi

systemctl enable caddy

# --- UFW ---
echo ">>> Configuring UFW..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable
echo "UFW status:"
ufw status verbose

# --- Fail2Ban ---
echo ">>> Configuring Fail2Ban..."
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = 22
logpath = %(sshd_log)s
EOF

systemctl enable fail2ban
systemctl restart fail2ban
echo "Fail2Ban status:"
fail2ban-client status sshd 2>/dev/null || echo "  (not yet active)"

# --- Auto security updates ---
echo ">>> Configuring unattended-upgrades..."
cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Unattended-Upgrade "1";
EOF

echo "Unattended-upgrades configured."

# --- SSH hardening ---
echo ">>> Hardening SSH..."
sed -i 's/^#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd
echo "SSH hardened: root login disabled, password auth disabled."

# --- App directory ---
mkdir -p "$APP_DIR"
chown ubuntu:ubuntu "$APP_DIR"
echo "App directory ready: $APP_DIR"

# --- Verify ---
echo ""
echo "=== Verification ==="
echo "Docker:      $(docker --version 2>/dev/null || echo 'FAIL')"
echo "Compose:     $(docker compose version 2>/dev/null || echo 'FAIL')"
echo "Caddy:       $(caddy version 2>/dev/null || echo 'FAIL')"
echo "UFW:         $(ufw status 2>/dev/null | head -1)"
echo "Fail2Ban:    $(systemctl is-active fail2ban 2>/dev/null)"
echo "Swap:        $(swapon --show 2>/dev/null | awk 'NR==2{print $3}' || echo 'none')"
echo "Disk:        $(df -h / | awk 'NR==2{print $3\" used / \"$2\" total\"}')"
echo "Memory:      $(free -h | awk 'NR==2{print $3\" used / \"$2\" total\"}')"
echo ""
echo "=== VPS Setup Complete ==="
echo "Next: scp your project files to $APP_DIR, then 'docker compose up -d --build'"
echo "Caddy config goes in /etc/caddy/Caddyfile"
echo ""
