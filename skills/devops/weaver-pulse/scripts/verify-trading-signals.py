#!/usr/bin/env python3
"""
verify-trading-signals — ad-hoc behavior verification for trading-signals-mcp.py
fixes (provider, column-oriented to_dict, pre-market price fallback — commit 890da31).

Usage:
  env -u PYTHONPATH "${USER_HOME}/AppData/Local/hermes/venvs/openbb-trading/Scripts/python.exe" \
      verify-trading-signals.py [path/to/trading-signals-mcp.py]

Asserts:
  1. Module py_compiles clean.
  2. market_summary: all 5 indices have price > 0 and change != -100.0
     (the exact regression from bid/ask = 0.0 pre-market).
  3. technical_signals(SPY) and (QQQ): success, >= 20 data points, price + rsi present,
     no "Unexpected data format: dict" error.

Exits 0 on pass, 1 on failure. NOT a suite run — focused behavior check.
"""
import json
import importlib.util
import py_compile
import sys

TARGET = sys.argv[1] if len(sys.argv) > 1 else r"${MY_REPOS}/Documents/github/_project/mcp/trading-signals-mcp.py"
failures = []

try:
    py_compile.compile(TARGET, doraise=True)
    print("[PASS] py_compile clean")
except py_compile.PyCompileError as e:
    failures.append(f"py_compile: {e}")
    print(f"[FAIL] py_compile: {e}")
    sys.exit(1)

spec = importlib.util.spec_from_file_location("tsm_verify", TARGET)  # hyphenated name: can't `import`
tsm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tsm)

try:
    ms = json.loads(tsm.market_summary())
    assert ms.get("success") is True, f"success flag: {ms.get('success')}"
    for name, q in ms["market"].items():
        p, c = q["price"], q["change"]
        ok = isinstance(p, (int, float)) and p > 0 and isinstance(c, (int, float)) and c != -100.0
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: price={p} change={c}")
        if not ok:
            failures.append(f"market_summary {name}: price={p!r} change={c!r}")
except Exception as e:
    failures.append(f"market_summary raised: {type(e).__name__}: {e}")
    print(f"[FAIL] market_summary raised: {e}")

for sym in ("SPY", "QQQ"):
    try:
        out = json.loads(tsm.technical_signals(sym))
        err = out.get("error")
        if err:
            failures.append(f"technical_signals({sym}) error: {err}")
            print(f"[FAIL] technical_signals({sym}): {err}")
            continue
        n = out.get("data_points", 0)
        ok = out.get("success") is True and n >= 20 and "price" in out and "rsi_14" in out
        print(f"[{'PASS' if ok else 'FAIL'}] technical_signals({sym}): {n} pts, price={out.get('price')}, rsi={out.get('rsi_14')}")
        if not ok:
            failures.append(f"technical_signals({sym}) incomplete: {out}")
    except Exception as e:
        failures.append(f"technical_signals({sym}) raised: {type(e).__name__}: {e}")
        print(f"[FAIL] technical_signals({sym}) raised: {e}")

print()
if failures:
    print(f"VERIFICATION FAILED — {len(failures)} issue(s):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("VERIFICATION PASSED — all changed behaviors confirmed (ad-hoc, not a suite run)")
