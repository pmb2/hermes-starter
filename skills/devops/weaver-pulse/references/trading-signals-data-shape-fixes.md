# trading-signals MCP — data-shape fixes (Aug 2–3 2026)

Server: `${MY_REPOS}\Documents\github\_project\mcp\trading-signals-mcp.py`
Runtime: durable venv `${USER_HOME}\AppData\Local\hermes\venvs\openbb-trading` (openbb 4.6.0 + openbb-core 1.6.13 + mcp 1.28.1 + pydantic 2.13.4).
Three stacked bugs, each found when the previous fix was live-tested against real market data.

## Bug 1 (Aug 2): default provider hangs
`obb.equity.price.quote(sym)` with no `provider=` → OpenBB default provider routing hangs without API keys. Fix: `provider="yfinance"`.

## Bug 2 (Aug 2, market_summary): column-oriented `to_dict()`
openbb-core 1.6.13 `OBBject.to_dict()` returns **column-oriented** dicts — `{"bid": [744.11], "open": [744.68], ...}` (every value a list) — never row-dict lists. Consumers doing `for d in data if isinstance(d, dict)` silently get nothing, or error `Unexpected data format: dict` when they type-check against list.
Fix (market_summary): unwrap `{k: (v[0] if isinstance(v, list) and v else v) for k, v in data.items()}`.

## Bug 3 (Aug 3): bid/ask = 0.0 pre-market → 0.0/−100%
The Aug 2 fallback `data.get("price", data.get("bid", ...))` resolved to `bid=0.0` outside trading hours. yfinance quote `to_dict()` has **no `price`/`close`/`c` key at all**, and `bid`/`ask` are literally `0.0` pre-market/overnight. change% then computed `(0−prev)/prev = −100%`. QQQ looked fine only because yfinance had a populated bid.

Raw evidence (pre-market Aug 3, venv diagnostic dump):
```
[SPY] bid (list)=[0.0]  ask (list)=[0.0]  open (list)=[744.68]  prev_close (list)=[741.69]   ← no 'price' key
[QQQ] bid (list)=[688.49]                open (list)=[692.12]  prev_close (list)=[683.55]   ← why QQQ "worked"
[VXX] bid (list)=[0.0]  ask (list)=[21.09]  open (list)=[21.64]
HISTORICAL (SPY): {date, open, high, low, close, volume} — every key a list of 22
```
Durable fix (committed `890da31`):
```python
price = None
for k in ("last_price", "price", "open", "close", "c", "bid", "ask"):
    v = data.get(k)
    if isinstance(v, (int, float)) and v != 0:
        price = v
        break
# change% guard — never compute (0-prev)/prev:
if isinstance(price, (int, float)) and price and isinstance(prev, (int, float)) and prev:
    change = round((price - prev) / prev * 100, 2)
```

## Same-shape bug in technical_signals (Aug 3)
`historical().to_dict()` is also column-oriented. Fix: extract the column directly:
```python
elif isinstance(data, dict):
    col = data.get("close") or data.get("c") or []
    closes = [v for v in col if isinstance(v, (int, float))]
```
**Lesson:** after a data-shape fix in one tool, grep the whole file for other `to_dict()` consumers.

## Verification recipe
- In-process (no MCP transport): hyphenated filenames (`trading-signals-mcp.py`) cannot be `import`ed — load via `importlib.util.spec_from_file_location`, then call the tool functions directly.
- Always use the venv python with a clean env:
  `env -u PYTHONPATH "${USER_HOME}/AppData/Local/hermes/venvs/openbb-trading/Scripts/python.exe"` — the agent process PYTHONPATH carries Python-3.13 ABI packages that break 3.11 venv servers.
- Assertion script: `scripts/verify-trading-signals.py` (py_compile; all 5 indices price>0 and change≠−100.0; `technical_signals` ≥20 points, no dict-format error; exit 0 on pass). Ad-hoc variants: OS temp dir, `hermes-verify-` filename prefix, clean up after.
- FastMCP worker-thread hang (Aug 2 finding): NOT reproduced Aug 3 — live server returned results quickly (wrong values, no hang). Re-check after the next Hermes restart with the patched code.
