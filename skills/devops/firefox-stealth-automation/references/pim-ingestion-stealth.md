# PIM Ingestion Stealth Integration (Two-Phase)

## Architecture

```
Phase 1: StealthEngine.apply(browser) → 22 script.addPreloadScript → disconnect
Phase 2: PIM connector → new BiDi session → preload scripts still active → navigate
```

## Step-by-Step

1. Start patched portable Firefox on port 9239 with **automation profile** (`firefox-profile`)
2. Connect via `_firefox_bidi.py` → `_try_bidi_connect()` → creates BiDi session
3. `_apply_stealth()` called immediately after session creation, BEFORE `_create_context()`:
   ```python
   await self._apply_stealth()  # 22 measures via StealthEngine
   await self._create_context() # tab creation
   ```
4. `_apply_stealth()` imports `StealthEngine` from `ultimate_firefox_mcp.stealth`, calls `get_preload_script()` for combined 32KB JS
5. Registers via `script.addPreloadScript` → runs on ALL future page loads
6. Session continues during extraction → navigates to ChatGPT/Grok
7. PyAutoGUI is NOT needed — extraction uses only BiDi WebSocket commands

## Critical Dependency

`ultimate_firefox_mcp` must be `pip install -e .`-ed for the import to work:

```bash
cd ${USER_HOME}\ultimate-firefox-mcp
pip install -e .
```

Without this, `from ultimate_firefox_mcp.stealth import StealthEngine` silently fails (caught ImportError, falls back to zero stealth).

## Belt-and-Suspenders

Both `_apply_stealth()` and `_apply_cdp_stealth()` include a `sys.path.insert(0, ...)` fallback:

```python
sys.path.insert(0, r'${USER_HOME}\ultimate-firefox-mcp')
from ultimate_firefox_mcp.stealth import StealthEngine
```

This ensures stealth works even if `pip install -e` was skipped during development.

## Verification

```python
# In the BiDi session, after navigation:
result = await ff.evaluate("typeof navigator.webdriver")
# -> "undefined" (patched xul.dll)
```
