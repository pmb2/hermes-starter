# Tab Lifecycle Investigation (June 2026)

## Problem

When Hermes Agent uses the `browser_*` tools, each `browser_navigate("url")` opens a new browser tab in the running Chromium instance. Over the course of a session — especially automated cron jobs or research tasks — hundreds of tabs accumulate in the Windows taskbar, spamming the desktop.

## Source Code Analysis

### File: `tools/browser_tool.py` (3891 lines)

**Session creation** (`_get_session_info`, line 1671):
- Checks `_active_sessions[task_id]` for an existing session
- If none: creates a local session (`_create_local_session`, line 1644) generating `session_name = f"h_{uuid.uuid4().hex[:10]}"`
- If cloud provider configured: calls `provider.create_session(task_id)` (line 1721)
- If CDP override: calls `_create_cdp_session(task_id, cdp_override)` (line 1712)

**Navigation** (`browser_navigate`, line 2309):
- Calls `_navigation_session_key(task_id, url)` to determine which session key to use (bare task_id or `{task_id}::local` for hybrid routing)
- Calls `_get_session_info(nav_session_key)` to get/create session
- Calls `_run_browser_command(nav_session_key, "open", [url], ...)` (line 2410) — **this opens a new tab**

**Command execution** (`_run_browser_command`, line 1895):
- Resolves agent-browser CLI path
- Builds command: `agent-browser [--cdp <url>|--session <name>] --json open <url>`
- For cloud/CDP mode: `--cdp <websocket_url>`
- For local mode: `--session <session_name>`
- Sets `AGENT_BROWSER_IDLE_TIMEOUT_MS` from inactivity config
- Runs via `subprocess.Popen` with temp files for stdout/stderr

**Cleanup** (`cleanup_browser`, line 3411):
- Stops CDP supervisor
- Stops recording
- Runs `agent-browser close` (line 3487) — kills ENTIRE browser, not individual tabs
- Removes from `_active_sessions`
- For cloud sessions: calls `provider.close_session(bb_session_id)`
- Kills daemon process and cleans socket directory

**Inactivity cleanup** (`_cleanup_inactive_browser_sessions`, line 1265):
- Runs every 30 seconds in a background daemon thread
- Checks `_session_last_activity` for sessions idle > `BROWSER_SESSION_INACTIVITY_TIMEOUT` (120s default)
- Calls `cleanup_browser(task_id)` for idle sessions
- Only fires when no browser activity has happened in the timeout window

### File: `tools/browser_supervisor.py` (1475 lines)

**CDP Supervisor** (`CDPSupervisor`, line 259):
- One supervisor per (task_id, cdp_url) pair
- Maintains persistent WebSocket to the browser's CDP endpoint
- Handles dialog interception via injected JS bridge + Fetch domain
- Provides `snapshot()` for pending dialogs + frame tree
- Provides `evaluate_runtime(expression)` for JS evaluation over the live WS
- Has `_cdp(method, params, session_id)` for sending raw CDP commands (line 500+)

**Available for navigation reuse**: The supervisor's `_cdp()` method could send `Page.navigate` to navigate the current tab instead of opening a new one. Currently only used for dialog handling and runtime evaluation.

### File: `tools/browser_cdp_tool.py` (569 lines)

**Raw CDP passthrough** (`browser_cdp` tool):
- Sends arbitrary CDP commands to the WebSocket endpoint
- Supports `target_id` for page-scoped commands, `frame_id` for OOPIF-scoped
- Calls `Target.getTargets` etc. for browser-level commands

### File: `agent/browser_provider.py` (175 lines)

**ABC** for cloud providers:
- `create_session(task_id)` → returns `{session_name, bb_session_id, cdp_url, features}`
- `close_session(bb_session_id)` → closes cloud session
- `emergency_cleanup()` → force-close all sessions

### File: `agent/browser_registry.py`

**Provider registry** — lookup by name, used by `_get_cloud_provider()` to find the active provider.

