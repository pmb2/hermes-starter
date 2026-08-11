# Firefox Canvas 2D Compatibility Patterns

Three distinct Firefox canvas issues discovered in the AI Sharp crash-chart implementation. Each has a different browser-version boundary and different fix. Reference for any Canvas 2D project that needs to support Firefox ESR (102+) or older Firefox releases.

## Issue 1: ctx.roundRect() — Firefox < 112

**Symptom:** `TypeError: ctx.roundRect is not a function` — chart stops rendering entirely.

**Support:** Chrome 99+, Firefox 112+ (April 2023). Unspported in Firefox ESR 102.

**Fix — polyfill with fallthrough:**

```javascript
function canvasRoundRect(ctx, x, y, w, h, r) {
  if (ctx.roundRect) { ctx.roundRect(x, y, w, h, r); return; }
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

**Pattern:** Feature-detect `ctx.roundRect` — Chrome uses native method, Firefox falls back to manual path. The two `ctx.roundRect` references (feature-detect check + native call inside the polyfill) are both intentional.

## Issue 2: 8-digit Hex Colors (#RRGGBBAA) in Canvas — Firefox < 106

**Symptom:** Canvas `fillStyle`, `strokeStyle`, and gradient `addColorStop()` with 8-digit hex strings silently fail — the canvas operations produce no visible output but throw no error. Chart grid may appear but trajectories, dots, and labels are invisible.

**Support:** Chrome 99+, Firefox 106+ (October 2022). On Firefox ESR 102, **every** canvas color operation with an 8-digit hex would silently fail.

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

**Usage in canvas operations:**
- `color + 'aa'` → `hexAlpha(color, 0.67)`
- `color + '18'` → `hexAlpha(color, 0.09)`
- `color + '1a'` → `hexAlpha(color, 0.10)`
- `color + '33'` → `hexAlpha(color, 0.20)`
- `color + '66'` → `hexAlpha(color, 0.40)`
- `color + '00'` → `'transparent'`

**Also affects CSS inline styles** (e.g., tooltip box-shadow): `<span style="box-shadow: 0 0 8px ${color}66">` — use `hexAlpha(color, 0.4)` instead.

## Issue 3: ResizeObserver vs requestAnimationFrame Execution Order

**Symptom:** Chart appears in Chrome but is mostly blank or incorrectly scaled in Firefox. Grid is present but trajectories/dots are in wrong positions or invisible.

**Root cause:** `ResizeObserver` and `requestAnimationFrame` fire in **opposite orders** across browsers:

| Browser | Execution order |
|---------|----------------|
| Chrome  | rAF → ResizeObserver → paint |
| Firefox | **ResizeObserver → rAF** → paint |

When the chart constructor:
1. Creates canvas with `ctx.scale(dpr, dpr)` ✅
2. Starts rAF loop :white_check_mark:
3. Observes container with `ResizeObserver` :white_check_mark:

Then in Firefox, ResizeObserver fires BEFORE the first rAF callback. `handleResize()` sets `canvas.width = w * dpr`, which **resets the context transform to the identity matrix**, losing the `scale(dpr, dpr)`. All subsequent `draw()` calls use unscaled coordinates, only painting the top-left `1/dpr` fraction of the canvas.

**Fix — reapply scale in handleResize:**

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

## Browser Support Summary

| Feature | Chrome | Firefox | Firefox ESR 102 |
|---------|--------|---------|-----------------|
| `ctx.roundRect()` | 99+ | 112+ | ❌ |
| 8-digit hex colors | 99+ | 106+ | ❌ |
| `ResizeObserver` | 64+ | 69+ | ✅ |
| `canvas.scale()` | ✓ | ✓ | ✅ |
| `rgba()` in canvas | ✓ | ✓ | ✅ |
