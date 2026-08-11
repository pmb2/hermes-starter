#!/usr/bin/env bash
# ───────────────────────────────────────────────────────────
# Personal Intelligence: ChatGPT + Grok + Gemini Ingestion
# Visible mode + sidebar scroll discovers ALL conversations
# ───────────────────────────────────────────────────────────
set -u -o pipefail

PYTHON="${USER_HOME}/AppData/Local/Programs/Python/Python311/python.exe"

# Deactivate any active venv so system Python doesn't pick up Hermes venv packages
unset VIRTUAL_ENV
unset PYTHONHOME
unset PYTHONPATH
# Remove Hermes venv from PATH to avoid picking up wrong scripts
export PATH=$(echo "$PATH" | tr ':' '\n' | grep -v "hermes-agent/venv" | tr '\n' ':' | sed 's/:$//')

PIM_DIR="${MY_REPOS}/Documents/github/git-mcp/services/personal-intelligence-mcp"
cd "$PIM_DIR"

export PIM_BIDI_PORT=9239

# ───────────────────────────────────────────────────────────
# SAFETY: Kill orphan Firefox processes
# ───────────────────────────────────────────────────────────
echo "[SAFETY] Checking for orphan Firefox processes on port 9239..."
$PYTHON << 'PYEOF'
import subprocess, os
def kill_on_port(port):
    try:
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            if f':{port}' in line and 'LISTENING' in line:
                pid = line.strip().split()[-1]
                if pid != '0':
                    subprocess.run(['powershell', '-Command', f'Stop-Process -Id {pid} -Force'],
                                  capture_output=True, timeout=5)
                    print(f'Killed orphan PID {pid} on port {port}')
    except Exception as e:
        print(f'Orphan cleanup for port {port} skipped: {e}')

kill_on_port(9239)
kill_on_port(9223)
PYEOF
sleep 1

# ───────────────────────────────────────────────────────────
# SYNC: Fresh cookies from the operator's main profile
# ───────────────────────────────────────────────────────────
echo "[SYNC] Syncing session cookies from main profile to automation profile (live)..."
$PYTHON "C:\\Users\\<you>\\AppData\\Local\\hermes\\scripts\\sync-cookies.py" 2>&1

# ───────────────────────────────────────────────────────────
# Launch Firefox (visible mode — GFX crash workaround)
# ───────────────────────────────────────────────────────────
if ! powershell -Command "try { \$t = New-Object Net.Sockets.TcpClient; \$t.Connect('127.0.0.1', 9239); \$t.Dispose(); exit 0 } catch { exit 1 }" 2>/dev/null; then
    echo "[INFO] Firefox not on 9239. Launching visible (non-headless)..."
    rm -f "${HERMES_HOME}/firefox-profile/parent.lock" 2>/dev/null
    rm -f "${HERMES_HOME}/firefox-profile/WebDriverBiDiServer.json" 2>/dev/null
    rm -f "${HERMES_HOME}/firefox-profile/MarionetteActivePort" 2>/dev/null
    "${USER_HOME}/firefox-portable/firefox.exe" \
        --remote-debugging-port 9239 \
        --no-remote \
        --profile "C:\\Users\\<you>\\AppData\\Local\\hermes\\firefox-profile" &
    sleep 14
fi

# Get tokens
GH_TOKEN=$(gh auth token 2>/dev/null || echo "")
if [ -z "$GH_TOKEN" ]; then
    echo "[WARN] No GitHub token available — summaries may fail"
else
    echo "[INFO] GitHub token loaded (${#GH_TOKEN} chars)"
fi

# Write .env
$PYTHON << PYEOF
import os, json
pim_dir = r"${PIM_DIR}"
gh_token = r"${GH_TOKEN}"

ds_key = os.environ.get("DEEPSEEK_API_KEY", "")
auth_path = os.path.expanduser(r"~/.local/share/opencode/auth.json")
if os.path.exists(auth_path):
    try:
        with open(auth_path) as f:
            auth = json.load(f)
            ds_key = auth.get("opencode-go", {}).get("key", "")
    except Exception:
        pass

llm_key = ds_key or gh_token
llm_base = "https://api.deepseek.com/v1"

with open(os.path.join(pim_dir, '.env'), 'w') as f:
    f.write('# LLM for summarization (DeepSeek API)\n')
    f.write('LLM_PROVIDER=deepseek\n')
    f.write(f'LLM_API_BASE_URL={llm_base}\n')
    f.write('LLM_MODEL=deepseek-chat\n')
    if llm_key:
        f.write(f'LLM_API_KEY={llm_key}\n')
    else:
        f.write('# LLM_API_KEY= (no key available)\n')
    f.write('EMBEDDING_PROVIDER=local\n')
    f.write('EMBEDDING_MODEL=nomic-embed-text\n')
    f.write('DATABASE_URL=sqlite+aiosqlite:///./pim.db\n')
    if llm_key:
        f.write(f'# OpenCode Go key also available: {llm_key[:8]}...\n')
