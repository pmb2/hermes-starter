# Tab Reuse Implementation (June 2026)

Committed as `feat(browser): tab reuse to prevent tab proliferation` on branch `feature/tab-reuse`.

## Files Modified

### tools/browser_tool.py

**New function: `_get_tab_reuse_enabled()`**
Reads `browser.tab_reuse` from config.yaml (default: True). When disabled, all navigations use `agent-browser open` (legacy behavior).

**New function: `_try_navigate_same_tab(task_id, url)`**
Returns a dict shaped like `_run_browser_command` output. Three strategies:

1. **CDP supervisor navigate** -- `SUPERVISOR_REGISTRY.get(task_id)` -> `supervisor.navigate(url, timeout=15.0)`. If the supervisor is active and navigate returns ok, returns `{"success": True, "data": {"url": ..., "title": "", "_via": "cdp_navigate"}}`.

2. **agent-browser eval** -- `_run_browser_command(task_id, "eval", [f"window.location.href = '{escaped_url}'"], timeout=15)`. URL is escaped: `url.replace("\\", "\\\\").replace("'", "\\'")`. Returns `{"success": True, "data": {"url": ..., "title": "", "_via": "eval_navigate"}}`.

3. **agent-browser open** -- Falls back to `_run_browser_command(task_id, "open", [url], timeout=...)` which creates a new tab.

**Modified: `browser_navigate()`**
Before: always called `_run_browser_command(nav_session_key, "open", [url], ...)`
After:
```python
if is_first_nav or not _get_tab_reuse_enabled():
    result = _run_browser_command(nav_session_key, "open", [url], ...)
else:
    result = _try_navigate_same_tab(nav_session_key, url)
```
The `_first_nav` flag uses `session_info.get("_first_nav", True)` and is set to `False` after the first navigation.

**New function: `_cleanup_extra_tabs()`**
Runs on the cleanup loop every 30 seconds. For each active session with a running CDP supervisor:
1. Calls `supervisor.get_open_tabs()` to list all page targets
2. Compares against `supervisor._page_target_id` (the current tab)
3. Calls `supervisor.close_tab(tab["targetId"], timeout=3.0)` for extra tabs
4. Logs count at INFO level: "Tab GC: closed N surplus tabs for task=X (kept current)"

**Modified: `_browser_cleanup_thread_worker()`**
Added `_cleanup_extra_tabs()` call after `_cleanup_inactive_browser_sessions()`.

### tools/browser_supervisor.py

**New field: `_page_target_id`**
Set during `_attach_initial_page()` from the selected page target's targetId. Used by the tab GC to identify the current tab.

**New method: `navigate(url, timeout=15.0)`**
Sync bridge -> async `_cdp("Page.navigate", {"url": url}, session_id=self._page_session_id, timeout=timeout)`. Returns `{"ok": True, "frame_id": ..., "url": ..., "loader_id": ...}` or `{"ok": False, "error": ...}`.

**New method: `close_current_tab(timeout=5.0)`**
Sync bridge -> async `_cdp("Target.closeTarget", {"targetId": self._page_target_id}, timeout=timeout)`. Returns `{"ok": True}` or error. After closing, the supervisor has no page session until it reconnects.

**New method: `close_tab(target_id, timeout=5.0)`**
Same as close_current_tab but accepts an explicit target_id. Used by tab GC to close non-current tabs.

**New method: `get_open_tabs()`**
Sync bridge -> async `_cdp("Target.getTargets", timeout=5.0)`. Filters for type=="page". Returns `{"ok": True, "tabs": [{"targetId": ..., "url": ..., "title": ...}, ...]}`.

### hermes_cli/config.py

Added to DEFAULT_CONFIG["browser"]:
```python
"tab_reuse": True,  # When True, navigations reuse existing tabs instead of opening new ones
```

## Usage

Enable/disable:
```bash
hermes config set browser.tab_reuse true   # default - reuse tabs
hermes config set browser.tab_reuse false  # legacy - new tab per nav
```

Requires `/reset` or restart to take effect.

## Implementation Notes

- The CDP supervisor's `navigate()` uses `Page.navigate` which triggers the same lifecycle as a normal page navigation (load, DOMContentLoaded, etc.). The `browser_navigate` response's auto-snapshot captures the resulting page state as before.
- The eval strategy (`window.location.href = ...`) works for same-origin navigations and most cross-origin ones, but may fail on pages with restrictive Content Security Policies. In that case it falls through to `open`.
- Tab GC only works for sessions with active CDP supervisors (cloud/CDP mode). Local headless sessions without CDP are cleaned up by the inactivity timeout.
- All new methods on CDPSupervisor use the `safe_schedule_threadsafe` pattern to bridge from the caller's thread to the supervisor's asyncio loop, matching `evaluate_runtime()`.
