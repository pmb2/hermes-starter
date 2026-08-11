# Recommendation Engine Architecture

Phase 6 of stock-sniffer. Three new modules that close the signal → trade → P&L loop.

## Flow

```
Signal + RiskCard → recommendation.py → TradeRecommendation
                                        ↓
                                   rec_ledger.py (saved to SQLite)
                                        ↓
                                   live_tracker.py (mark-to-market, triggers)
```

## recommendation.py

`generate_recommendation(signal, risk_card)` → `TradeRecommendation` with:

### Entry Zone (3 levels)
- Bottom: bounce/pullback entry (0.5% below spot for bullish)
- Center: current price zone
- Top: breakout confirmation (1% above spot for bullish)
- Each level has: price, label, trigger condition, notes
- Bearish reverses the levels

### Stop Loss
- 2-2.5% from entry, adjusted by score confidence
- Higher score = tighter stop (more conviction)
- Includes trigger condition (close above/below)

### Profit Targets
- T1: 3-5% from entry (50% position) — score-scaled
- T2: 6-9% from entry (remaining 50%) — score-scaled

### Options Contract
- Direction: `long_call` (bullish) or `long_put` (bearish)
- Strike: from chain data (ATM, OTM-N%) or fallback 2% OTM
- Expiry: nearest Friday ≥ DTE target
- DTE target: 7 (swing), 5 (weekly), 14 (monthly), 2 (0dte_watch)
- Estimated premium: chain mid or 2.5% of spot

### Exit Signals
- T1 partial exit rule
- Stop loss rule
- Time-based exit (50% of max profit)
- Source-specific invalidation

### Quality Assessment
- `high`: score ≥ 70, 2+ sources, no risk flags
- `medium`: score ≥ 55
- `low`: score < 55
- `research_only`: bankroll/risk incomplete

## rec_ledger.py

SQLite schema: `recommendations` table with full lifecycle.

### Columns
- `rec_id`: `YYYYMMDD-HHMMSS-TICKER` (primary key)
- Full contract details (direction, strike, strike_sel, expiry, dte, premium, cost)
- Full levels as JSON (entry_zone, stop_loss, profit_targets, exit_signals, invalidation)
- `acted_on`: 0 → 1 when user acts
- `fill_price`, `fill_contracts`, `fill_cost_usd`, `filled_at`: set on act
- `close_price`, `close_reason`, `closed_at`, `realized_pnl_usd`: set on close
- `signal_quality`, `dte_band`, `confidence_notes_json`

### Close reasons
- `win_t1`: first profit target hit
- `win_t2`: second profit target hit
- `stop_loss`: stopped out
- `expired`: DTE exhausted
- `manual`: user closed manually
- `ignored`: rec was ignored (acts as 0 P&L marker)

### Aggregate stats via `ledger_summary()`
- Total recs, acted, ignored, open
- Wins / losses / expired counts
- Total realized P&L
- Win rate %
- By ticker breakdown
- By quality distribution

## live_tracker.py

`fetch_live_status()`:
1. Reads open recs from ledger (`acted_on=1 AND close_reason IS NULL`)
2. Fetches live quotes via yfinance per ticker
3. Parses JSON stop_loss / profit_targets from ledger
4. Computes unrealized P&L per position
5. Checks trigger conditions:
   - Stop hit: current price ≤ stop (calls) or ≥ stop (puts)
   - T1 hit: current price ≥ T1 (calls) or ≤ T1 (puts)
   - T2 hit: current price ≥ T2 (calls) or ≤ T2 (puts)
6. Returns `LiveUpdate` with positions, triggered_stops, triggered_targets

`auto_close_stops=True` calls `mark_closed()` on triggered positions.

## Pipeline integration

In `run_scan()`:
```python
if rec_cfg.get("enabled", True) and signals and risk_cards:
    recs = generate_recommendations(signals, risk_cards)
    save_recommendations(recs)
    rec_block = join format_recommendation_discord for top 5
```

All modes (morning/intraday/evening) generate recs. Live tracker runs only on evening mode. Ledger summary included when `show_ledger: true` in config.

## Config (`sources.yaml`)

```yaml
recommendations:
  enabled: true
  max_recommendations: 10
  max_display: 5
  show_ledger: true

live_tracker:
  enabled: true
  auto_close_stops: false
```
