# Fermi Instance Configuration

## How Fermi Discovers Instances

Fermi fetches `/instances.json` at startup to populate the instance picker on the login page. The file is served by the Fermi Node.js server (not static files).

**Source locations:**
- Source: `src/webpage/instances.json`
- Built: `dist/webpage/instances.json`

The server reads it at startup via:
```typescript
const instances = JSON.parse(
  readFileSync(process.env.JANK_INSTANCES_PATH || __dirname + "/webpage/instances.json").toString(),
);
```

**🚨 After modifying instances.json, restart the server:**
```bash
kill <fermi-pid> && cd /path/to/Fermi && node dist/index.js
```

## Instance Entry Format

```json
{
  "name": "Display name",
  "description": "Shown below the name in the picker",
  "image": "optional URL for an icon",
  "url": "https://your.domain",
  "display": true,
  "urls": {
    "api": "https://your.domain/api/v9",
    "gateway": "wss://your.domain/api/v9",
    "cdn": "https://your.domain"
  }
}
```

- `url` — Used for .well-known discovery (appended with `/.well-known/spacebar`)
- `urls.api` — Base URL for all REST API calls. Must be full path including `/api/v9`
- `urls.gateway` — WebSocket URL for the real-time gateway
- `urls.cdn` — CDN URL for file uploads
- `display: true` — Shows in the welcome page instance list
- `display: false` — Hidden from the welcome page but selectable via URL parameter

## Mixed-Content Fix

When accessing Fermi via `https://domain`, instances with `http://localhost:3001` API URLs fail with Chrome's `Local Network Access detected` errors. The fix is to add an instance with HTTPS/WSS URLs:

```json
{
  "name": "Your Instance",
  "urls": {
    "api": "https://your.domain/api/v9",
    "gateway": "wss://your.domain/api/v9",
    "cdn": "https://your.domain"
  },
  "url": "https://your.domain",
  "display": true
}
```

## Order Matters

The first entry in the array becomes the default selected instance on the login page. Keep your primary instance first.

## .well-known Auto-Discovery

Fermi checks `.well-known/spacebar` and `.well-known/spacebar/client` on the instance URL for automatic configuration. Serve this from your proxy:

```json
// /.well-known/spacebar
{"api": "https://your.domain/api/v9"}
```
