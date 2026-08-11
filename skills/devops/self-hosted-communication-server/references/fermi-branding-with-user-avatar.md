# Fermi Branding — Use Actual User Avatar

When the operator says "use the the operator logo/avatar," he means **his actual profile picture on the Spacebar server** — not a generic branded SVG or a logo file.

## Full Chain: Spacebar User → Fermi Logo

### 1. Find the operator's User in Spacebar DB

```bash
# Query DB for users with avatars (exclude bots)
PGPASSWORD='<password>' psql -h 127.0.0.1 -U hamilton -d spacebar \
  -c "SELECT id, username, avatar FROM users WHERE avatar IS NOT NULL AND username NOT LIKE '%bot%' LIMIT 20;"
```

Result:
```
     id      | username | avatar
-------------+----------+----------------------------------
 151045859... | the operator   | 10c3ecdf84fe5d07786b1b4cc3fa605a
```

### 2. Locate Avatar on Spacebar Filesystem

Avatar files are stored at:
```
/opt/spacebar/files/avatars/<user_id>/<avatar_hash>
```

```bash
ls -la /opt/spacebar/files/avatars/<discord-channel-id>/
# → 10c3ecdf84fe5d07786b1b4cc3fa605a  (PNG, 1200×1200)
```

**No authentication needed** — the file is readable directly from the filesystem. Avoid using the CDN API endpoint (`/api/v9/users/:id/avatars/:hash`) which may 500 with mismatched tokens.

### 3. Copy + Convert to Required Formats

From the local machine, SCP the avatar, then convert:

```bash
# Copy from VPS
scp ubuntu@vps:/opt/spacebar/files/avatars/<user_id>/<hash> /tmp/the operator-avatar.png
```

**Required formats for Fermi branding:**

| Usage | Path | Format | Size | 
|-------|------|--------|------|
| Instance selector image | `/backus-logo.png` | PNG | 256×256 |
| Loading screen | `/backus-avatar.webp` | WebP | 336×336 (3.5in @96dpi) |
| Header icon | `/backus-logo.png` | PNG | 256×256 (rendered at 40px CSS) |
| OG social meta | `/backus-logo.png` | PNG | 256×256 |
| Favicon | `/favicon.ico` or `.png` | PNG | 48×48 |

Conversion with Pillow + cairosvg (from Hermes venv):

```python
from PIL import Image
img = Image.open('the operator-avatar.png')

# Instance selector + OG meta (256×256)
logo = img.resize((256, 256), Image.LANCZOS)
logo.save('backus-logo.png', 'PNG')

# Loading screen (336×336 for 3.5in display)
avatar = img.resize((336, 336), Image.LANCZOS)
avatar.save('backus-avatar.webp', 'WEBP', quality=90)

# Favicon (48×48)
fav = img.resize((48, 48), Image.LANCZOS)
fav.save('favicon.png', 'PNG')
```

### 4. Upload to VPS

```bash
scp -i ~/.ssh/oracle_vps backus-logo.png backus-avatar.webp \
  ubuntu@vps:/opt/fermi/src/webpage/
```

### 5. Update HTML + Config References

**Login page** (`login.html`) — OG meta image:
```html
<meta content="/backus-logo.png" property="og:image" />
```

**Index/home page** (`index.html`) — OG meta + header:
```html
<meta content="/backus-logo.png" property="og:image" />
<img src="/backus-logo.png" width="40" alt="the operator icon" />
```

**Loading screen** (`app.html`) — uses larger webp for full-size display:
```html
<img src="/backus-avatar.webp" style="width: 3.5in; height: 3.5in" />
```

**Instance selector** (`instances.json`) — the login picker image:
```json
{
  "name": "the operator",
  "image": "/backus-logo.png"
}
```

**sed one-liner for HTML updates:**
```bash
sed -i 's|/logo.svg|/backus-logo.png|g' login.html index.html app.html
sed -i 's|src="/logo.svg"|src="/backus-logo.png"|g' index.html
```

### 6. Verify

```bash
curl -s http://localhost:8081/backus-logo.png | file -
# → PNG image data, 256 x 256

curl -s http://localhost:8081/backus-avatar.webp | file -
# → RIFF (little-endian) data, Web/P image

grep 'backus-logo\|backus-avatar' login.html index.html app.html
```

## Key Insight

**Do NOT assume existing SVG/PNG files are correct.** The files `logo.svg` and `backus-logo.svg` may have been created as generic branded SVGs (purple chat-bubble with wings + "B"). the operator's actual Spacebar user avatar is always the authoritative source for "the the operator avatar."

**If in doubt, ask** "which exact image should I use?" — or if the operator says "the one my user uses," query the Spacebar DB for his user record and extract the avatar from the filesystem.
