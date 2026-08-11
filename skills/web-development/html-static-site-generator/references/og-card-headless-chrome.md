# OG / Social Share Card via Headless Chrome (when image_generate is unavailable)

Deterministic 1200x630 social card without any image-generation API. Render an HTML
card in a headless browser at exactly 1200x630 and screenshot it. Pixel-exact, no
API key needed, and the design matches the site (same fonts/colors) because it IS
the site's CSS.

## When to use

- `image_generate` fails (no provider key configured) or the style must match a
  specific brand design exactly.
- You want a one-source-of-truth card (edit the HTML, re-render, done).

## Recipe

1. **Write the card as a standalone HTML file** (`og-card.html`) sized exactly
   1200x630: `body { width: 1200px; height: 630px; overflow: hidden; }`. Include
   the brand's fonts via Google Fonts link, a centered composition (icon, brand
   name, divider, tagline), and absolute-positioned glow/grid background layers.
   Keep the text large (brand ~58px, tagline ~27px) since it will be read at
   small thumbnail sizes.

2. **Serve it locally** (needed for the browser to load fonts/CSS):
   ```bash
   cd /path/to/site && python -m http.server 8741   # background
   ```

3. **Render via Chrome DevTools MCP** (chrome-devtools-mcp tools, not the raw
   CDP tool — raw CDP may have no reachable endpoint):
   - `navigate_page {type: "url", url: "http://127.0.0.1:8741/og-card.html"}`
   - `emulate {viewport: "1200x630x1"}` (width x height x deviceScaleFactor;
     scale 1 keeps output pixels == viewport pixels)
   - `take_screenshot {}` — returns a `MEDIA:C:\...\img_<hash>.png` path

4. **Verify the PNG dimensions** (vision_analyze may be unavailable if the model
   config is broken — verify programmatically instead):
   ```bash
   python -c "from PIL import Image; print(Image.open(r'<png>').size)"
   # expect (1200, 630); fallback: struct-unpack the PNG IHDR width/height
   ```

5. **Copy into the deploy repo** and reference it in OG meta:
   ```html
   <meta property="og:image" content="https://<host>/<path>/og-card.png" />
   <meta property="og:image:width" content="1200" />
   <meta property="og:image:height" content="630" />
   ```
   Use PNG/JPG — SVG is NOT reliably supported as og:image by Facebook/LinkedIn.

## Pitfalls

- Screenshot resolution == viewport x deviceScaleFactor. At scale 1, 1200x630
  viewport gives a 1200x630 PNG. Verify with PIL/struct before deploying.
- Don't leave the emulated 1200x630 viewport set — reset to a normal desktop
  viewport (e.g. 1280x900x1) before continuing browser QA of the actual site.
- Heavy pages can make the MCP screenshot call time out (120s); the card itself
  is lightweight, but re-navigate + retry if it does.
