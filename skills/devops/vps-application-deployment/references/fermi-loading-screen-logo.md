# Fermi Loading Screen & Instance Selector Logo

## Loading Screen Avatar

Fermi's `app.html` loading screen renders a large logo at 3.5in×3.5in:

```html
<img src="/backus-avatar.webp" style="width: 3.5in; height: 3.5in" />
```

**File:** `src/webpage/backus-avatar.webp` (11460 bytes, 336x336px WebP)

**Creating from SVG** (when no ImageMagick/cwebp available):

Use Python with cairosvg + Pillow on a dev machine, then SCP the result to the VPS:

```bash
# Local machine (with Python + Pillow + cairosvg)
python -c "
import cairosvg
from PIL import Image
import io

with open('/path/to/logo.svg') as f:
    svg = f.read()

png_data = cairosvg.svg2png(bytestring=svg.encode(), output_width=336, output_height=336)
img = Image.open(io.BytesIO(png_data))
img.save('backus-avatar.webp', 'WEBP', quality=90)
"

# Upload to VPS
scp backus-avatar.webp ubuntu@vps:/opt/fermi/src/webpage/
```

**Alternative — SVG direct reference** (no conversion needed):

Instead of creating a WebP, update the HTML to reference the SVG directly:

```html
<img src="/backus-logo.svg" style="width: 3.5in; height: 3.5in" />
```

Browsers render SVG natively at any size. This avoids the conversion step entirely.

## Instance Selector Logo

The login page's instance selector gets its image from `instances.json`:

```json
{
  "name": "the operator",
  "image": "/logo.svg",
  "display": true
}
```

The file `src/webpage/logo.svg` should be the the operator branded logo (chat-bubble + wings + "B" monogram, 135.5×135.5 viewBox). It's identical to `backus-logo.svg`.

## OG Meta Tags

Both `login.html` and `index.html` use `og:image` for social link previews:

```html
<meta content="/backus-logo.svg" property="og:image" />
```

Using SVG here works with most modern social platforms (Discord, Slack, X/Twitter). For wider compatibility, a PNG/WebP fallback could be added.

## Missing File Symptoms

| Missing file | Symptom | Loads on page |
|-------------|---------|---------------|
| `backus-avatar.webp` | Broken image icon on loading screen (3.5in square) | `app.html` |
| `backus-logo.svg` | Missing instance icon on login selector | `login.html` (via `instances.json`) |
| Missing or wrong | Social preview shows generic/dark card | `login.html`, `index.html` |

## File Inventory

| File | Size | Purpose |
|------|------|---------|
| `logo.svg` | 3133 B | Instance selector icon (identical to backus-logo.svg) |
| `backus-logo.svg` | 3133 B | OG meta + header icon + general branding |
| `backus-logo.png` | 26943 B | the operator's actual Spacebar avatar (256x256 PNG) |
| `backus-avatar.webp` | 12252 B | Loading screen avatar (336x336 WebP) |
| `favicon.ico` | 748 B | Browser tab icon |
| `favicon.svg` | 496 B | SVG favicon (modern browsers) |

### Instance Selector Logo Source

The `instances.json` entry for the the operator instance points to `"image": "/backus-logo.png"` — this is the operator's actual Spacebar user avatar fetched from the database and converted. To change it:

1. Find the operator's user in Spacebar DB: `SELECT id, username, avatar FROM users WHERE username='the operator';`
2. The avatar file is at `/opt/spacebar/files/avatars/<user_id>/<avatar_hash>`
3. Convert to WebP/PNG for web serving
4. Copy to **both** `src/webpage/` AND `dist/webpage/` (see dual-directory pitfall in fermi-client-customization.md)
5. Update `instances.json` in both directories
6. Restart Fermi

### Dual Directory Requirement

**All logo/avatar changes must be applied to both `src/webpage/` AND `dist/webpage/`.** See `references/fermi-client-customization.md` for the full dual-directory pitfall explanation.
