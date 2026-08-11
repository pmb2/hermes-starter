# Brand Promo Composition (5-Scene Pattern)

A proven 30-second HyperFrames brand promo video composition. Captures logo reveal,
pain point, price, CTA, and footer in five timed scenes with GSAP entrance/exit.

Tested: HyperFrames 0.7.82, Windows 10, Node 22.14, RTX 3090.
Render: 34s for 783 frames / 26.1s video, 1.3MB MP4, 3 parallel workers.

## Scene Structure

```
Scene 1 (0-6s):   Logo reveal → brand name → tagline → value hook
Scene 2 (6-12s):  Pain point → solution
Scene 3 (12-18s): Price reveal → guarantee
Scene 4 (18-24s): CTA with handwritten accent font
Scene 5 (24-30s): Footer / outbound URL
```

## Composition Contract (v0.7.x)

Each scene is a `<div class="scene clip">` with `data-start`, `data-duration`,
`data-track-index`. The framework manages clip visibility — you drive entrance/exit
via GSAP:

```html
<div id="stage" data-composition-id="my-promo" data-start="0" data-width="1920" data-height="1080">
  <div id="scene1" class="scene clip" data-start="0" data-duration="6" data-track-index="0">
    <!-- scene content -->
  </div>
  <div id="scene2" class="scene clip" data-start="6" data-duration="6" data-track-index="1">
    <!-- scene content -->
  </div>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js"></script>
  <script>
    var tl = gsap.timeline({ paused: true });
    tl.from("#scene1 .logo-mark", { scale: 0, duration: 1, ease: "back.out(1.7)" }, 0);
    tl.to("#scene1", { opacity: 0, duration: 0.4 }, 5.6);
    window.__timelines = window.__timelines || {};
    window.__timelines['my-promo'] = tl;
  </script>
</div>
```

## Entrance Stagger

Stagger elements within each scene by 0.3-0.5s:
- Logo at 0s, brand name at 0.5s, tagline at 0.9s, hook at 1.5s
- Use `back.out(1.5-2)` easing for scale entrances, standard ease for opacity+fade

## Exit Timing

Fade each scene out 0.4s BEFORE the next scene's `data-start`.
Scene 1 ends at 6s → exit tween starts at 5.6s.

## Lint Warnings (informational)

HyperFrames lint may show `gsap_exit_missing_hard_kill` and
`scene_layer_missing_visibility_kill`. These are style warnings — the renderer
handles them. To silence: wrap scene content in inner non-clip `<div>` elements
and target those for exit tweens instead of the clip element.

## Pricing Scene Pattern

```html
<div class="price-old">$349/m</div>    <!-- strikethrough -->
<div class="price-new">$295/m</div>    <!-- large, accent color -->
<div class="price-label">Limited-time launch rate</div>
<div class="guarantee">No contracts. 30-day guarantee.</div>
```

GSAP entrance: old price slides from left, new price scales up with back easing,
label and guarantee fade up sequentially.

## Integration with `hyperframes capture`

```bash
# 1. Capture live page → extracts tokens, screenshots, copy
npx hyperframes capture https://example.com/pitch/ --output my-video --max-screenshots 12 --timeout 30000

# 2. Read extracted/visible-text.txt for copy
# 3. Read extracted/tokens.json for brand colors
# 4. Write composition index.html following this pattern
# 5. Render
npx hyperframes render
```
