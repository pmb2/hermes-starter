# Web Animation Patterns from Top-Tier Open Source Repos

When asked to "add smooth animations" or "level up UI/UX" on a dashboard or web page, systematically mine inspiration from starred repos known for excellent UI. This reference documents concrete animation patterns extracted from four of the most influential open-source UI projects.

## Pattern Sources

| Repo | Stars | Best For |
|------|-------|----------|
| **shadcn-ui/ui** | 114K | Micro-interactions, skeleton loaders, progress rings, button states |
| **lobehub/lobehub** | 76K | AI-agent UI, floating particles, glassmorphism, gradient text |
| **open-webui/open-webui** | 136K | Live status indicators, toast notifications, dark theme patterns |
| **supabase/supabase** | 102K | Dashboard data presentation, staggered entries, scroll reveal |

## Animation Pattern Catalog

### 1. Background Particle System (lobehub)

40-60 semi-transparent dots slowly drifting across the screen at 60fps via a Canvas 2D renderer.

```html
<canvas id="particle-canvas"></canvas>
<script>
function initParticles() {
  const canvas = document.getElementById('particle-canvas');
  const ctx = canvas.getContext('2d');
  let particles = [];
  function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
  resize(); window.addEventListener('resize', resize);
  for (let i = 0; i < 40; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      size: Math.random() * 2 + 0.5,
      speedX: (Math.random() - 0.5) * 0.3,
      speedY: (Math.random() - 0.5) * 0.3,
      opacity: Math.random() * 0.3 + 0.05,
    });
  }
  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(p => {
      p.x += p.speedX; p.y += p.speedY;
      if (p.x < 0) p.x = canvas.width; if (p.x > canvas.width) p.x = 0;
      if (p.y < 0) p.y = canvas.height; if (p.y > canvas.height) p.y = 0;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0, 255, 136, ${p.opacity})`;
      ctx.fill();
    });
    requestAnimationFrame(animate);
  }
  animate();
}
</script>
```

**Key decisions:** Canvas (not DOM) for performance at 60fps. Color matches accent. Opacity < 0.3 so it's subtle. `pointer-events: none` on the canvas.

### 2. Skeleton Loading (shadcn-ui)

Shimmer placeholders shown while API data loads, replaced by real content once data arrives.

```css
.skeleton {
  background: linear-gradient(90deg, var(--bg-card) 25%, var(--bg-card-hover) 50%, var(--bg-card) 75%);
  background-size: 200% 100%;
  animation: skeletonPulse 1.5s ease infinite;
  border-radius: var(--radius-sm);
}
@keyframes skeletonPulse {
  0% { opacity: 0.6 }
  50% { opacity: 1 }
  100% { opacity: 0.6 }
}
```

```javascript
function showSkeleton(containerId, type = 'card', count = 3) {
  const container = document.getElementById(containerId);
  if (!container) return;
  let html = '';
  for (let i = 0; i < count; i++) {
    if (type === 'card') html += `<div class="skeleton skeleton-card" style="animation-delay:${i * 0.1}s"></div>`;
    if (type === 'pick') html += `<div class="card skeleton" style="height:160px;animation-delay:${i * 0.1}s"></div>`;
  }
  container.innerHTML = html;
}

// Usage on page load:
showSkeleton('leaderboardContainer', 'card', 5);
showSkeleton('picksContainer', 'pick', 3);
loadAllData(); // Replaces skeletons with real data
```

### 3. SVG Confidence / Progress Ring (shadcn-ui)

Circular progress indicator using SVG `stroke-dasharray` and `stroke-dashoffset`.

```html
<svg width="28" height="28" viewBox="0 0 28 28">
  <circle class="ring-bg" cx="14" cy="14" r="11"/>
  <circle class="ring-fill" cx="14" cy="14" r="11"
    stroke="${color}" stroke-dasharray="${circumference}"
    stroke-dashoffset="${offset}"
    style="transition: stroke-dashoffset 1.2s cubic-bezier(0.16,1,0.3,1)"/>