### File: `tools/browser_camofox.py`

**Camofox REST API adapter** — replaces agent-browser CLI with Camofox HTTP API when `CAMOFOX_URL` is set.

## agent-browser CLI Commands

| Command | Effect | Tab behavior |
|---------|--------|-------------|
| `open <url>` | Navigate to URL | **Opens a new tab** |
| `close [--all]` | Close browser | Kills entire session |
| `back` | Go back in history | Same tab |
| `forward` | Go forward in history | Same tab |
| `reload` | Reload page | Same tab |
| `eval <js>` | Run JavaScript | Same tab |
| `snapshot` | Get accessibility tree | Same tab |
| `click <sel>` | Click element | Same tab (can open popup) |
| `screenshot [path]` | Take screenshot | Same tab |
| `connect <port|url>` | Connect to browser via CDP | Same session |

Source: `npx agent-browser --help`

**Key finding**: There is NO `close-tab` command. The only way to close a tab is via CDP (`Target.closeTarget` or `Page.close`), which requires a CDP connection.

## Config (from `~/.hermes/config.yaml`)

The relevant config section:

```yaml
browser:
  inactivity_timeout: 120
  command_timeout: 30
  record_sessions: false
  allow_private_urls: false
  engine: auto
  auto_local_for_private_urls: true
  cdp_url: ''
  dialog_policy: must_respond
  dialog_timeout_s: 300
  camofox:
    managed_persistence: false
    adopt_existing_tab: false
```

The `adopt_existing_tab: false` on camofox is interesting — it suggests tab reuse was considered for the Camofox backend but not implemented for the general case.

## Chrome DevTools MCP

Configured in `mcp_servers` as:
```yaml
chrome-devtools-mcp:
  args:
    - -y
    - chrome-devtools-mcp@latest
  command: npx
  timeout: 120
```

This connects to a real Chrome instance. Tools available include `list_pages`, `close_page`, `new_page`, `navigate_page`, `select_page`, `take_screenshot`, `take_snapshot`, `fill`, `click`, etc.

This MCP is a viable alternative for tab-aware browser automation. Unlike the native `browser_*` tools, it provides explicit tab lifecycle management.

## Fix Strategy (Recommended)

### Primary: Modify `browser_navigate` to navigate current tab

In `tools/browser_tool.py`, around line 2410, instead of always calling `_run_browser_command(nav_session_key, "open", [url])`:

1. Track whether a session has already established a tab (`_has_open_tab` flag in `_active_sessions`)
2. On first navigation: `open` creates the tab, set `_has_open_tab = True`
3. On subsequent navigations:
   - If CDP supervisor is active: `supervisor.navigate_current_tab(url)` via `_cdp("Page.navigate", {"url": url})`
   - If no CDP supervisor (local mode): `_run_browser_command(nav_session_key, "eval", [f"window.location.href='{url}'"])`
   - Fallback: `_run_browser_command(nav_session_key, "open", [url])` with an immediate close of the spare tab via `eval` and `window.close()`

### Secondary: Close consumed tabs

Add a tab tracker to `_active_sessions` that records all open tab targets. After a navigation is consumed (snapshot/screenshot taken), close the old tab via CDP:
```python
await supervisor._cdp("Target.closeTarget", {"targetId": old_tab_id})
```

Or via a periodic reaper: count open tabs via `Target.getTargets` and close all but the active one.

### Considerations

- **SSRF/redirect safety**: The post-redirect check in `browser_navigate` (lines 2431-2454) navigates away to `about:blank` if a redirect lands on a blocked URL. This would need to be preserved.
- **Cross-origin eval**: `window.location.href = url` works for same-origin but may fail or throw for cross-origin navigations in some cases. `Page.navigate` via CDP is more reliable.
- **Session duration**: With tab reuse, sessions should live longer (no need to kill after 120s) since they only have one tab. Consider increasing `inactivity_timeout` or making it dynamic.
