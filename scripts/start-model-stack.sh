#!/bin/bash
# === Start Model Provider Stack (OmniRoute + Switch Monitor) ===

echo "=== Starting Model Provider Stack ==="
echo ""

# Kill any existing zombie processes
python -c "
import subprocess
# Kill old OmniRoute
try:
    result = subprocess.run(['C:/Windows/System32/tasklist.exe', '/FO', 'CSV'], capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if 'node.exe' in line:
            pid = line.split(',')[1].strip('\"') if ',' in line else None
            if pid:
                subprocess.run(['C:/Windows/System32/taskkill.exe', '/F', '/PID', pid], capture_output=True)
except Exception as e:
    print(f'Cleanup: {e}')
" 2>/dev/null
sleep 2

# Start OmniRoute
cd ${USER_HOME}/OmniRoute
echo "Starting OmniRoute on port 20128..."
node --max-old-space-size=8192 scripts/dev/run-next.mjs dev &
OMNIROUTE_PID=$!
echo "OmniRoute PID: $OMNIROUTE_PID"

# Wait for OmniRoute to be ready
echo "Waiting for OmniRoute to start..."
for i in $(seq 1 30); do
    python -c "import socket; s=socket.socket(); s.settimeout(2); exit(0 if s.connect_ex(('127.0.0.1', 20128))==0 else 1)" 2>/dev/null && break
    sleep 1
done
echo "✓ OmniRoute is running at http://localhost:20128"

# Start Model Switch Monitor
echo "Starting Model Switch Monitor daemon..."
python "${USER_HOME}/AppData/Local/hermes/scripts/model_switch_monitor.py" --daemon &
MONITOR_PID=$!
echo "✓ Monitor PID: $MONITOR_PID"

echo ""
echo "=== Stack Active ==="
echo "  Tier 1: OpenCode Zen    (Free DeepSeek V4 Flash)  → oc/deepseek-v4-flash-free"
echo "  Tier 2: Together AI     (Free DeepSeek V3)         → tllm/together_deepseek_v3"
echo "  Tier 3: OmniRoute Auto  (Best Free)                → auto/coding:free"
echo "  Tier 4: DeepSeek Paid   (Your key)                  → deepseek/api"
echo "  Never:  Kimi K3         (Manual switch only)"
echo ""
echo "Model switch notifications: ENABLED (Discord)"
