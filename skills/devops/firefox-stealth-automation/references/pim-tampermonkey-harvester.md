# PIM Conversation Extraction via Tampermonkey (CSP-Proof, No Automation Detection)

## Context
ChatGPT and Grok conversations need regular extraction into Personal Intelligence (PIM).
Both sites are protected by Cloudflare Bot Management and restrictive Content-Security-Policies.
Firefox `--remote-debugging-port` is detectable at the C++ engine level in FF151+ and triggers
Cloudflare challenge pages regardless of JS stealth measures.

## Architecture

```
Browser (Tampermonkey userscript)
  |-- GM_xmlhttpRequest (bypasses CSP, uses browser cookies)
  v
Local HTTP Harvester (port 8897)
  |-- Python http.server (CORS-enabled)
  v
PIM pipeline (app.core.pipeline.process_item)
  |-- full_text_override bypasses HTTP fetcher
  v
pim.db
```

## Files

| File | Location | Purpose |
|------|----------|---------|
| Tampermonkey script | `templates/pim-full-extractor.user.js` | Installed in Tampermonkey, runs on chatgpt.com and grok.com |
| Harvester server | `scripts/pim-harvester-tampermonkey.py` | Local HTTP server, receives data, writes to PIM |
| PIM runner (legacy) | `scripts/pim-ingest-runner.py` | Old two-phase stealth runner (superseded by Tampermonkey approach) |
| PIM runner (v2) | `scripts/pim-harvester.py` | Latest Tampermonkey-based harvester |

## API Endpoints

**ChatGPT conversation content:**
```
GET https://chatgpt.com/backend-api/conversation/{id}
Response: { title, mapping: { msgId: { message: { author: { role }, content: { parts: [...] } } } } }
```

**Grok conversation content:**
```
GET https://grok.com/rest/app-chat/conversations/{id}
Response: { messages: [{ role, content }] } or { conversation: { messages: [...] } }
```
**Note:** Grok's sidebar conversation links changed from `/chat/<uuid>` to `/c/<uuid>` (circa May 2026). The API endpoint `/rest/app-chat/conversations/{id}` may still work — verify if the harvester receives 403s.

## CSP Behavior

| Site | `connect-src` allows | Blocks | Working transport |
|------|---------------------|--------|-------------------|
| ChatGPT | `wss://*.chatgpt.com`, `https://*.chatgpt.com`, `https://*.oaistatic.com` | `http://127.0.0.1:*`, `ws://127.0.0.1:*` | `GM_xmlhttpRequest` |
| Grok | `ws://127.0.0.1:*`, `ws://localhost:*`, `https://*.x.ai` | `http://127.0.0.1:*` | WebSocket (`ws://`, but upgraded to `wss://` on HTTPS pages) or `GM_xmlhttpRequest` |

`GM_xmlhttpRequest` works for BOTH sites because it runs in the Tampermonkey extension context (not page context).

## Setup Steps

```bash
# 1. Start the harvester
python scripts/pim-harvester.py

# 2. Open chatgpt.com in Firefox (normal browsing — NO remote debugging)
# 3. Tampermonkey should already have the PIM Full Extractor v2 script installed
#    If not: Tampermonkey icon -> Create a new script -> paste templates/pim-full-extractor.user.js -> Ctrl+S
# 4. The script auto-runs. Look for [PIM] messages in browser console (F12)
# 5. Repeat for grok.com
# 6. Check PIM DB: sqlite3 pim.db "SELECT source_type, COUNT(*) FROM saved_items GROUP BY source_type"
```

## Known Issues

- **Firefox force-kill destroys session cookies**: `taskkill.exe //F //IM firefox.exe` kills ALL Firefox processes
  including the one with active ChatGPT/Grok sessions. The cookies in the profile's `cookies.sqlite` survive,
  but `cf_clearance` and OAuth tokens expire. The user must re-authenticate in the automation window.
- **Tampermonkey script runs once per page load**: It sets `window.__PIM_DONE = true` to avoid re-running.
  Refresh the tab to trigger re-extraction.
- **`GM_xmlhttpRequest` rate limits**: Large conversation lists (50+) trigger per-conversation API calls.
  On free ChatGPT tier, the `/backend-api/conversation/{id}` endpoint may rate-limit after 5-10 calls per minute.
  The script fires all requests simultaneously. Consider adding a throttle.
