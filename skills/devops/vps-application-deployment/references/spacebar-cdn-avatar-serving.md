# Spacebar CDN / Avatar Serving Workaround

Spacebar's bundled server often fails to register its internal CDN routes for serving avatar, banner, and attachment files. The Express app logs "Request route path was undefined" for `/avatars/*` requests — the avatar image files exist on disk but no route serves them.

## Root Cause

The `CDNServer.start()` method calls `registerRoutes()` from `@spacebar/util` to auto-discover CDN route files in `/opt/spacebar/dist/cdn/routes/`. The avatar route file (`avatars.js`) has:

```javascript
router.get("/:user_id/:hash", cache_1.cache, exports.getAvatar);
```

This should create a GET endpoint at `/avatars/<user_id>/<hash>`. But the route doesn't register — the route path shows as `undefined` in monitoring logs. Likely cause: the CDN and API servers share the same Express `app` object, and the API server temporarily swaps `this.app` to a sub-router during its own route registration, creating a race condition that prevents CDN routes from mounting.

## Quick Fix: Standalone Avatar Server

### Step 1 — Create the server script (`/opt/spacebar/serve-avatars.js`)

```javascript
const http = require('http');
const fs = require('fs');
const path = require('path');

const AVATAR_DIR = '/opt/spacebar/files/avatars';
const PORT = 3456;

const MIME_TYPES = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
  '.svg': 'image/svg+xml',
  '.svgz': 'image/svg+xml',
};

http.createServer((req, res) => {
  let urlPath = req.url.split('?')[0].replace(/\/+$/, '');
  const ext = path.extname(urlPath);
  const lookupPath = ext ? urlPath.slice(0, -ext.length) : urlPath;
  
  // Take the LAST two segments as [userId, hash]
  // handles both /avatars/user/hash and /user/hash
  const segments = lookupPath.split('/').filter(Boolean);
  if (segments.length < 2) {
    res.writeHead(400);
    res.end('Bad request: need at least 2 path segments');
    return;
  }
  
  const userId = segments[segments.length - 2];
  const hash = segments[segments.length - 1];
  const avatarDir = path.join(AVATAR_DIR, userId);
  
  // Try exact hash match
  const exactPath = path.join(avatarDir, hash);
  if (fs.existsSync(exactPath) && fs.statSync(exactPath).isFile()) {
    const mime = MIME_TYPES[path.extname(hash)] || 'image/png';
    res.writeHead(200, { 'Content-Type': mime, 'Cache-Control': 'public, max-age=31536000' });
    fs.createReadStream(exactPath).pipe(res);
    return;
  }
  
  // Fallback: first file in directory (handles animated a_ hash variants)
  if (fs.existsSync(avatarDir)) {
    const files = fs.readdirSync(avatarDir).filter(f => f !== '.' && f !== '..');
    if (files.length > 0) {
      const filePath = path.join(avatarDir, files[0]);
      const ext2 = path.extname(files[0]);
      const mime = MIME_TYPES[ext2] || 'image/png';
      res.writeHead(200, { 'Content-Type': mime, 'Cache-Control': 'public, max-age=31536000' });
      fs.createReadStream(filePath).pipe(res);
      return;
    }
  }
  
  res.writeHead(404);
  res.end('Not found');
}).listen(PORT, '0.0.0.0', () => {
  console.log('Avatar server listening on port ' + PORT);
});
```

### Step 2 — Create systemd service

```ini
[Unit]
Description=Avatar Static File Server for Spacebar
After=network.target
Wants=spacebar.service

[Service]
Type=simple
User=ubuntu
ExecStart=/usr/bin/node /opt/spacebar/serve-avatars.js
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable avatar-server
sudo systemctl start avatar-server
```

### Step 3 — Update Caddy config

In the Caddyfile (bound-mounted from host), change the `/avatars/*` route:

```caddy
# BEFORE (broken — routes to Spacebar's unregistered CDN):
@avatars path /avatars/*
handle @avatars {
    reverse_proxy 172.17.0.1:3100
}

# AFTER (routes to standalone avatar server):
@avatars path /avatars/*
handle @avatars {
    reverse_proxy 172.17.0.1:3456
}
```

Then reload Caddy:
```bash
sudo docker restart hmac-caddy
```

### Step 4 — Add iptables rule

For Docker to host traffic (from Caddy container to avatar server on host), add:

```bash
sudo iptables -I INPUT 13 -p tcp --dport 3456 -j ACCEPT
# Persist across reboots:
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

If `iptables-persistent` is not installed:
```bash
sudo apt-get install -y iptables-persistent
```

## URL Path Handling

Caddy proxies the full URI to the backend. If the Caddy route matches `/avatars/*`, the upstream request becomes `http://backend/avatars/<user_id>/<hash>`. The avatar server uses the **last two path segments** as `[userId, hash]` so it works whether the path contains `/avatars/` prefix or not.

## Verification

```bash
# Direct from avatar server:
curl -s -o /dev/null -w '%{http_code}' http://localhost:3456/<user_id>/<hash>
# → 200

# Via Caddy (full HTTPS chain):
curl -s -o /dev/null -w '%{http_code}' https://gc.your-domain.example/avatars/<user_id>/<hash>
# → 200
```

## File Location

Avatar files are stored at: `/opt/spacebar/files/avatars/<user_id>/<hash>`

The `STORAGE_LOCATION` env var (or default `process.cwd() + "/files"`) determines the root. For the systemd spacebar service with `WorkingDirectory=/opt/spacebar`, location resolves to `/opt/spacebar/files/`.

Each user has a subdirectory named by their user ID, containing one or more avatar hash files. The hash is an MD5 of the image bytes (prefixed with `a_` for animated files).

For up-to-date info on the Spacebar avatar route issue, see the source: `/opt/spacebar/dist/cdn/routes/avatars.js`
