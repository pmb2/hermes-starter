# Fixing Fermi Logo / Avatar Black Backgrounds on VPS

When the Fermi client's loading screen or server selector shows logos/avatars with a **solid black background** instead of transparency, the image files on disk have an opaque black background that needs to be converted to alpha transparency.

## Diagnosis

Check which images have the problem from the VPS:

```bash
# Install Pillow if not installed
pip3 install Pillow -q

# Check image transparency
python3 -c "
from PIL import Image
import os
for f in ['/opt/fermi/dist/webpage/backus-avatar.webp',
          '/opt/fermi/dist/webpage/backus-logo.png',
          '/opt/fermi/dist/webpage/backus-logo-loading.webp',
          '/opt/spacebar/files/backus-avatar.webp',
          '/opt/spacebar/files/backus-logo-128.png',
          '/opt/fermi/src/webpage/backus-avatar.webp',
          '/opt/fermi/src/webpage/backus-logo.png']:
    if not os.path.exists(f):
        print(f'MISSING: {f}')
        continue
    img = Image.open(f)
    mode = img.mode
    has_alpha = 'A' in mode
    w, h = img.size
    corners = [img.getpixel((x,y)) for x,y in [(0,0),(w-1,0),(0,h-1),(w-1,h-1)]]
    print(f'{os.path.basename(f)}: mode={mode}, alpha={has_alpha}, corners={corners}')
"
```

**Key indicators:**
- `mode=RGB` (no alpha channel at all) — definitely has opaque background
- `mode=RGBA` with corners like `(0,0,0,255)` — has alpha channel but background is still opaque black
- `mode=RGBA` with corners `(0,0,0,0)` — already transparent, no fix needed

## Fix

Use Python PIL to remove near-black pixels from the background by creating an alpha channel:

```python
from PIL import Image

def remove_black_bg(img, threshold=30):
    if img.mode == "RGB":
        img = img.convert("RGBA")
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if r < threshold and g < threshold and b < threshold and a > 0:
                pixels[x, y] = (0, 0, 0, 0)
    return img

# Fix Fermi dist files (what's actually served)
for path, fmt in [
    ("/opt/fermi/dist/webpage/backus-avatar.webp", "webp"),
    ("/opt/fermi/dist/webpage/backus-logo.png", "png"),
]:
    img = Image.open(path)
    kwargs = {"lossless": True, "quality": 100} if fmt == "webp" else {}
    remove_black_bg(img).save(path, **kwargs)
    print(f"Fixed: {path}")

# Fix src files (preserves transparency on rebuild)
import os
for path, fmt in [
    ("/opt/fermi/src/webpage/backus-avatar.webp", "webp"),
    ("/opt/fermi/src/webpage/backus-logo.png", "png"),
]:
    if os.path.exists(path):
        img = Image.open(path)
        kwargs = {"lossless": True, "quality": 100} if fmt == "webp" else {}
        remove_black_bg(img).save(path, **kwargs)
        print(f"Fixed: {path}")
```

## Which Files Need Fixing

| File | Format | Location | Purpose | Typical Issue |
|------|--------|----------|---------|---------------|
| backus-avatar.webp | WebP | Fermi dist/webpage/ | Loading selector avatar | RGB mode, black bg |
| backus-logo.png | PNG | Fermi dist/webpage/ | Loading screen logo | RGBA with opaque black |
| backus-avatar.webp | WebP | Fermi src/webpage/ | Source copy | RGB mode, black bg |
| backus-logo.png | PNG | Fermi src/webpage/ | Source copy | RGBA with opaque black |
| backus-logo-loading.webp | WebP | Fermi dist/webpage/ | Loading animation | Usually already transparent |
| backus-avatar.webp | WebP | Spacebar files/ | Instance config avatar | Usually already transparent |
| backus-logo-128.png | PNG | Spacebar files/ | Instance config image | Usually already transparent |

## No Restart Needed

Fermi serves static files from dist/webpage/ on every request — no restart required after fixing dist files. Browser cache may serve old versions — the user should hard refresh (Ctrl+Shift+R) to see changes.

## Verification

After fixing, verify transparency:

```python
from PIL import Image
for f in ['/opt/fermi/dist/webpage/backus-avatar.webp',
          '/opt/fermi/dist/webpage/backus-logo.png']:
    img = Image.open(f)
    w, h = img.size
    corners = [img.getpixel((x,y)) for x,y in [(0,0),(w-1,0),(0,h-1),(w-1,h-1)]]
    print(f'{f.split(chr(47))[-1]}: mode={img.mode}, corners={corners}')
```

All corners should show (0,0,0,0) — fully transparent.
