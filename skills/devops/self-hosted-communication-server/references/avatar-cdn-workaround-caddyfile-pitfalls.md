# Avatar CDN Workaround & Caddyfile Pitfalls

## Spacebar CDN Route Failure

**Problem:** The bundled Spacebar server (`dist/bundle/start.js`) does not register CDN avatar routes properly. Express returns `"Request route path was undefined"` for all `/avatars/*` requests — a CDN initialization issue where `registerRoutes` fails to mount the avatar route handlers from `dist/cdn/routes/avatars.js`.

**Impact:** All bot/user profile avatars return 404, appearing as broken images in the client.

**Diagnosis:**
1. Check if avatar files exist on disk: `ls /opt/spacebar/files/avatars/<user_id>/`
2. Test the avatar API directly: `curl http://localhost:3100/avatars/<user_id>/<hash>` → 404
3. Check server logs for `"Request route path was undefined? Request path: /avatars/..."` in journalctl
4. Compare with a direct API ping: `curl http://localhost:3100/api/ping` → 200 (confirms Spacebar is running, CDN just doesn't mount)

**Workaround — Standalone Avatar Server:**

Instead of fixing the Spacebar CDN (which requires source changes and rebuilding a memory-heavy TS project on a VPS), run a lightweight static file server behind Caddy.

### Step 1: Create the Avatar Server

Create `/opt/spacebar/serve-avatars.js`:

```javascript
const http = require('http');
const fs = require('fs');
const path = require('path');

const AVATAR_DIR = '/opt/spacebar/files/avatars';
const PORT = 3456;

const MIME_TYPES = {
  '.png': 'image/png', '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg', '.gif': 'image/gif',
  '.webp': 'image/webp', '.svg': 'image/svg+xml',
};

http.createServer((req, res) => {
  let urlPath = req.url.split('?')[0].replace(/\/+$/, '');
  const ext = path.extname(urlPath);
  const lookupPath = ext ? urlPath.slice(0, -ext.length) : urlPath;
  const segments = lookupPath.split('/').filter(Boolean);
  if (segments.length < 2) { res.writeHead(400); res.end('Bad request'); return; }
  
  // Take LAST two segments to handle both /avatars/user/hash and /user/hash
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
  
  // Fallback: first file in directory
  if (fs.existsSync(avatarDir)) {
    const files = fs.readdirSync(avatarDir).filter(f => f !== '.' && f !== '..');
    if (files.length > 0) {
      const filePath = path.join(avatarDir, files[0]);
      const mime = MIME_TYPES[path.extname(files[0])] || 'image/png';
      res.writeHead(200, { 'Content-Type': mime, 'Cache-Control': 'public, max-age=31536000' });
      fs.createReadStream(filePath).pipe(res); return;
    }
  }
  res.writeHead(404); res.end('Not found');
}).listen(PORT, '0.0.0.0', () => console.log('Avatar server on port ' + PORT));
```

### Step 2: Create Systemd Service

`/etc/systemd/system/avatar-server.service`:

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

### Step 3: Add iptables Rule

```bash
sudo iptables -I INPUT 13 -p tcp --dport 3456 -j ACCEPT
# Make persistent:
sudo apt-get install -y iptables-persistent
sudo sh -c 'iptables-save > /etc/iptables/rules.v4'
```

### Step 4: Update Caddyfile

Only the `/avatars/*` route should point to port 3456. All other routes (API, WebSocket, files, CDN, well-known) must remain on port 3100:

```caddy
@avatars path /avatars/*
handle @avatars {
    reverse_proxy 172.17.0.1:3456
}
```

## ⚠️ Caddyfile Pitfall: `sed -i -g` Replaces ALL Matches

**When updating Caddy proxy targets, NEVER use `sed -i -g` (global flag) when the old string appears in multiple semantically different route blocks.**

Example of what **WILL break everything**:

```bash
# ❌ DANGEROUS — this replaces ALL occurrences of 3100 with 3456:
sudo sed -i 's|reverse_proxy 172.17.0.1:3100|reverse_proxy 172.17.0.1:3456|g' Caddyfile
```

The Caddyfile has `reverse_proxy 172.17.0.1:3100` in FIVE different route groups:
- `@api` (Spacebar API)
- `@ws` (WebSocket)
- `@files` (file attachments)
- `@cdn` (CDN assets)
- `@spacebar_well_known` (well-known endpoints)
- `@avatars` (should be 3456, not 3100)

The global replace changes ALL of them to 3456, which means:
- API calls → avatar server → 404 "Not found"
- Login → avatar server → 404
- WebSocket connections → avatar server → 502
- File uploads → avatar server → 404

**✅ Safe approach — write the entire Caddyfile:**

```bash
sudo tee /home/ubuntu/Caddyfile > /dev/null << 'CADDYEOF'
# ... full correct content with only /avatars/* → 3456 ...
CADDYEOF
```

Or use a targeted edit on the specific block:
```bash
# Target only the avatars block by using context anchors
sudo sed -i '/@avatars/,/^}/s|172.17.0.1:3100|172.17.0.1:3456|' Caddyfile
```

**Verification after any Caddyfile edit:**

```bash
# Check counts — should have exactly N occurrences of 3100 and 1 per domain of 3456
grep -c '172.17.0.1:3100' Caddyfile  # Expected: 10 (5 routes × 2 domains)
grep -c '172.17.0.1:3456' Caddyfile  # Expected: 2 (avatars on gc + avatars on discy)

# Test every route group via the Caddy container:
sudo docker exec hmac-caddy curl -s -o /dev/null -w '%{http_code}' 'https://gc.your-domain.example/api/ping'
# Expected: 200 ({"ping":"pong!"})
sudo docker exec hmac-caddy curl -s -o /dev/null -w '%{http_code}' 'https://gc.your-domain.example/avatars/<user_id>/<hash>'
# Expected: 200 (PNG image)
```

## Reverse Proxy Debugging Flow

When diagnosing a "page broken" or "can't connect" issue through Caddy, check each layer independently:

```
Layer 1: Backend directly     curl http://localhost:3100/api/ping
Layer 2: From Docker container curl http://172.17.0.1:3100/api/ping  (inside Caddy container)
Layer 3: Via Caddy HTTPS       curl https://gc.your-domain.example/api/ping
Layer 4: External              test from different machine/network
```

Each layer gives a different signal:
- **Layer 1 fails**: Backend (Spacebar/Fermi) is down or misconfigured
- **Layer 2 fails, Layer 1 passes**: Docker network or iptables blocking the port
- **Layer 3 fails, Layer 2 passes**: Caddy config error (wrong proxy target, wrong port)
- **Layer 4 fails, Layer 3 passes**: External DNS, TLS, or firewall issue

**Quick iptables check for new ports:**
```bash
sudo iptables -L INPUT -n --line-numbers | grep <port>
# If not listed on an ACCEPT line before the final REJECT, add it:
sudo iptables -I INPUT 13 -p tcp --dport <port> -j ACCEPT
```

**Docker container connectivity test:**
```bash
sudo docker exec <container> curl -s -o /dev/null -w '%{http_code}' http://172.17.0.1:<port>/path
```

## Password Recovery via DB

When a user can't log in (forgot password, DB migration invalidated hash):

```bash
cd /opt/spacebar
HASH=$(node -e "const bcrypt = require('bcrypt'); console.log(bcrypt.hashSync('NewPassword123!', bcrypt.genSaltSync(10)));")
sudo docker exec -i mobile-mechanic_postgres_1 psql -U hamilton -d spacebar \
  -c "UPDATE users SET data = jsonb_set(COALESCE(data, '{}'::jsonb), '{hash}', '\"$HASH\"', true) WHERE username = 'the operator'"
```

The password is stored in `users.data->>'hash'` as a bcrypt hash. The `jsonb_set` function updates just the hash field without touching the rest of the JSON data. After resetting, the user should also have `valid_tokens_since` updated if they were already logged in (invalidates existing JWTs).
