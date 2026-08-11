# 3D Camera Flythrough Implementation Reference

## CSS Setup

```css
perspective: 1000px;
transform-style: preserve-3d;
```

## Generating the Layer Cloud

```js
// 40 geometric objects + 60 particles
for (let i = 0; i < 40; i++) {
  const z = -200 - Math.random() * 800;
  const x = (Math.random() - 0.5) * 200;
  const y = -100 + Math.random() * 200;
  const size = 10 + Math.random() * 50;
  // Append div with translate3d(x, y, z)
}
```

## Scroll Listener

```js
window.addEventListener('scroll', () => {
  const scrollY = window.scrollY;
  const maxScroll = Math.max(totalScroll.scrollHeight - window.innerHeight, 1);
  const progressPct = Math.min(scrollY / maxScroll, 1);
  const cameraZ = -progressPct * 800;

  layers.forEach(l => {
    const relDepth = l.z - cameraZ;
    const scale = 1000 / (1000 + relDepth);
    const driftX = l.origX * (1 - scale) * 0.5;
    const driftY = l.origY * (1 - scale) * 0.3;
    l.el.style.transform =
      `translate3d(${driftX}px,${driftY}px,${relDepth}px) rotateX(${progressPct*5}deg) rotateY(${progressPct*8}deg)`;
  });
}, { passive: true });
```

## Scene Label Keyframes

```js
const sceneRanges = [
  [0, 0.25],    // intro — first quarter
  [0.2, 0.45],  // craft — overlaps slightly
  [0.4, 0.65],  // trust — overlaps
  [0.6, 1.0],   // cta — last portion
];
// For each label: fade in over first 15% of range, stay, fade out over last 15%
```

## scroll-world Pipeline Asset Structure

When using Higgsfield or ComfyUI + Seedance:

```
assets/
  stills/        # GPT Image 2 / FLUX diorama images
  dives/         # Seedance .mp4 clips (one per scene)
  connectors/    # Seedance .mp4 clips (N-1 connecting scenes)
  posters/       # First frame extracted from each dive clip
```

## scrub-engine.js Integration

The vanilla JS scrub engine (from cth9191/scroll-world references) takes:
- `brand`: name, href
- `sections[]`: each with id, label, still, clip, accent, eyebrow, title, body, tags, cta
- `connectors[]`: clip URLs between sections
- `diveScroll`, `connScroll` scroll distances per clip

It builds its own DOM and CSS inside a container you provide. Drops into
any framework: plain HTML, Astro, Next.js, Vue.

## Gotchas

- **Seams must be frame-identical.** Connector clips must use the actual
  rendered frames of their neighbours as start/end images. Same prompt
  re-renders slightly differently — use the extracted frame, not the still.
- **SSIM gate** scores every seam from encoded files before the page loads.
  Score < 0.95 = visible pop. Re-generate the connector.
- **Phone handling:** clips should be 720p, -g 8, +faststart for smooth
  seeking. Mobile variants can be 720p, -g 4. Engine coalesces seeks to
  prevent decoder queue pileup on fast scroll flicks.
- **Caveats:** Higgsfield generations take 3-8 min each. Always run detached
  (background) and poll — never foreground blocking.
