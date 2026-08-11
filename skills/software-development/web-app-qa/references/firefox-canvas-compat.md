# Firefox Canvas 2D Compatibility

Three Firefox-specific Canvas 2D quirks that cause charts/graphics to render in Chrome but silently fail in Firefox. If a user reports "works in Chrome, blank/nothing in Firefox", check these in order.

## 1. `ctx.roundRect()` — Firefox <112 (2022)

**Problem:** Chrome supports `CanvasRenderingContext2D.roundRect()` since Chrome 99 (March 2022). Firefox added it in Firefox 112 (April 2023). Older Firefox throws `TypeError: ctx.roundRect is not a function`.

**Fix — feature-detect polyfill:**
```javascript
function canvasRoundRect(ctx, x, y, w, h, r) {
  if (ctx.roundRect) { ctx.roundRect(x, y, w, h, r); return; }
  // Manual path fallback for older Firefox
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}
```

**Usage:** Replace all `ctx.roundRect(...)` calls with `canvasRoundRect(ctx, ...)`.

## 2. 8-Digit Hex Colors (`#RRGGBBAA`) — Firefox <106 (2022)

**Problem:** Chrome supports 8-digit hex colors (`#00ff88aa`) in Canvas `fillStyle`, `strokeStyle`, and gradient `addColorStop` since Chrome 99. Firefox only added it in Firefox 106 (October 2022). In older Firefox, `ctx.fillStyle = '#00ff88aa'` fails **silently** — the fill/stroke doesn't render at all. No error thrown, just invisible.

**Fix — hex-to-rgba converter:**
```javascript
function hexAlpha(hex, a) {
  if (!hex || hex.length < 7) return hex;
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
}
```

**Usage:** Replace all `color + 'xx'` patterns in canvas ops with `hexAlpha(color, 0.xx)`:
| Old (Chrome-only) | New (Firefox-safe) |
|---|---|
| `ctx.strokeStyle = color + 'aa'` | `hexAlpha(color, 0.67)` |
| `ctx.fillStyle = p.color + '1a'` | `hexAlpha(p.color, 0.10)` |
| `gradient.addColorStop(0, color + '66')` | `hexAlpha(color, 0.40)` |
| `gradient.addColorStop(1, color + '00')` | `'transparent'` |

**Also applies to CSS inline styles** in innerHTML: `box-shadow: 0 0 8px ${color}66` → `box-shadow: 0 0 8px ${hexAlpha(color, 0.4)}`.

## 3. ResizeObserver vs requestAnimationFrame Execution Order

**Problem:** Setting `canvas.width` or `canvas.height` resets the context transform to the identity matrix. If `handleResize()` fires **before** the first `requestAnimationFrame` callback (which happens in Firefox's rendering pipeline order), the `ctx.scale(dpr, dpr)` from initialization is lost. All subsequent drawing uses unscaled coordinates — chart only renders in the top-left fraction of the canvas.

**Execution order differs by browser:**
- **Chrome:** `rAF callbacks → ResizeObserver → paint` — scale survives the first frame
- **Firefox:** `ResizeObserver → rAF callbacks → paint` — scale is lost before first draw

**Fix — reapply context transform after every resize:**
```javascript
handleResize() {
  const dpr = devicePixelRatio;
  this.width = this.container.clientWidth || 900;
  this.canvas.width = this.width * dpr;
  this.canvas.height = this.height * dpr;
  this.canvas.style.width = this.width + 'px';
  this.canvas.style.height = this.height + 'px';
  // Setting canvas.width/.height resets the context transform — reapply scale
  this.ctx = this.canvas.getContext('2d');
  this.ctx.scale(dpr, dpr);
}
```

## Diagnostic Checklist

When a Canvas 2D chart fails silently in Firefox:

1. **Check Firefox version** — if < 106, 8-digit hex colors are the likely culprit
2. **Check Firefox version** — if < 112, `roundRect` is the likely culprit
3. **Check rendering timing** — if the chart renders part of itself (grid visible, data missing), it's likely the hex color issue. If nothing renders at all, check for JS errors in Firefox console.
4. **Check `canvas.width` resets** — if the chart appears but is shifted/scaled wrong, the context transform was lost after a resize.

## Testing

Always test Canvas 2D charts in both Chrome AND Firefox before declaring a fix complete. curl HTTP 200 says nothing about canvas rendering.
