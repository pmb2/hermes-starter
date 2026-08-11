# Webull Deep Links for Signal Calls

Webull has predictable URL patterns for quote pages and options chains. These can be used to make ticker symbols and contract specs clickable in Discord report output.

## URL Patterns

```
Quote page:   https://www.webull.com/quote/{exchange}-{ticker}
Options chain: https://www.webull.com/quote/{exchange}-{ticker}/options
WebTrade:      https://app.webull.com/
```

## Exchange Prefix Mapping

| Exchange | Prefix | Examples |
|----------|--------|---------|
| NASDAQ | `nasdaq-` | NVDA, AAPL, MSFT, TSLA, AMD, SMCI, PLTR, SOFI, RKLB, ASTS, META, GOOGL, AMZN, NFLX, PYPL, COIN, MSTR, TSM, HOOD |
| NYSE | `nyse-` | JPM, GS, BA, DIS, GME, AMC, NET, SNAP, UBER, SQ, RDDT |
| NYSE Arca | `nysearca-` | SPY, IWM, DIA, XLF, XLK, XLE, XLV, TLT, HYG, LQD, GDX, ARKK, VTI, VOO, GLD, SLV, USO, FNGU |

Default fallback for unknown tickers: `nasdaq-`

## Discord Markdown Format

```markdown
[$NVDA](https://www.webull.com/quote/nasdaq-nvda)
[$122C 8/14](https://www.webull.com/quote/nasdaq-nvda/options)
[Open WebTrade](https://app.webull.com/)
```

## Implementation

```python
# Static exchange map keyed by uppercase ticker symbol
_WEBULL_EXCHANGE_MAP: dict[str, str] = {
    "SPY": "nysearca",
    "QQQ": "nasdaq",
    "NVDA": "nasdaq",
    "JPM": "nyse",
    # ... 80+ entries covering common stocks and ETFs
}

def webull_quote_url(ticker: str) -> str:
    ticker_clean = ticker.upper().replace("$", "")
    exchange = _WEBULL_EXCHANGE_MAP.get(ticker_clean, "nasdaq")
    return f"https://www.webull.com/quote/{exchange}-{ticker_clean.lower()}"

def webull_options_url(ticker: str) -> str:
    return f"{webull_quote_url(ticker)}/options"
```

## Verification

Test URLs by checking HTTP status code:

```python
import requests
r = requests.get("https://www.webull.com/quote/nasdaq-nvda",
                 headers={"User-Agent": "Mozilla/5.0"})
assert r.status_code == 200
```

All 80+ mapped tickers verified live. QQQ uses `nasdaq-qqq` (not `nysearca-qqq`).