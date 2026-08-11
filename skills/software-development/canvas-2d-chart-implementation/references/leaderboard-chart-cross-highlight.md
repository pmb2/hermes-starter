# Leaderboard ↔ Chart Cross-Highlight with Color Matching

## Problem

A leaderboard (DOM element list) and a Canvas 2D chart show the same
players. Hovering a leaderboard entry should:
1. Cross-highlight the player's trajectory on the chart
2. Style the leaderboard entry's border + background + left accent bar
   to match the player's *actual* chart line color

## Architecture

```
Chart.setHoveredPlayer(player)
  │
  ├── Stores the hovered player reference
  ├── Highlights the trajectory path on canvas
  └── Fires onHoverChange callback

Leaderboard entry (DOM)
  │
  ├── mouseenter → chart.setHoveredPlayer(player)
  │                + inline styles (borderColor, background, boxShadow)
  │                + CSS variable (--lb-color) for ::before
  ├── mouseleave → chart.setHoveredPlayer(null)
  │                + clear inline styles
  │                + remove CSS variable
  └── click → showPlayerModal(name, rank, chart player color)
```

## Getting the Right Color

The leaderboard entry's `entry.color` is often empty because the
leaderboard API doesn't carry chart colors. **Always look up the
color from the chart data, not the leaderboard entry:**

```javascript
// ❌ Wrong — uses default colors, not per-player chart colors
const playerColor = entry.color || (isAI ? '#7c3aed' : '#00ff88');

// ✅ Correct — looks up actual chart player color
const chart = window.crashChart;  // or window._chartFullData
const chartPlayer = chart?.players?.find(p => p.name === entry.name);
const actualColor = chartPlayer?.color || '#00ff88';
```

## Setting Inline Styles on Hover

```javascript
div.addEventListener('mouseenter', () => {
  const chart = window.crashChart;
  if (!chart?.players) return;
  const player = chart.players.find(p => p.name === name);
  if (player) {
    chart.setHoveredPlayer(player);
    const c = player.color || '#00ff88';
    div.style.borderColor = c;
    div.style.background = c + '18';        // ~10% opacity via hex
    div.style.boxShadow = `0 0 20px ${c}25`; // ~15% opacity glow
    div.style.setProperty('--lb-color', c); // for ::before pseudo-element
  }
});

div.addEventListener('mouseleave', () => {
  const chart = window.crashChart;
  if (chart) chart.setHoveredPlayer(null);
  div.style.borderColor = '';
  div.style.background = '';
  div.style.boxShadow = '';
  div.style.removeProperty('--lb-color');
});
```

## CSS Custom Property for ::before Pseudo-Element

The left accent bar (`::before`) can't receive inline styles directly.
Use a CSS variable on the element itself:

```css
.leaderboard-entry::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: var(--lb-color, var(--accent));
  opacity: 0;
  transition: opacity 0.2s;
}

.leaderboard-entry:hover::before {
  opacity: 1;
}
```

- `var(--lb-color, var(--accent))` — uses the player's color when set
  (via `setProperty` on mouseenter), falls back to the default accent
  color when cleared.
- `opacity` is animated (not `background`), because CSS variable changes
  don't trigger CSS transitions automatically.

## Click → Player Modal

The same color lookup pattern applies when opening a player detail
modal:

```javascript
div.addEventListener('click', () => {
  const chart = window.crashChart;
  const chartPlayer = chart?.players?.find(p => p.name === name);
  const actualColor = chartPlayer?.color || '#00ff88';
  showPlayerModal(name, rank, { color: actualColor, ... });
});
```

## Pitfalls

- **`:hover` CSS vs inline style conflicts.** Both are active on hover.
  Inline styles (`div.style.borderColor = c`) always win over stylesheet
  rules, so they correctly override the CSS `:hover` block.
- **Empty `entry.color`.** Most leaderboard APIs don't return chart
  colors. Always look up from `chart.players[]` or `_chartFullData`.
- **CSS transitions on CSS variables.** Changing `--lb-color` does NOT
  trigger a CSS transition on `background`. If you want the left bar
  to animate in, animate `opacity` or `width` instead — not the
  `background` property.
- **Inline `background` shorthand.** Setting `div.style.background`
  sets the full shorthand, which may override other background
  sub-properties. If the element uses a CSS gradient background that
  should be preserved, set `background-color` instead.
- **Pseudo-element `::before` `opacity` reset.** When the CSS variable
  is removed on mouseleave, `background` falls back to `var(--accent)`.
  Without the `opacity: 0` on mouseleave, the default green bar stays
  visible. Always ensure `::before` has `opacity: 0` by default and
  only shows on hover via `:hover::before { opacity: 1 }` — this way
  every player gets their correct color when hovered, and nothing shows
  by default.
