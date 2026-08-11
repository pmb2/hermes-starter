# Firefox Remote Debugging Setup for PIM Ingestion

## Overview

The PIM ingestion pipeline (ChatGPT, Grok, bookmarks, YouTube extraction) requires a running Firefox instance with remote debugging enabled. This document covers setup, maintenance, troubleshooting, and known limitations.

## Architecture

```
Firefox Binary: C:\Program Files\Mozilla Firefox\firefox.exe
Profile:       ${USER_HOME}\AppData\Local\hermes\firefox-profile  (hermes-mcp)
Port:          9223 (WebDriver BiDi protocol)
Mode:          headless (--headless flag)
```

## Starting Firefox

### Batch Script (recommended)
```
${MY_REPOS}\Documents\github\_project\scripts\start-firefox-remote.bat
```
Checks if port 9223 is already in use, starts Firefox headless if not, waits up to 20s for ready.

### Health Check Script
```
python ${MY_REPOS}/_project/scripts/firefox-health.py [check|start|watchdog|restart]
```

| Action | Behavior | Output |
|--------|----------|--------|
| `check` | Test if Firefox is healthy on 9223 | `HEALTHY`, `BIDI_DOWN`, `DOWN` |
| `start` | Start Firefox on 9223 if not running | `ALREADY_RUNNING`, `STARTED`, `FAILED` |
| `watchdog` | Auto-heal: silent when healthy, output only on restart | (silent), `[FF-HEAL] started` |
| `restart` | Kill and re-launch | `RESTARTED`, `RESTART_FAILED` |

### Manual Start (for debugging)
```bash
"C:\Program Files\Mozilla Firefox\firefox.exe" --headless --no-remote --profile "${USER_HOME}\AppData\Local\hermes\firefox-profile" --remote-debugging-port 9223
```

## Watchdog (Auto-Healing)

A no_agent cron job (`Firefox Remote Debugging Watchdog`, job_id: `010bc215150a`) checks every 15 minutes via:
```bash
bash ~/AppData/Local/hermes/scripts/firefox-watchdog.sh
```
- Silent when Firefox is healthy (no output = no delivery)
- Only produces output when an auto-restart occurred
- Scripts in: `~/AppData/Local/hermes/scripts/firefox-health.py`

## Connector Configuration

The FirefoxBiDiClient reads the `PIM_BIDI_PORT` environment variable to determine which port to connect to:

| Env Var | Default | Current Value |
|---------|---------|---------------|
| `PIM_BIDI_PORT` | `9239` | `9223` |

Without this env var, the connector will start its own Firefox on a random port (9239+), which can cause port conflicts and session confusion. Always set `PIM_BIDI_PORT=9223` before running any connector.

## Firefox Version Compatibility

| Firefox Version | Protocol | Endpoint | Notes |
|---------------|----------|----------|-------|
| **136+** | WebDriver BiDi only | `ws://127.0.0.1:{port}/session` | CDP removed entirely |
| **Pre-136** | CDP + BiDi | `http://127.0.0.1:{port}/json/version` | Falls back to CDP |

Current version: **Firefox 151.0.3** (BiDi only). The old CDP endpoints (`/json/version`, `/json/list`, `/json/new`) do NOT exist — they return 404.

### Verifying BiDi is Working
```bash
# Check port is listening
netstat -ano | findstr ":9223" | findstr LISTENING

# Test BiDi WebSocket connection (Python)
python -c "
import asyncio, json, websockets
async def t():
    async with websockets.connect('ws://127.0.0.1:9223/session') as ws:
        await ws.send(json.dumps({'id': 1, 'method': 'session.new', 'params': {
            'capabilities': {'alwaysMatch': {'acceptInsecureCerts': True}}
        }}))
        r = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        print(f'Session: {r[\"result\"][\"sessionId\"][:12]}')
asyncio.run(t())
"
```

## Session Exhaustion ("Maximum number of active sessions")

Firefox BiDi enforces a **one-session-per-WebSocket-connection** limit. Symptoms:

1. First attempt returns `{"error": "session not created", "message": "Maximum number of active sessions"}`
2. The FirefoxBiDiClient's `connect()` method detects this, calls `_kill_firefox()`, and retries
3. Second attempt starts fresh and succeeds

**This is normal behavior.** The connector handles it via restart + retry (up to 3 attempts). Each PIM ingestion cycle will typically restart Firefox once. The restart takes ~5-8 seconds.

**Do NOT pre-create BiDi sessions for testing** — every manual `websockets.connect` + `session.new` call consumes a session slot and forces the connector to restart Firefox on its next run.

## Zombie Process Handling

When Firefox is killed via `kill -9` or the connector's `_kill_firefox()`, child content processes can persist and hold the port. Symptoms:

- Port 9223 shows `LISTENING` but the PID no longer exists in task manager
- New Firefox instances fail to start because "port is in use"
- `taskkill /F /PID X` returns success but port stays bound

### Fix: PowerShell Force Kill
```powershell
Stop-Process -Id <PID> -Force
```
or via wmic:
```
wmic process where processid=<PID> call terminate
```

If multiple zombie processes accumulate:
```powershell
# Kill ALL firefox processes (only use when Firefox isn't needed)
Get-Process firefox | Stop-Process -Force
```

## Key Scripts

| Script | Location | Purpose |
|--------|----------|---------|
| `firefox-health.py` | `_project/scripts/` | Health check, start, watchdog, restart |
| `firefox-health.py` (copy) | `~/AppData/Local/hermes/scripts/` | Symlinked for no_agent cron |
| `firefox-watchdog.sh` | `~/AppData/Local/hermes/scripts/` | Bash wrapper calling `watchdog` action |
| `start-firefox-remote.bat` | `_project/scripts/` | Windows batch script for Firefox launch |
| `unseen-backlog.py` | `_project/scripts/` | Backlog manager for Pulsar |
| `intelligence_collector.py` | `hermes-config/scripts/` | Full PIM ingestion pipeline |

## Known Limitations

### Grok Conversation Content Extraction
The GrokConnector can list all conversations via sidebar scrolling, but **content extraction from individual conversations may fail** because Grok's React SPA blocks direct URL navigation. Loading `https://grok.com/c/{id}` in a BiDi-controlled browser returns "You need access — This is a private conversation link" even when properly authenticated.

**Root cause**: Grok's SPA handles conversation routing entirely client-side via Next.js router. Direct URL navigation bypasses the necessary React state initialization. The sidebar click interaction works because it triggers the SPA's internal navigation.

**Workarounds:**
- The GrokConnector's `discover()` with `skip_content=False` tries to visit each conversation and extracts messages — works for most conversations but slow (30 convos can take 2+ minutes)
- For reliable content extraction, use the GrokConnector's `discover()` method (which scrolls sidebar + clicks links) rather than standalone BiDi navigation
- Conversations are still ingested into PIM via the connector's sidebar-click-and-scrape approach

### PIM DB Content Quality
The `saved_items` table's `full_text` column for Grok/ChatGPT conversations often contains **raw HTML page source** rather than clean extracted text. This happens because the extraction script captures `document.documentElement.outerHTML` before React finishes rendering the conversation messages.

If you need clean text from a conversation:
1. Query PIM for `title` and `source_id` first (these are reliable)
2. For full text, re-extract using the connector with `document.body.innerText` instead of `outerHTML`
3. Or navigate to the conversation URL using a browser and manually extract

### ChatGPT Conversation Extraction
ChatGPT connector typically works better than Grok because OpenAI's SPA handles URL navigation more gracefully. Still subject to session exhaustion.