</svg>
```

```javascript
// r=11 → circumference = 2 * PI * 11 = 69.12
const circumference = 2 * Math.PI * 11;
const offset = circumference - (confidence / 10) * circumference;
const ringColor = confidence >= 8 ? '#00ff88' : confidence >= 6 ? '#f59e0b' : '#ef4444';
```

**CSS:** SVG circles need `fill: none`, `stroke-linecap: round`, and `transform: rotate(-90deg)` to start at 12 o'clock.

### 4. Animated Number Counting (supabase/shadcn-ui)

Numbers animate from a starting value to the final value with cubic ease-out over ~1200ms.

```javascript
function animateValue(el, start, end, duration = 1200) {
  if (!el) return;
  const startTime = performance.now();
  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    const current = start + (end - start) * eased;
    el.textContent = '$' + current.toFixed(2);
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}
```

**Usage tip:** Start from ~90% of the real value so the user perceives movement immediately. Use `requestAnimationFrame` (not `setInterval`) for smooth 60fps animation.

### 5. Staggered Entry Animation (supabase)

List items fade in one-by-one with incremental delay.

```javascript
entries.forEach((entry, i) => {
  const div = document.createElement('div');
  div.style.opacity = '0';
  div.style.transform = 'translateY(16px)';
  div.style.transition = `all 0.4s cubic-bezier(0.16,1,0.3,1) ${i * 0.06}s`;
  container.appendChild(div);
  // Trigger on next frame to ensure transition fires
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      div.style.opacity = '1';
      div.style.transform = 'translateY(0)';
    });
  });
});
```

**Double `requestAnimationFrame`:** The first rAF is for the browser to paint the initial state (opacity:0). The second triggers the transition. Without this, both states paint in the same frame and no animation occurs.

### 6. Toast Notifications (open-webui)

Slide-down notification bar with auto-dismiss.

```javascript
function showToast(msg, type = 'success', duration = 3000) {
  const container = document.getElementById('toastContainer');
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span class="toast-icon">${icons[type]}</span> ${msg}`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}
```

```css
.toast-container {
  position: fixed; top: 80px; right: 24px; z-index: 1000;
  display: flex; flex-direction: column; gap: 8px; pointer-events: none;
}
.toast {
  pointer-events: auto;
  padding: 12px 20px; border-radius: var(--radius-md);
  background: var(--bg-card); border: 1px solid var(--border);
  backdrop-filter: blur(16px);
  font-size: 13px; font-weight: 500;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  animation: slideDown 0.3s var(--ease-out);
  display: flex; align-items: center; gap: 8px;
}
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-12px); }
  to { opacity: 1; transform: translateY(0); }
}
```

### 7. Scroll-Triggered Reveal (lobehub)

Sections animate in when scrolled into view using IntersectionObserver.

```javascript
function initScrollReveal() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

  document.querySelectorAll('.animate-in').forEach(el => observer.observe(el));
}

// CSS:
.animate-in {
  opacity: 0;
  transform: translateY(24px);
  transition: opacity 0.7s cubic-bezier(0.16,1,0.3,1),
              transform 0.7s cubic-bezier(0.16,1,0.3,1);
}
.animate-in.visible {
  opacity: 1;
  transform: translateY(0);
}
```

**Performance tip:** `unobserve()` after first reveal so already-visible sections don't keep firing.

### 8. Confetti Burst (custom)

Small colored squares that fly outward on milestone/achievement unlock.

```javascript
function fireConfetti(count = 20) {
  const container = document.getElementById('confettiContainer');
  const colors = ['#00ff88', '#7c3aed', '#f59e0b', '#ef4444', '#3b82f6', '#ff6b9d'];
  for (let i = 0; i < count; i++) {
    const piece = document.createElement('div');
    piece.className = 'confetti-piece';
    piece.style.background = colors[Math.floor(Math.random() * colors.length)];
    piece.style.left = (Math.random() * 200 - 100) + 'px';
    piece.style.top = (Math.random() * 200 - 100) + 'px';
    piece.style.animationDuration = (1 + Math.random()) + 's';
    container.appendChild(piece);
    setTimeout(() => piece.remove(), 3000);
  }
}
```

```css
.confetti-container {
  position: fixed; top: 50%; left: 50%; pointer-events: none; z-index: 999;
}
.confetti-piece {
  position: absolute; width: 8px; height: 8px; border-radius: 2px;
  animation: confettiBurst 1.5s cubic-bezier(0.16,1,0.3,1) forwards;
}
@keyframes confettiBurst {
  0% { transform: translateY(0) scale(1); opacity: 1; }
  100% { transform: translateY(-300px) scale(0.3); opacity: 0; }
}
```

### 9. Micro-Interactions: Button Press (shadcn-ui)

Scale down on active, gradient sweep on hover.

```css
.btn {
  position: relative; overflow: hidden;
  transition: all 0.2s cubic-bezier(0.34,1.56,0.64,1);
}
.btn::after {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
  transform: translateX(-100%); transition: transform 0.6s;
}
.btn:hover::after { transform: translateX(100%); }
.btn:active { transform: scale(0.97); }
```

### 10. Card Hover Effects (shadcn-ui + supabase)

Border glow, left accent bar, translate lift, and avatar scale.

```css
.card {
  position: relative; overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
}
.card::before {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 2px;
  background: var(--accent); opacity: 0; transition: all 0.3s;
}
.card:hover {
  border-color: var(--border-hover); transform: translateX(4px);
  box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}
.card:hover::before { opacity: 1; }
.card:hover .avatar { transform: scale(1.05) rotate(-3deg); }
```

### 11. Live Status Indicator (open-webui)

Pulsing dot with concentric rings.

```html
<div class="status-dot">
  <span class="dot online" id="statusDot"></span>
  <span class="status-text" id="statusText">Live</span>
</div>
```

```css
.status-dot .dot {
  width: 6px; height: 6px; border-radius: 50%;
  display: inline-block;
}
.status-dot .dot.online {
  background: var(--accent);
  animation: statusPulse 2s ease infinite;
}
.status-dot .dot.offline {
  background: var(--accent-red);
  animation: none;
}
@keyframes statusPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(0,255,136,0.4); }
  50% { box-shadow: 0 0 0 8px rgba(0,255,136,0); }
}
```

### 12. Gradient Text Animation (lobehub)

Animated multi-color gradient on headings using `background-clip: text`.

```css
.gradient-text {
  background: linear-gradient(135deg, var(--accent), var(--accent-dim),
              var(--accent-purple), var(--accent));
  background-size: 300% 300%;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  animation: gradientShift 6s ease infinite;
}
@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
```

## Easing Curve Reference

| Curve Name | cubic-bezier | Best For |
|---|---|---|
| **Spring** | `(0.34, 1.56, 0.64, 1)` | Scale-in, buttons, playful entries |
| **Custom Ease-Out** | `(0.16, 1, 0.3, 1)` | Card reveals, toast slides, content entrances |
| **Smooth** | `(0.4, 0, 0.2, 1)` | Hover transitions, color changes, standard interactions |
| **Standard Ease-Out** | `(0.16, 1, 0.3, 1)` | (alias — same as custom above) |

Place as CSS variables:
```css
:root {
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-smooth: cubic-bezier(0.4, 0, 0.2, 1);
}
```

## Integration Checklist

When adding animations to an existing dashboard, run through these in order:

1. [ ] **CSS custom properties** for easing curves and timing (3 variables above)
2. [ ] **Background** — subtle grid + orb glow + optional particle canvas
3. [ ] **Skeleton loaders** for every data-driven section (shown on mount, removed on data)
4. [ ] **Staggered entries** for lists (leaderboard, picks, cards)
5. [ ] **Micro-interactions** on cards, buttons, avatars (hover scale, left-bar, border glow)
6. [ ] **Animated numbers** for financial values (bankroll, target, stats)
7. [ ] **Toast notifications** for user actions (generate picks, place bet)
8. [ ] **Live status indicator** (green/red dot connected to API health endpoint)
9. [ ] **Scroll reveal** for below-fold sections
10. [ ] **Responsive** — hide particle canvas and heavy animations on mobile/low-end devices via `prefers-reduced-motion`

## Common Pitfalls

- **scale transform on hover causing layout shift:** Always use `transform: scale()` instead of changing `width`/`height`. Scale doesn't trigger layout.
- **Double rAF for staggered entry:** Without it, the initial `opacity: 0` and the target `opacity: 1` paint in the same frame — no animation.
- **Canvas memory on resize:** Debounce resize handler or use requestAnimationFrame coalescing. Too many resize callbacks create canvas flicker.
- **Skeleton vs content flash:** Show skeletons in the container initially. When data arrives, replace `innerHTML`. The skeleton opacity animation stops naturally.
- **`prefers-reduced-motion`:** Wrap heavy animations (particles, confetti, gradient-shift) in `@media (prefers-reduced-motion: no-preference)`.
- **Button `:active` and `:hover` conflicts:** On mobile, `:hover` sticks after tap. Use `@media (hover: hover)` for hover-only effects.
