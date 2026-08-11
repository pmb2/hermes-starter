#!/bin/bash
# ==============================================================================
# Hermes AI Stack — Unified Startup Script
echo "║        Hermes AI Provider Stack — Starting All Services      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$HOME/AppData/Local/hermes/.stack_pids"

# Kill any existing stack
echo "→ Cleaning up existing processes..."
if [ -f "$PID_FILE" ]; then
    while read pid; do
        taskkill //F //PID "$pid" 2>/dev/null || true
    done < "$PID_FILE"
    rm -f "$PID_FILE"
fi

# ─────── 1. OmniRoute (Primary AI Gateway) ───────
echo ""
echo "╔═══ 1. OmniRoute v3.8.49 — AI Gateway ═══╗"
cd "$HOME/OmniRoute"
node --max-old-space-size=8192 scripts/dev/run-next.mjs dev &
echo $! >> "$PID_FILE"
echo "  Starting on port 20128..."
for i in $(seq 1 30); do
    python -c "import socket; exit(0 if socket.socket().connect_ex(('127.0.0.1',20128))==0 else 1)" 2>/dev/null && break
    sleep 1
done
echo "  ✓ OmniRoute ready (117 models)"
echo "╚═══════════════════════════════════════════╝"

# ─────── 2. Hermes-router (the operator's Router) ───────
echo ""
echo "╔═══ 2. Hermes-router — YOUR Router ═══╗"
cd "${MY_REPOS}/Documents/github/Hermes-router"
python router.py &
echo $! >> "$PID_FILE"
echo "  Starting on port 8319..."
for i in $(seq 1 10); do
    python -c "import socket; exit(0 if socket.socket().connect_ex(('127.0.0.1',8319))==0 else 1)" 2>/dev/null && break
    sleep 1
done
echo "  ✓ Hermes-router ready"
echo "╚═══════════════════════════════════════════╝"

echo $! >> "$PID_FILE"
echo "  ✓ Model monitor running"
echo "╚════════════════════════════════════════════════════════╝"

# ─────── 4. Firefox MCP (if needed) ───────
echo ""
echo "╔═══ 4. Firefox Remote Debugging (optional) ═══╗"
# Comment out if Firefox already running
if ! python -c "import socket; exit(0 if socket.socket().connect_ex(('127.0.0.1',9239))==0 else 1)" 2>/dev/null; then
    "/c/Program Files/Mozilla Firefox/firefox.exe" \
        --remote-debugging-port 9239 \
        --no-remote \
        --profile "$HOME/AppData/Roaming/Mozilla/Firefox/Profiles/<profile-id>.default-release-1" \
        --disable-gpu &
    echo $! >> "$PID_FILE"
    echo "  ✓ Firefox CDP on port 9239"
else
    echo "  ✓ Firefox already running"
fi
echo "╚════════════════════════════════════════════════════╝"

# ─────── Summary ───────
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    Stack is LIVE!                             ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║  Tier 1 (FREE): OpenCode Zen → DeepSeek V4 Flash             ║"
echo "║  Tier 2 (FREE): Together AI  → DeepSeek V3                   ║"
echo "║  Tier 3 (FREE): Auto-Free    → Best free model               ║"
echo "║  Tier 4 (FREE): Hermes-router→ YOUR custom router            ║"
echo "║  Tier 5 (FREE): CLIProxyAPI  → Claude/Codex/Antigravity      ║"
echo "║  Tier 6 (FREE): FreeLLMAPI   → 28 free providers             ║"
echo "║  Last (PAID):   DeepSeek API → Only if all free exhausted    ║"
echo "║  NEVER AUTO:    Kimi K3      → Manual switch only            ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "To stop: for pid in \$(cat $PID_FILE); do taskkill //F //PID \$pid; done; rm -f $PID_FILE"
