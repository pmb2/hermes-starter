# Fermi Login Troubleshooting — Session Detail

## Environment

- **Server:** Discy (Spacebar fork) running on VPS at `129.153.156.190`
- **Public domain:** `https://discy.your-domain.example`
- **Admin user:** `backus-admin`
- **Admin password:** `backusAdmin2026!`
- **Guild ID:** `<discord-channel-id>`
- **Guild name:** the operator
- **Instance ID (from policies):** `<discord-channel-id>`
- **Frontend:** Fermi client (served by Caddy at `https://discy.your-domain.example`)

## Chain: Caddy → Spacebar

```
Browser → https://discy.your-domain.example → Caddy (443)
  ├── /api/*       → reverse_proxy localhost:3100 (Spacebar API)
  ├── /.well-known/spacebar* → static response {"api":"https://discy.your-domain.example/api/v9"}
  └── /*           → Fermí static files (HTML/JS client)
```

## API Responses (Verified)

### Login — works
```
POST /api/v9/auth/login
→ 200 {"user_id":"<discord-channel-id>","token":"eyJ...","settings":{}}
```

### User info — works
```
GET /api/v9/users/@me
→ 200 {"id":"<discord-channel-id>","username":"backus-admin","bot":false,...}
```

### Gateway URL — returns INTERNAL address (ROOT CAUSE)
```
GET /api/v9/gateway
→ 200 {"url":"ws://localhost:3100/"}  ← ❌ Should be wss://discy.your-domain.example/
```

### Policies — serverName is correct but irrelevant
```
GET /api/v9/policies/instance
→ 200 {
  "serverName": "discy.your-domain.example",
  "instanceName": "the operator",
  ...
}
```

### .well-known — correct
```
GET /.well-known/spacebar
→ 200 {"api":"https://discy.your-domain.example/api/v9"}

GET /.well-known/spacebar-v2
→ 200 {"api":"https://discy.your-domain.example/api/v9"}
```

### Config endpoints — NONE are writable via API
```
PATCH /api/v9/policies/instance → 404
PUT   /api/v9/policies/instance → 404
POST  /api/v9/policies/instance → 404
```

## Fermi Console Logs

Key output when loading login screen:
```
Attempting to fetch .well-known's for https://discy.your-domain.example
No .well-known v2 for https://discy.your-domain.example Cannot read properties of undefined (reading 'baseUrl')
All good  ← Fermi detected the API OK
start / middle / middle2
needs to be implemented
```

When "Other instance" was selected with URL `https://discy.your-domain.example`:
```
WE GOT URL->INSTANCE MAP ENTRY FOR http://localhost:3100
{api: "http://localhost:3100/api/v9", gateway: "ws://localhost:3100", ...}
```

## The localStorage Workaround

Setting these BEFORE the client loads bypasses the URL validation:

```js
localStorage.setItem("instanceinfo", JSON.stringify({
  api: "https://discy.your-domain.example/api/v9",
  gateway: "wss://discy.your-domain.example/",
  cdn: "https://discy.your-domain.example"
}));
localStorage.setItem("fermi_client_instance", "https://discy.your-domain.example");
```

After this, the login button is no longer disabled. The client attempts login (POSTs to the correct API), but if the server still returns bad gateway/CDN URLs, it may overwrite localStorage and re-disable the button on next load.

## Minimal Client Proof of Concept

A hand-rolled HTML chat client at `${USER_HOME}\chat.html` successfully:
1. Logged in via `POST /auth/login`
2. Loaded all 18+ channels (categories + text channels)
3. Rendered the channel list in a sidebar
4. Accepted input for sending messages

The client worked because it bypasses Fermi's URL validation entirely — it just calls the API directly.

## Root Cause Summary

Spacebar was started with `http://localhost:3100` as its base URL (probably via the default config or the DB-stored config). When it constructs the gateway URL, it uses the configured base, yielding `ws://localhost:3100/`. Fermi validates that this URL's hostname matches the API URL's hostname, finds `localhost` ≠ `discy.your-domain.example`, and blocks login.

**Fix requires server-side config update** — either:
- PostgreSQL SQL to update the `config` table JSON
- Environment variables at Spacebar startup (if CONFIG_PATH is set)
- Or a Caddy response rewrite as a band-aid
