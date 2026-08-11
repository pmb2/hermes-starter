# Trigger Watch — Intraday Cron Setup

## Hermes cron job

```bash
hermes cron create \
  --name "Stock Sniffer: Intraday Trigger Watch" \
  --schedule "*/15 9-16 * * 1-5" \
  --script trigger_watch.sh \
  --no-agent \
  --deliver origin \
  --skills social-trading-intelligence-scanner
```

## Shell script (`~/.hermes/scripts/trigger_watch.sh`)

```bash
#!/bin/bash
set -e
cd ${USER_HOME}/Documents/github/stock-sniffer
python -m stocksniffer.cli trigger-watch 2>&1 || echo "[SILENT]"
```

## How it works

1. Cron fires every 15 minutes during market hours (9:00 AM–4:00 PM ET, Mon–Fri)
2. Script runs `stock-sniffer trigger-watch`
3. Trigger watch checks:
   - **Stop loss triggers**: any open position where price crossed stop level
   - **Profit target triggers**: T1 (sell 50%) or T2 (sell remaining) hit
   - **Gap alerts**: significant pre-market/intraday gaps on watchlist
   - **Econ events**: high-importance events within 2 days
4. If ANY triggers fire → formatted alert blocks printed to stdout → delivered to Discord
5. If NOTHING fires → prints `[SILENT]` → no delivery (suppresses notification spam)

## Silent-by-default design

The `no_agent=true` mode means:
- Non-empty stdout → sent verbatim to delivery target
- Empty stdout → SILENT, nothing delivered
- The trigger watch script prints `[SILENT]` when no triggers → no message

This is the same pattern as watchdog scripts — silent when healthy, noisy when action needed.

## Watchlist

Config in `configs/sources.yaml` under `trigger_watch.watchlist`:
```yaml
trigger_watch:
  enabled: true
  auto_close_stops: false
  check_gaps: true
  check_econ: true
  watchlist: [NVDA, TSLA, SPY, QQQ, AAPL, MSFT, META, AMZN, GOOGL, AMD, SMCI, PLTR, SOFI, RKLB, ASTS]
```

## What users see in Discord

```
🔔 TRIGGER ALERTS — 14:30 UTC
🛑 STOP LOSS HIT
**$TSLA** — PUT
Entry: $265.00 · Now: $275.00
Stop loss: $273.00 · Loss: -$1,000
---
🎯 T1 HIT — SELL 50%
**$NVDA** — CALL
Entry: $3.00 · Now: $4.50
T1: $124.20 · Gain: +$450
🟢 SELL 50%, move stop to breakeven
---
━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Manual trigger

```bash
stock-sniffer trigger-watch     # run once, see all triggers
stock-sniffer live              # positions only, no econ/gaps
stock-sniffer live --auto-close # mark-to-market + auto-close stops
```

## Cron cooldown

The 15-minute interval means:
- If a stop gets hit at 10:02, you'll see it by 10:15
- If T1 gets hit at 10:12, you'll see it by 10:15
- No duplicate alerts — each trigger fires once per check cycle
- `[SILENT]` most of the time — only fires when something needs action