PYEOF

# ───────────────────────────────────────────────────────────
# STEP 1: ChatGPT Ingestion
# ───────────────────────────────────────────────────────────
echo ""
echo "=== ChatGPT Ingestion (sidebar scroll, ALL conversations) ==="
$PYTHON << PYEOF
import os, asyncio, json
os.environ['PIM_BIDI_PORT'] = '9239'
from app.db import init_db, AsyncSessionLocal
from app.connectors.chatgpt import ChatGPTConnector
async def run():
    await init_db()
    async with AsyncSessionLocal() as s:
        r = await ChatGPTConnector().ingest(s, {
            'max_conversations': 1000,
            'scroll_pause': 2500,
            'headless': False,
        })
    print(json.dumps(r, indent=2))
asyncio.run(run())
PYEOF

# ───────────────────────────────────────────────────────────
# STEP 2: Grok Ingestion
# ───────────────────────────────────────────────────────────
echo ""
echo "=== Grok Ingestion (sidebar scroll, ALL conversations) ==="
$PYTHON << PYEOF
import os, asyncio, json
os.environ['PIM_BIDI_PORT'] = '9239'
from app.db import init_db, AsyncSessionLocal
from app.connectors.grok import GrokConnector
async def run():
    await init_db()
    async with AsyncSessionLocal() as s:
        r = await GrokConnector().ingest(s, {
            'max_conversations': 1000,
            'scroll_pause': 2500,
            'headless': False,
        })
    print(json.dumps(r, indent=2))
asyncio.run(run())
PYEOF

# ───────────────────────────────────────────────────────────
# STEP 3: Gemini Ingestion (both accounts)
# ───────────────────────────────────────────────────────────
echo ""
echo "=== Gemini Ingestion (sidebar scroll, both accounts) ==="
$PYTHON << PYEOF
import os, asyncio, json
os.environ['PIM_BIDI_PORT'] = '9239'
from app.db import init_db, AsyncSessionLocal
from app.connectors.gemini import GeminiConnector
async def run():
    await init_db()
    async with AsyncSessionLocal() as s:
        r = await GeminiConnector().ingest(s, {
            'max_conversations': 500,
            'scroll_pause': 2500,
            'headless': False,
            'account_switch': True,
        })
    print(json.dumps(r, indent=2))
asyncio.run(run())
PYEOF

# ───────────────────────────────────────────────────────────
# STEP 4: Run Relevance Analyzer on new items
# ───────────────────────────────────────────────────────────
echo ""
echo "=== Running Relevance Analysis on new items ==="
$PYTHON << PYEOF
import sys, json
sys.path.insert(0, r"${PIM_DIR}")
try:
    from app.core.relevance import check_new_items, get_pending_suggestions
    suggestions = check_new_items()
    if suggestions:
        print(f"Found {len(suggestions)} new relevance suggestions:")
        for s in suggestions:
            print(f"  [{s.get('project','?')}] ({s.get('confidence',0):.0%}) {s.get('suggestion','')[:80]}")
    else:
        print("No new relevance suggestions.")
    pending = get_pending_suggestions()
    if pending:
        print(f"\nPending suggestions to deliver: {len(pending)}")
except ImportError:
    print("Relevance engine not yet available (skipping)")
except Exception as e:
    print(f"Relevance analysis skipped: {e}")
PYEOF

# ───────────────────────────────────────────────────────────
# STEP 5: Sync to MemPalace
# ───────────────────────────────────────────────────────────
echo ""
echo "=== Syncing to MemPalace ==="
${USER_HOME}/AppData/Local/Programs/Python/Python311/python.exe ${HERMES_HOME}/scripts/pim_sync_mempalace.py

echo ""
echo "=== Ingestion + Sync Complete ==="
# ───────────────────────────────────────────
# STEP 6: Email Summary Enrichment
# ───────────────────────────────────────────
echo ""
echo "=== Email Summary Enrichment ==="
"$PYTHON" -m app.connectors.email_summary --batch 10 2>&1 || echo "[WARN] Email summary enrichment failed"

# ───────────────────────────────────────────
# STEP 7: Browser History (Chrome/Edge/Firefox)
# ───────────────────────────────────────────
echo ""
echo "=== Browser History Connector ==="
"$PYTHON" -m app.connectors.browser_history 2>&1 || echo "[WARN] Browser history connector failed"

# ───────────────────────────────────────────
# STEP 8: RSS Feed Connector
# ───────────────────────────────────────────
echo ""
echo "=== RSS Feed Connector ==="
"$PYTHON" -m app.connectors.rss_feeds 2>&1 || echo "[WARN] RSS feed connector failed"

# ───────────────────────────────────────────
# STEP 9: Real-Time Trigger (run FOSS mapping immediately)
# ───────────────────────────────────────────
echo ""
echo "=== Real-Time Trigger ==="
"$PYTHON" "${MY_REPOS}/Documents/github/_project/scripts/pim_trigger.py" trigger 2>&1 || echo "[WARN] Trigger failed"
