# Animation Patterns for Single-File HTML Pages

Three composable, zero-dependency animation patterns that work together on a single
HTML page. All use pure CSS transitions + vanilla JS. No libraries, no CDN.

Tested on the the company pitch page (v4, 27KB inline). Designed to work across
light and dark mode via CSS custom properties.

## 1. IntersectionObserver Scroll-Reveal

Sections fade in and slide up as the user scrolls. Lightweight — no scroll event
listener, no requestAnimationFrame.

### CSS

```css
.reveal {
  opacity: 0; transform: translateY(30px);
  transition: opacity 0.7s ease, transform 0.7s ease;
}
.reveal.visible {
  opacity: 1; transform: translateY(0);
}
```

### JS

```js
var reveals = document.querySelectorAll('.reveal');
if (reveals.length && 'IntersectionObserver' in window) {
  var observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) entry.target.classList.add('visible');
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
  reveals.forEach(function(el) { observer.observe(el); });
} else {
  // Fallback for old browsers: show all immediately
  reveals.forEach(function(el) { el.classList.add('visible'); });
}
```

### Usage

Add `class="reveal"` to each section you want to animate in: hero, stat bar,
phone mockup, benefits, CTA block. The observer fires once (`entry.isIntersecting`
is checked, class is added; no unobserve needed for one-shot reveal).

Threshold 0.15 means the element must be 15% visible before triggering.
Root margin -40px delays trigger slightly so elements appear as they're
comfortably in view.

## 2. Particle Canvas Background

Floating accent-colored particles drifting across the page. Uses a fixed-position
canvas behind all content with pointer-events disabled so it never blocks clicks.

### HTML

```html
<canvas id="particleCanvas"></canvas>
```

### CSS

```css
#particleCanvas {
  position: fixed; inset: 0; z-index: 0; pointer-events: none; opacity: 0.4;
}
html[data-theme="light"] #particleCanvas { opacity: 0.25; }
```

The wrap element needs `position: relative; z-index: 1` to sit above the canvas.

### JS

```js
var canvas = document.getElementById('particleCanvas');
if (canvas) {
  var ctx = canvas.getContext('2d');
  var particles = [];
  var COUNT = 60; // tune for visual density
  var accentRGB = '56,224,56'; // match brand accent

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  for (var i = 0; i < COUNT; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4 - 0.1,
      r: Math.random() * 2 + 0.5,
      o: Math.random() * 0.6 + 0.2
    });
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0) p.x = canvas.width; if (p.x > canvas.width) p.x = 0;
      if (p.y < 0) p.y = canvas.height; if (p.y > canvas.height) p.y = 0;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(' + accentRGB + ',' + p.o + ')';
      ctx.fill();
    }
    requestAnimationFrame(draw);
  }
  draw();
}
```

Particles drift upward slightly (vy bias of -0.1) and wrap around screen edges.
60 particles at 0.4 opacity is subtle; tune COUNT for more or less density.

## 3. Timer Tick-Pop Animation

Makes a countdown timer feel alive by popping the seconds digit on every change.

### CSS

```css
.timer-digits .num.pulse {
  animation: tick-pop 0.3s ease;
}
@keyframes tick-pop {
  0%   { transform: scale(1); }
  50%  { transform: scale(1.25); color: var(--accent); }
  100% { transform: scale(1); }
}
```

### JS (inside the timer tick function)

```js
if (secondsEl) {
  var oldVal = secondsEl.textContent;
  secondsEl.textContent = pad(secs);
  if (oldVal !== secondsEl.textContent) {
    secondsEl.classList.remove('pulse');
    void secondsEl.offsetWidth; // force reflow to restart animation
    secondsEl.classList.add('pulse');
  }
}
```

The `void el.offsetWidth` trick forces a reflow, which restarts the CSS animation
from frame 0. Without it, consecutive `classList.add('pulse')` calls do nothing
because the class is already present.

## Combining All Three

All three patterns are independent and firewall via try/catch. Order doesn't matter.
The particle canvas sits behind content (z-index 0), reveal sections stack above
(z-index 1 via the wrap element), timer animation is self-contained.
