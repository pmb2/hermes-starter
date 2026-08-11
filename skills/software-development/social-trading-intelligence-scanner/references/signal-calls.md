# Signal Calls — the operator's Clean Format

## Design principle
the operator wants one-liner trade signals he can act on in seconds. No paragraphs. No ambiguity.
Every call must answer: WHAT to buy, AT WHAT price, with WHAT stop, to WHAT targets.
All tickers and contract specs must be **clickable Webull links** for one-click execution.

## Tier system

| Tier | Icon | Criteria |
|------|------|----------|
| STRONG BUY | 🔥 | Score ≥ 80 AND ≥ 3 sources |
| BUY | 📈 | Score ≥ 70 AND ≥ 2 sources |
| BUY WEAK | 🔍 | Score ≥ 60 AND ≥ 2 sources |
| WATCH | 👀 | Score ≥ 50, any sources |
| SKIP | ⛔ | Research only, incomplete data, score < 50 |

## One-liner format (with Webull links)

```
🔥 STRONG BUY  [$NVDA](https://www.webull.com/quote/nasdaq-nvda)  [$122C 8/14](https://www.webull.com/quote/nasdaq-nvda/options)  @$3.00  @$120.00 bounce
  Stop: $117.53  T1:$124.20 T2:$128.40  3 sources · score 82 ✅
```

### Line 1: [tier] [ticker_link] [contract_link] [@premium] [@entry_trigger]
- Ticker link: `[$NVDA](https://www.webull.com/quote/nasdaq-nvda)` — opens quote page
- Contract link: `[$122C 8/14](https://www.webull.com/quote/nasdaq-nvda/options)` — opens options chain
- Entry trigger: extracted from entry zone center level with trigger condition

### Line 2: Stop: [price]  T1:[price] T2:[price]  [conviction] [quality_flag]

## Suggested Moves — pre-market briefing (8:30 AM)

The `format_suggested_moves()` function is the SOLE morning format (8:30 AM pre-bell).
Replaces old `format_premarket_briefing()` as the pipeline's morning mode output.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
☀️ SUGGESTED MOVES — AUGUST 11, 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔥 STRONG BUYS
  [$NVDA](https://www.webull.com/quote/nasdaq-nvda) [$122C 8/14](https://www.webull.com/quote/nasdaq-nvda/options) — @$120.00 bounce
  → Enter: $117.53 | Targets: T1:$124.20 T2:$128.40
  → 3 sources · score 82 ✅

📈 BUYS
  [$SPY](https://www.webull.com/quote/nysearca-spy) [$595C 8/16](https://www.webull.com/quote/nysearca-spy/options) — @$592.50 break above
  → Enter: $588.00 | Targets: T1:$605.00 T2:$612.00
  → 2 sources · score 72 ✅

📋 ENTRY CHECKLIST
1. [$NVDA](https://www.webull.com/quote/nasdaq-nvda) — @$120.00 bounce
2. [$SPY](https://www.webull.com/quote/nysearca-spy) — @$592.50 break above

⚠️ RISK
  Max 15% of bankroll per position · 6% per cluster
  Check earnings calendar before entry

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 [Open WebTrade](https://app.webull.com/) — ready to trade
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Sections: 🔥 STRONG BUYS → 📈 BUYS → 🔍 BUY WEAK (Sizing) → 👀 WATCH LIST,
each with clickable Webull links, entry trigger, stop, targets, conviction.
CLI: `python -m stocksniffer.cli moves --mode morning` (added `cmd_moves`).

## Weblink builders

```python
webull_quote_url("NVDA")   # → https://www.webull.com/quote/nasdaq-nvda
webull_options_url("NVDA") # → https://www.webull.com/quote/nasdaq-nvda/options
```

Exchange map: 80+ tickers, `nasdaq` default. See `references/webull-deep-links.md` for the full map.

## Trigger alert format

Each trigger type has a specific header and content:

```
🛑 STOP LOSS HIT
**$TSLA** — PUT
Entry: $265.00 · Now: $275.00
Stop loss: $273.00 · Loss: -$1,000
ID: `20260810-143000-TSLA`

🎯 T1 HIT — SELL 50%
**$NVDA** — CALL
Entry: $3.00 · Now: $4.50
T1: $124.20 · Gain: +$450
🟢 SELL 50%, move stop to breakeven
ID: `20260810-120000-NVDA`
```

## Key functions

```python
from stocksniffer.signal_calls import (
    resolve_tier,              # (rec) → (icon, label)
    build_signal_call,         # (rec) → SignalCall
    format_signal_call,        # (SignalCall) → str (one-liner, Webull-linked)
    format_all_calls,          # (recs) → str (grouped by tier)
    format_suggested_moves,    # (recs) → str (morning briefing, Webull-linked)
    format_premarket_briefing, # (recs) → str (legacy morning format)
    format_trigger_alert,      # (rec_id, trigger_type, details) → str
    generate_calls_from_scan,  # (signals, cards, max_calls) → (recs, calls)
    webull_quote_url,          # (ticker) → Webull quote page URL
    webull_options_url,        # (ticker) → Webull options chain URL
)
```