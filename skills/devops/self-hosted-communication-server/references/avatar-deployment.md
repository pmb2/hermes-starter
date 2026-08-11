# Bot Avatar Deployment for Spacebar

## Problem

Spacebar's CDN API (`PATCH /users/@me` with base64 data URI) **rejected avatar uploads** until Caddy CDN routing was fixed. The root cause was NOT the Spacebar CDN validation — it was Caddy routing `/avatars/` paths to the web client SPA (port 8081) instead of the Spacebar backend (port 3100). Once Caddy was fixed, the API method works fine.

## Two Verified Methods

### Method 1: API PATCH (requires CDN routing fix)

See the main skill's "Bot Avatar Upload → Method A: API PATCH" section. Works after adding these Caddy routes:

```caddy
@cdn path /avatars/* /icons/* /files/* /cdn/*
handle @cdn { reverse_proxy <spacebar-backend>:3100 }
```

Each bot PATCHes its own `/users/@me` with a base64 data URI. Returns the avatar hash which clients use to construct the CDN URL.

### Method 2: Direct File Copy + DB Update (works regardless of CDN routing)

Use this when the API method is unavailable (e.g., CDN routing not yet fixed, or no direct API access to the Spacebar backend).

### Step 1: Generate Avatar Images

Use Python PIL to create 256×256 PNGs from a base logo, tinted per team:

```python
from PIL import Image
logo = Image.open("base-avatar.png").convert("RGBA").resize((256, 256), Image.LANCZOS)
color = (212, 175, 55)  # Gold for council
img = logo.copy()
pixels = img.load()
for y in range(img.height):
    for x in range(img.width):
        r, g, b, a = pixels[x, y]
        factor = 0.35
        pixels[x, y] = (min(255, int(r*(1-factor)+color[0]*factor)),
                        min(255, int(g*(1-factor)+color[1]*factor)),
                        min(255, int(b*(1-factor)+color[2]*factor)), a)
import hashlib
hash_val = hashlib.md5(f"{bot_name}-backus-2026".encode()).hexdigest()
img.save(f"/tmp/avatars/{hash_val}", "PNG")
```

### Step 2: Deploy to VPS

```bash
ssh -i ~/.ssh/key ubuntu@<vps> "mkdir -p /opt/spacebar/files/avatars/{user_id}"
scp -i ~/.ssh/key avatar_file ubuntu@<vps>:/opt/spacebar/files/avatars/{user_id}/{hash}
ssh -i ~/.ssh/key ubuntu@<vps> "chown -R ubuntu:ubuntu /opt/spacebar/files/avatars/{user_id}"
```

### Step 3: Update Database

```sql
UPDATE users SET avatar = '<hash>' WHERE id = <user_id>;
```

Execute via Docker: `sudo docker exec -i mobile-mechanic_postgres_1 psql -U hamilton -d spacebar < update_avatars.sql`

### Step 4: Restart Spacebar (required — cached in memory)

### Step 5: Verify

```bash
sudo docker exec mobile-mechanic_postgres_1 psql -U hamilton -d spacebar -c \
  "SELECT COUNT(*) FROM users WHERE bot = true AND avatar IS NOT NULL;"
# Expected: total bot count
```

## File Format

| Property | Value |
|----------|-------|
| Format | PNG (RGBA) |
| Size | 256×256 |
| Storage | `/opt/spacebar/files/avatars/{user_id}/{hash}` |
| DB column | `users.avatar` = hash string (no extension) |

## Team Colors Used (the operator Fleet)

| Team | Color |
|------|-------|
| Executive Council | Gold (212,175,55) |
| Specialists | Teal (0,168,107) |
| Pulse | Blue (88,101,242) |
| Hermes Dev | Purple (155,89,182) |
| Trading | Yellow (241,196,15) |
