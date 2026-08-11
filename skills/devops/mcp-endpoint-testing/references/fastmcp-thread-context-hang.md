# FastMCP Thread-Context Hang — OpenBB trading-signals Case Study

Proven 2026-08-02 (Weaver pulse). Diagnostic pattern that generalizes to any stdio MCP
server whose tool bodies call heavy lazy-import libraries (OpenBB, pandas, numba).

## Symptom

- `initialize` OK, `list_tools` OK (all 4 tools registered).
- Tool call over stdio MCP (`call_tool("market-summary", {})`) either:
  - hangs indefinitely (server processed `CallToolRequest`, never responds), or
  - kills the server process mid-call → client raises `McpError: Connection closed`.
- The IDENTICAL tool function completes in 2–5 s when called directly in the main thread.
- A second tool using the same stack (`technical-signals`) hangs the same way → shared
  context problem, not per-tool logic.

## Isolation Ladder (what actually worked)

1. **In-process direct call** (main thread, no MCP):
   ```python
   import importlib.util
   spec = importlib.util.spec_from_file_location("ts", r"E:/.../trading-signals-mcp.py")
   m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
   print(m.market_summary()[:400])
   ```
   Result: real JSON with live prices in seconds → data layer proven fine → hang is in
   the FastMCP `anyio.to_thread` execution context.
2. **Client-side timeout discipline**: every MCP round-trip test run under
   `timeout 110` — a hang and a crash look identical through a 240 s wall-clock run
   unless you bound each call and read the partial output file.
3. **Check for orphaned server processes** after timeout kills (`wmic process where
   "name='python.exe'" get ProcessId,CommandLine | grep <server>`): orphaned stdio
   servers can hold cache locks that make the NEXT fresh server hang on startup.

## Two OpenBB SDK Quirks Found (independent of the thread hang)

### 1. Provider default routing hangs without API keys
`obb.equity.price.quote(sym)` with NO provider lets OpenBB auto-route through its
default provider list; with no API keys configured this hangs on auth/retry.
Fix: be explicit — `obb.equity.price.quote(sym, provider="yfinance")`.
Symptom at server level: tool call that used to "fail fast with N/A" now hangs once the
import chain is fixed and the call actually reaches OpenBB.

### 2. `OBBject.to_dict()` is COLUMN-oriented (openbb-core 1.6.13)
`q.to_dict()` on a quote result returns:
```python
{'symbol': ['SPY'], 'asset_type': ['ETF'], 'bid': [744.11], 'ask': [744.6],
 'open': [744.68], 'prev_close': [741.69], ...}   # values are LISTS, no 'price' key
```
NOT a row dict. Code written for row-shaped results (`data.get("price", data.get("close",
data.get("c", "N/A")))`) silently resolves every field to the fallback → "N/A" even when
the quote succeeded. There is no `price`/`close`/`change` key at all in yfinance quote
output; the usable keys are `bid`/`ask`/`prev_close` (change% must be computed:
`(bid - prev_close) / prev_close * 100`).
Fix (generic unwrap that tolerates both shapes):
```python
data = q.to_dict() if hasattr(q, "to_dict") else {}
if isinstance(data, dict):
    data = {k: (v[0] if isinstance(v, list) and v else v) for k, v in data.items()}
elif isinstance(data, list) and data:
    data = data[0]
price = data.get("price", data.get("bid", data.get("close", data.get("c", "N/A"))))
```
Lesson: probe the actual `to_dict()` shape of the SDK version in use before writing
extraction code; don't assume row orientation.

## Windows Clean-Env Pitfall (bit us mid-debug)

Testing with `env -i PATH=... HOME=...` broke the tool with a misleading
`"Could not determine home directory."` — Windows Python resolves home from
`USERPROFILE`, not `HOME`. And once `USERPROFILE` WAS passed, the same call hung
(OpenBB actually reaching its data fetch). Correct clean-env invocation:
```bash
env -i PATH="<venv>/Scripts:$PATH" USERPROFILE="$USERPROFILE" HOMEDRIVE="$HOMEDRIVE" \
  HOMEPATH="$HOMEPATH" APPDATA="$APPDATA" LOCALAPPDATA="$LOCALAPPDATA" SYSTEMROOT="$SYSTEMROOT" \
  <venv>/Scripts/python.exe ...
```

## Verified-Fix State (as of 2026-08-02)

- Data layer FIXED and verified (11/11 ad-hoc checks, main-thread): live quotes for
  SPY 744.11, QQQ 688.49, DIA 522.4, IWM 289.6, VXX 21.4 with computed change%.
- MCP-context hang REMAINS OPEN. Suspected: openbb-core extension auto-build not
  thread-safe under `anyio.to_thread` (crash vs hang varies run to run — classic
  race/deadlock signature).
- Next debug steps (untested): pre-warm OpenBB at module import in the main thread
  before `mcp.run()`; wrap tool bodies in a dedicated `threading.Thread` with join
  timeout; pin `fastmcp`/`mcp` to the `fastmcp>=0.4,<1.0` + `mcp>=1.0,<1.2` combo the
  native-mcp skill recommends; escalate to Forge with the repro if confirmed at the
  openbb-core level.
