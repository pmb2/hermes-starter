# Ticker extraction noise control

Learned from live stock-sniffer morning smokes (2026-08-08).

## Failure mode

Feeding full YouTube transcripts into standalone ALLCAPS extraction produces junk signals:

`DAY`, `RED`, `OF`, `COPY`, `YEARS`, `SMALL`, `WIN`, `PDF`, `NBA`, `IRA`, `USB`, `AMA`, `NYC`, `OTM`, `ITM`, `ATM`, `PDT`, `ACCT`, `DAS`, `DRAM`, …

These can score above threshold via recency/weight and dominate the Discord watchlist.

## Working policy

1. **Cashtags (`$NVDA`)** — always extract (minus blocklist)
2. **YouTube standalone** — title + description only, min length 3
3. **YouTube transcript** — cashtags only
4. **Reddit** — title + selftext; min length 2; large stop list still required
5. **Scoring gate** — single-source + single-mention needs `score >= max(min_signal_score+15, 55)`
6. **Multi-source** (reddit+youtube) is the quality signal you want to surface first

## YAML blocklist booleans

Unquoted YAML:

```yaml
- ON
- OFF
- YES
- NO
- OR
```

becomes Python bools and crashes `.upper()`.

Always quote those tokens, and in code:

```python
blocked = {
    str(b).upper()
    for b in (blocklist or [])
    if b is not None and not isinstance(b, bool)
}
blocked.update({"ON", "OFF", "YES", "NO", "TRUE", "FALSE"})
```

## Minimum stop-set categories

- English function words (`THE`, `AND`, `FOR`, `OF`, `TO`, …)
- Time/market prose (`DAY`, `WEEK`, `TODAY`, `EOD`, `AH`, `PM`)
- Options jargon not tickers (`OTM`, `ITM`, `ATM`, `DTE`, `IV`, `PDT`)
- Social/meta (`AMA`, `YOLO`, `FOMO`, `DD`, `COPY`, `SUBSCRIBE`)
- Geography/org noise (`USA`, `NYC`, `FOMC`, `SEC`) unless cashtagged
- Video title glue (`RED`, `GREEN`, …)

Keep real equities like `ZETA` out of the stop list unless chronic false positives without cashtags.

## Test ideas

- Noise string with no cashtags → empty or near-empty
- `$PLTR and $MRVL` → exact pair
- Challenge title without tickers → no invented tickers from `DAY`/`ACCOUNT`
