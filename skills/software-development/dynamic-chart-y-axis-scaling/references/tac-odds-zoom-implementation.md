# TAC Odds Crash Chart — Dynamic Zoom Implementation

## Context

The TAC Odds dashboard at `/tac-odds/crash-chart.js` (ES module, Canvas 2D) tracks bankrolls from $100→$10M on a log scale. Previously used a hardcoded `chartLogScale(bankroll, minLog=2, maxLog=7)` mapping everything to the full range.

## Change Summary

Replaced the static log scale with dynamic `yMaxLog` getter that zooms to ~1.5x the highest player's bankroll.

### Key changes in v4:

1. **Added `get yMaxLog()`** — computes tight ceiling based on max player bankroll
2. **Added `get maxBankroll()`** — considers current + historical maxes
3. **Added `getVisibleLevels()`** — generates grid lines only within the visible range
4. **Added `drawGoalIndicator()`** — draws $10M goal line when visible, floating badge when above viewport
5. **Added `formatYLabel()`** — formats axis labels with K/M suffixes
6. **Removed old `chartLogScale()` standalone function** — inlined into `toPlotY()`

### Ceiling calculation (1.5x headroom):

```
maxB * 1.5 → round up to next [1, 2, 5, 10] × 10^N
```

Examples:
- max=$125 → ceil=$200 (33% chart use vs 10% old)
- max=$1K → ceil=$2K (77% vs 59%)
- max=$50K → ceil=$100K (90% vs 82%)
- max=$5M → ceil=$10M (full range, normal)

### Files modified:
- `/tac-odds/crash-chart.js` — entire v4 rewrite (dynamic Y-axis, goal indicator, dynamic grid)
