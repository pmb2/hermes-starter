# Domain Consolidation with Caddy + CORS

## Problem

When consolidating domains (e.g., `discy.your-domain.example` → `gc.your-domain.example`), a simple HTTP 301 redirect breaks API calls from clients that have the old domain cached. The browser's Same-Origin Policy blocks the redirect because the 301 response lacks `Access-Control-Allow-Origin` headers — even though both domains point to the same server.

Fermi client caches instance URLs in IndexedDB. When it connects to an old domain, it stores that domain as the API endpoint. Even after the server changes `.well-known` to return the new domain, the client ignores it and keeps using the old one.

## Solution: Split Proxy + Redirect (Caddy)

The Caddy config should **proxy infrastructure paths** (API, WebSocket, CDN) on the old domain while **redirecting UI pages** to the new domain:

```
old-domain.com {
    encode gzip

    @api path /api/*
    handle @api { reverse_proxy backend:3100 }

    @ws {
        header Connection *Upgrade*
        header Upgrade websocket
    }
    handle @ws { reverse_proxy backend:3100 }

    @avatars path /avatars/*
    handle @avatars { reverse_proxy backend:3100 }

    @files path /files/*
    handle @files { reverse_proxy backend:3100 }

    @cdn path /cdn/*
    handle @cdn { reverse_proxy backend:3100 }

    # Web UI pages → redirect to new domain
    handle { redir https://new-domain.com{uri} 301 }
}
```

This ensures:
- API calls to the old domain get direct responses with proper `Access-Control-Allow-Origin: *` headers (Spacebar adds these)
- WebSocket connections to the old domain work
- CDN asset serving works
- Browser navigation to the old domain redirects to the new domain cleanly

## Fermi Client Cache Management

Fermi stores instance server URLs in:
- **localStorage** (`instanceinfo`, `userinfos`) — API/base URLs
- **IndexedDB** (via service worker) — cached page assets
- **Service Worker** — intercepts all requests, returns cached responses

### Clearing Stale Instance URLs

```js
// Option 1: Remove specific keys
localStorage.removeItem('instanceinfo');
localStorage.removeItem('userinfos');

// Option 2: Nuke everything
localStorage.clear();
sessionStorage.clear();

// Option 3: Unregister service worker (forces fresh page load)
navigator.serviceWorker.getRegistrations().then(
    r => r.forEach(reg => reg.unregister())
);
```

Then hard refresh (Ctrl+Shift+R).

### Why Clearing Cookies Isn't Enough

Fermi stores the API base URL in localStorage's `instanceinfo` key, **not** in cookies. Clearing cookies removes the auth session token but doesn't clear the stored server URL. The client then tries to log in using the old server URL, which may be a dead domain or a redirect — causing CORS errors that prevent login entirely.

## Verification

```bash
# Confirm old domain API works with CORS
curl -s -D- 'https://old-domain.com/api/auth/login' -X POST \
  -H 'Content-Type: application/json' \
  -d '{"login":"user","password":"pass"}' | head -10
# → Should have Access-Control-Allow-Origin: * and HTTP 200

# Confirm .well-known returns correct URLs
curl -s 'https://new-domain.com/.well-known/spacebar'
# → {"api": "https://new-domain.com/api/v9"}

# Confirm old domain .well-known works too
curl -s 'https://old-domain.com/.well-known/spacebar'
# → {"api": "https://new-domain.com/api/v9"} (proxied to backend)
```
