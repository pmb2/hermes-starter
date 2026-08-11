# Fermi Service Worker Cache (Browser Troubleshooting)

The Fermi web client registers a **service worker** (`service.js`) at page load that:
1. Downloads ALL static files listed in `/files.json` into a `"cache"` cache store
2. Intercepts fetch requests and serves cached responses when offline
3. Stores CDN assets (avatars, banners) in a separate `"cdn"` cache store with LRU eviction (100MB limit)
4. Persists across **hard refreshes** (Ctrl+Shift-R does NOT clear service workers)

## Symptom: Old API Endpoint URLs Persist

When the Spacebar server's domain changes (e.g., `discy.domain` → `gc.domain`), the Fermi client may continue making API calls to the old domain even after the server is fully migrated and the user hard-refreshes.

**Root cause — TWO separate persistence mechanisms:**

1. **Service worker cache** — The service worker cached the old `/manifest.json`, `/files.json`, and HTML assets when the page first loaded. Not cleared by hard refresh.

2. **localStorage instance URL** — Fermi stores the Spacebar instance's API/CDN/Gateway URLs in **two localStorage keys** that survive cookie deletion:
   - `instanceinfo` — `JSON.stringify({api, gateway, cdn})` — the parsed server config
   - `fermi_client_instance` — the base URL string the client discovered via `.well-known/spacebar`
   
   These are set during client startup when the client fetches `.well-known/spacebar` or falls back to `instances.json`. They persist across sessions until explicitly cleared. **Clearing cookies does NOT clear localStorage** — the user must clear "Site Data" or explicitly delete these keys.

**Why this breaks on domain consolidation:** Users who connected via the old domain have `instanceinfo` and `fermi_client_instance` set to the old URL. After the old domain is replaced with a 301 redirect to the new domain, every API call to the old URL gets a redirect response without CORS headers — the browser blocks the follow-up. The user is stuck: they can't log in because API calls fail, and they can't fix the URL because the client loads the stale localStorage before they can interact.

See the main skill's Caddy domain consolidation section (`### 🚨 Caddy + Config Domain Consolidation`) for the server-side fix (proxy API paths on old domain instead of redirecting them).

## Quick Fix — Override localStorage from DevTools Console

When a user has a stale instance URL stored but needs immediate access without clearing all site data:

```js
// Set these BEFORE the page finishes loading (run on first tab load or after clearing SW)
localStorage.setItem("instanceinfo", JSON.stringify({
  api: "https://new-domain.example.com/api/v9",
  gateway: "wss://new-domain.example.com/",
  cdn: "https://new-domain.example.com"
}));
localStorage.setItem("fermi_client_instance", "https://new-domain.example.com");
```

After setting these, refresh the page. The client will use the correct URLs immediately.

## Fix: Clear Site Data

**Step 1** — Open DevTools (F12)
**Step 2** — Go to the **Application** tab
**Step 3** — Under **Storage**, click **"Clear site data"** 
  - This removes: localStorage, sessionStorage, IndexedDB, Cookies, Cache Storage, Service Workers

**Alternative** — Unregister the service worker manually:
  1. Application → Service Workers
  2. Click "Unregister" for any service worker on `gc.domain` or `old-domain`
  3. Then refresh

**Alternative (nuclear)** — Chrome Settings → Privacy & Security → Clear browsing data → "All time" → Cookies + Cached images and files

## Prevention

When migrating Spacebar domains, inform users to clear site data *after* the migration is complete. A hard refresh (Ctrl+Shift-R) is NOT sufficient.

## Service Worker Architecture

```
service.js is registered on first page load
├── Listens to "install" event
├── Listens to "activate" event → checks for updates
├── Intercepts ALL fetch requests
│   ├── API calls (/api/*, /_spacebar/*) — NOT cached, passed through
│   ├── Static files — cached in "cache" store
│   ├── CDN assets (avatars, banners) — cached in "cdn" store with LRU (100MB)
│   └── HTML pages — cached in "cache" store
├── Periodic update check via /getupdates endpoint
│   → If content changed: delete old cache, download all files, notify all clients
└── IPC via MessageChannel ports for client communication
    ├── "ForceClear" → deletes "cache" store
    ├── "clearCdnCache" → deletes "cdn" store
    └── "updates" → notifies all tabs of new content
```

The service worker receives messages via `navigator.serviceWorker.controller.postMessage()`:
- `{code: "ForceClear"}` → deletes "cache" cache store
- `{code: "clearCdnCache"}` → deletes "cdn" cache store
- `{code: "setMode", data: "false"/"true"/"offlineOnly"}` → sets caching mode

## Debugging

To check if a service worker is interfering:
1. Open DevTools → Application → Service Workers
2. Check "Update on reload" to force-reload the service worker each refresh
3. Refresh the page — if the issue resolves with "Update on reload" checked, the SW was the root cause
