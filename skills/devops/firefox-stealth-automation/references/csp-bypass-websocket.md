# CSP WebSocket Bypass & Console-Paste Extraction

## Primary Finding: WebSocket is NOT always available — use Tampermonkey GM_xmlhttpRequest

ChatGPT's CSP blocks `ws://127.0.0.1:*` entirely. Grok allows `ws://127.0.0.1:*` but Firefox upgrades to `wss://` on HTTPS pages. **The working cross-site solution is Tampermonkey's `GM_xmlhttpRequest`**, which bypasses all CSP because it runs with extension privileges.

## Problem
Cloudflare-protected sites (ChatGPT, Grok) detect `--remote-debugging-port` at the network level — no JS stealth fixes it. HTTP API calls with cookies also fail because `cf_clearance` tokens expire in ~1-2 hours.

## Solution Strategy Decision Tree

```
Does the site have Cloudflare / bot detection?
├── No  → Use Firefox BiDi/CDP stealth via ultimate-firefox-mcp
└── Yes → Use browser-context extraction:
         ├── User has Tampermonkey? → GM_xmlhttpRequest (bypasses ALL CSP)
         └── No Tampermonkey:
                  ├── CSP allows ws://127.0.0.1:*? → WebSocket harvester
                  └── No WebSocket allowed → console fetch (CSP-dependent, often blocked)
```

## Primary Approach: Tampermonkey `GM_xmlhttpRequest` (Works Everywhere)

### Step-by-step

1. **User creates a new Tampermonkey script** (Tampermonkey icon → Create new script)
2. **Sets `@match` to the target site** (e.g., `https://chatgpt.com/*`, `https://grok.com/*`)
3. **Uses `GM_xmlhttpRequest`** (NOT fetch or WebSocket) — the extension API bypasses CSP
4. **Post data to local HTTP server** with proper CORS headers
5. **Server feeds data into PIM pipeline**

### Script Template
```js
// ==UserScript==
// @name         PIM Extractor
// @namespace    http://pim.local/
// @version      0.1
// @description  Extract data and send to local harvester
// @match        https://chatgpt.com/*
// @match        https://grok.com/*
// @grant        GM_xmlhttpRequest
// ==/UserScript==

(function() {
  "use strict";
  var API="http://127.0.0.1:8897/ingest";
  var isChat=location.hostname.includes("chatgpt");
  var isGrok=location.hostname.includes("grok");
  if(!isChat&&!isGrok)return;

  var sel=isChat?'a[href*="/c/"]':'a[href*="/chat/"]';
  var convs=[]; var seen={};
  document.querySelectorAll(sel).forEach(function(a){
    var re=isChat?/\\/c\\/([a-f0-9-]+)/:/\\/chat\\/([a-f0-9-]+)/;
    var m=a.href.match(re);
    if(m&&!seen[m[1]]){seen[m[1]]=true;convs.push({id:m[1],title:(a.textContent||"").trim()||"Untitled",url:a.href})}
  });
  if(convs.length>0){
    GM_xmlhttpRequest({
      method:"POST",url:API,
      headers:{"Content-Type":"application/json"},
      data:JSON.stringify({source:isChat?"chatgpt":"grok",conversations:convs}),
      onload:function(r){console.log("PIM:",r.responseText)}
    });
  }
})();
```

### Local HTTP Server Requirements
```python
# CORS headers required for cross-origin requests
self.send_header('Access-Control-Allow-Origin', '*')
self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
self.send_header('Access-Control-Allow-Headers', 'Content-Type')
# Handle OPTIONS preflight
def do_OPTIONS(self):
    self.send_response(200)
    for h in [('Access-Control-Allow-Origin','*'),('Access-Control-Allow-Methods','POST,OPTIONS'),('Access-Control-Allow-Headers','Content-Type')]:
        self.send_header(*h)
    self.end_headers()
```

