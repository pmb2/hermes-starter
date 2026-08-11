# Avatar CDN Workaround — Static File Server

When Spacebar's bundled server doesn't register CDN avatar routes (all `/avatars/*` return 404 with "Request route path was undefined" in logs), the avatar files still exist on disk but no Express route serves them.

## Symptom

- Browser shows broken images for all bot/user avatars
- `curl https://gc.your-domain.example/avatars/<user_id>/<hash>` returns 404
- Spacebar server logs show: `[Monitoring] Request route path was undefined? Request path: /avatars/...`
- But avatar files exist at `/opt/spacebar/files/avatars/<user_id>/<hash>`

## Root Cause

The CDN routes (avatars, banners, emojis, etc.) are auto-registered via `registerRoutes()` from `@spacebar/util`. Due to a race condition in how the shared Express app is initialized between the API server and CDN server (both use `this.app` which gets temporarily swapped during API server init), the CDN routes don't get registered at the expected paths.

This is a Spacebar bundling issue, not a config error. The compiled route files exist (`/opt/spacebar/dist/cdn/routes/avatars.js`) but aren't mounted on the Express app.

## Fix: Static Avatar Server

Create a standalone Node.js HTTP server that serves avatar files directly from the filesystem, then route Caddy's `/avatars/*` to it instead of Spacebar.

### 1. Create the Server

Location: `/opt/spacebar/serve-avatars.js`

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
};

http.createServer((req, res) => {
  let urlPath = req.url.split('?')[0].replace(/\/+$/, '');
  const ext = path.extname(urlPath);
  const lookupPath = ext ? urlPath.slice(0, -ext.length) : urlPath;
  
  // Take LAST two segments as [userId, hash] — handles /avatars/user/hash AND /user/hash
  const segments = lookupPath.split('/').filter(Boolean);
  if (segments.length < 2) {
    res.writeHead(400);
    res.end('Bad request: need at least 2 path segments');
    return;
  }
  
  const userId = segments[segments.length - 2];
  const hash = segments[segments.length - 1];
  const avatarDir = path.join(AVATAR_DIR, userId);
  
  // Try exact hash match first
  const exactPath = path.join(avatarDir, hash);
  if (fs.existsSync(exactPath) && fs.statSync(exactPath).isFile()) {
    const mime = MIME_TYPES[path.extname(hash)] || 'image/png';
    res.writeHead(200, { 'Content-Type': mime, 'Cache-Control': 'public, max-age=31536000' });
    fs.createReadStream(exactPath).pipe(res);
    return;
  }
  
  // Fallback: first file in directory (handles animated hash variants)
  if (fs.existsSync(avatarDir)) {
    const files = fs.readdirSync(avatarDir).filter(f => f !== '.' && f !== '..');
    if (files.length > 0) {
      const filePath = path.join(avatarDir, files[0]);
      const mime = MIME_TYPES[path.extname(files[0])] || 'image/png';
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

### 2. Create systemd Service

```bash
cat > /etc/systemd/system/avatar-server.service << 'SERVICEEOF'
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
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable avatar-server
sudo systemctl start avatar-server
```

### 3. Add iptables Rule

Docker containers can't reach new ports without explicit iptables allowance:

```bash
sudo iptables -I INPUT -p tcp --dport 3456 -j ACCEPT
# Make persistent:
sudo apt-get install -y iptables-persistent  # if not installed
sudo sh -c 'iptables-save > /etc/iptables/rules.v4'
```

### 4. Update Caddyfile

In the Caddyfile, change the `/avatars/*` handler to point to the avatar server:

```caddy
@avatars path /avatars/*
handle @avatars {
    reverse_proxy 172.17.0.1:3456
}
```

**⚠️ CRITICAL:** Use `sed` with a SPECIFIC pattern to replace only the avatar route. Do NOT use a catch-all replace like:
```bash
# DANGEROUS — replaces ALL 3100→3456 across the whole Caddyfile:
sed -i 's|reverse_proxy 172.17.0.1:3100|reverse_proxy 172.17.0.1:3456|g' Caddyfile
```
This will break API, WebSocket, files, and CDN routes. Instead, edit the Caddyfile manually or use a targeted `sed` that only matches the avatar block.

### 5. Restart Caddy

```bash
sudo docker restart hmac-caddy
```

### 6. Verify

```bash
curl -s -o /dev/null -w "HTTP %{http_code}" https://gc.your-domain.example/avatars/<user_id>/<hash>
# Should return 200 with image data
curl -s https://gc.your-domain.example/avatars/<user_id>/<hash> | file -
# Should show PNG/WebP image data
```
