# trading-signals MCP — MACD signal-line unit mismatch (Bug 4, Aug 4 2026)

Server: `${MY_REPOS}\Documents\github\_project\mcp\trading-signals-mcp.py`
Runtime: durable venv `${USER_HOME}\AppData\Local\hermes\venvs\openbb-trading`
(openbb 4.6.0 + openbb-core 1.6.13 + mcp 1.28.1 + pydantic 2.13.4).
Committed `9113836` (19 insertions, 7 deletions). Companion to
`references/trading-signals-data-shape-fixes.md` (Bugs 1-3).

## Symptom
`technical_signals` always printed `MACD_BEARISH`; `MACD_BULLISH` never fired in any
pulse since the server went live. Flagged Aug 3 as "latent MACD bug" when the signal
line read 744.9 while macd read −1.81 — two numbers from different universes.

## Root cause
```python
# BEFORE (bug):
ema12 = sum(closes[-12:]) / 12      # simple averages, not EMAs
ema26 = sum(closes[-26:]) / 26
signals["macd"] = round(ema12 - ema26, 2)   # ~2-3 units (indicator scale)
signal_line = sum(closes[-9:]) / 9          # SMA of last 9 CLOSES ≈ $770 (price scale)
# macd > signal_line → always False → MACD_BULLISH unreachable
```
Two independent bugs in one block:
1. **Unit mismatch**: signal line was SMA of closes (price units) compared against the
   MACD value (indicator units). The comparison `macd > signal_line` can never be true.
2. `ema12`/`ema26` were simple averages of the trailing window, not true EMAs.

## Fix (standard MACD(12,26,9))
```python
k12, k26 = 2 / 13, 2 / 27
ema12 = ema26 = closes[0]
macd_series = []
for px in closes:
    ema12 = px * k12 + ema12 * (1 - k12)
    ema26 = px * k26 + ema26 * (1 - k26)
    macd_series.append(ema12 - ema26)
macd = macd_series[-1]
k9 = 2 / 10
signal_line = macd_series[0]
for m in macd_series:
    signal_line = m * k9 + signal_line * (1 - k9)
# then: macd_histogram = macd - signal_line; BULLISH if macd > signal_line
```

## Live verification (Aug 4, pre-close)
SPY: price 771.33, **macd 2.56, signal 0.56, hist 2.0 → `MACD_BULLISH` fires for the
first time ever** (RSI 59.7, ABOVE_SMA20, 84 pts).

## General lesson
A one-sided indicator comparison (`X` is never > `Y`) almost always means **unit
mismatch** — indicator scale (MACD ~2-3 units, RSI 0-100) vs price scale (~$770).
Never trust a signal branch that has never fired; check the scales of both operands.

## Branch-coverage verification via mocked data source
Live market data can't force a specific branch (a bull day proves nothing about
BEARISH). To prove BOTH branches reachable, monkeypatch the data source with synthetic
series and call the tool function in-process (module loaded via
`importlib.util.spec_from_file_location` — hyphenated filename can't be `import`ed):
```python
class FakeResult:
    def __init__(self, closes): self._closes = closes
    def to_dict(self): return {"close": self._closes}
class FakeHist:
    def __init__(self, closes): self._closes = closes
    def historical(self, *a, **k): return FakeResult(self._closes)
class FakeObb:
    def __init__(self, closes): self.equity = type("E", (), {"price": FakeHist(closes)})()
m.get_obb = lambda: FakeObb(closes)
out = json.loads(m.technical_signals("SYNTH"))
```
- rising `[100 + i * 0.5 for i in range(80)]` → assert `MACD_BULLISH`
- falling `[200 - i * 0.5 for i in range(80)]` → assert `MACD_BEARISH`
- unit check: `abs(macd) < 50 and abs(signal) < 50 and abs(hist) < 50` — price-scale
  values (~hundreds) fail this instantly
- **Trap**: a "flat/chop" series like `[100 + (i % 10)]` averages UPWARD → correctly
  yields BULLISH. Don't assert BEARISH on it; use a true mean-reverting series if you
  need a flat case.

## Deployment note
The running MCP subprocess holds the old module in memory — the fix only goes live on
the next Hermes restart (trading-signals also self-heals venv-level deps per call, but
NOT module code). Verify against a fresh import of the on-disk file; live tool calls
keep showing old behavior until the process restarts. After config rewiring, watch for
duplicate server PIDs (stale subprocess on the old python surviving alongside the new).