### Why `GM_xmlhttpRequest` works
- Runs with extension privileges → bypasses CSP `connect-src`
- Uses the page's own cookies + Cloudflare clearance (browser already passed the challenge)
- Works on ANY site regardless of CSP strictness
- `@grant GM_xmlhttpRequest` is required in the userscript header

## Alternative: Console-Paste WebSocket (Site-specific)

Works only on sites whose CSP includes `ws://127.0.0.1:*` or `ws://localhost:*`.

### Known CSP patterns (May 2026)

| Site | CSP allows local WebSocket? | CSP allows local HTTP? | Working approach |
|------|---------------------------|----------------------|------------------|
| Grok | ✅ `ws://127.0.0.1:*` (but upgraded to `wss://` on HTTPS pages) | ❌ | Tampermonkey GM_xmlhttpRequest |
| ChatGPT | ❌ (only `wss://*.chatgpt.com`) | ❌ | Tampermonkey GM_xmlhttpRequest |

### Checking a site's CSP
```js
var m=document.querySelector('meta[http-equiv="Content-Security-Policy"], meta[http-equiv="Content-Security-Policy-Report-Only"]');
if(m) console.log(m.content.match(/connect-src [^;]+/));
```

### WebSocket Harvester Pattern (if CSP allows)

1. Start local WebSocket server (port 8898)
2. User opens target site in NORMAL Firefox (no debugging)
3. Paste extraction script into DevTools console
4. Script uses `var ws=new WebSocket("ws://127.0.0.1:8898")` to send data
5. Harvester feeds data into PIM

**⚠️ Caveat:** Firefox on HTTPS pages upgrades `ws://` to `wss://`, which requires an SSL server on the receiving end. If the server doesn't have SSL, the connection fails silently.

## Firefix Console Syntax Compatibility

Firefox DevTools console rejects some JS syntax when pasted:

| Syntax | Issue | Fix |
|--------|-------|-----|
| Arrow functions `()=>{}` | May fail | Use `function(){}` |
| Template literals `` `${var}` `` | Backticks confused | String concat: `'text '+var` |
| `let` / `const` | Redeclaration errors | Use `var` |
| `async` IIFE | May not parse | Use `.then()` or `onmessage` callback |

## Full HTTP Harvester for Tampermonkey

```python
import json, logging
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        msg = json.loads(body)
        convs = msg.get('conversations', [])
        self._ok({"ok": True, "count": len(convs)})
        self.server.processing_needed = True

    def do_OPTIONS(self):
        self.send_response(200)
        for h in [('Access-Control-Allow-Origin','*'),('Access-Control-Allow-Methods','POST,OPTIONS'),('Access-Control-Allow-Headers','Content-Type')]:
            self.send_header(*h)
        self.end_headers()

    def _ok(self, obj):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())
```

## Avoiding Port Ghosts

`taskkill /f` on Firefox leaves TIME_WAIT on the debug port for ~60-120 seconds. Same for Python servers on unclean shutdown.

**Clean kill:** `taskkill //F //PID <parent>` then verify with `netstat -ano | grep <port>` until no LISTENER remains.

## Checking Available Sessions via Cookie Extraction

```bash
sqlite3 "/path/to/profile/cookies.sqlite" \
  "SELECT name, value, host, expiry FROM moz_cookies \
   WHERE host LIKE '%chatgpt%' OR host LIKE '%grok%' OR host LIKE '%x.ai%'"
```

### Key cookies

| Cookie | Site | Meaning |
|--------|------|---------|
| `oai-sc` | `.chatgpt.com` | ChatGPT session token — if present, user was authenticated |
| `cf_clearance` | `.chatgpt.com`, `.x.ai` | Cloudflare challenge token — has expiry timestamp in value |
| `oauth` | `.accounts.x.ai` | Grok OAuth JWT — truncated in DB (ends `...`) |
| `__cf_bm` | Both | Cloudflare bot management — short-lived (~30 min) |

### CF clearance expiry
`cf_clearance` has a Unix timestamp (e.g., `-1780073722-`). Expires ~1-2 hours after last challenge. Even expired, OAuth/session tokens may re-auth through a browser context.
