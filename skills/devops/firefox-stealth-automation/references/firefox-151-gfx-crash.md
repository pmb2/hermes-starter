# Firefox 151 GFX Compositor Crash with --remote-debugging-port

## Crash Signature

Firefox 151.0.2 (this machine: Windows 10) crashes consistently when `--remote-debugging-port` is active:

```
WebDriver BiDi listening on ws://127.0.0.1:9222
[ERROR shell_windows::limited_access_features] Error generating feature token: NS_ERROR_FAILURE
[GFX1-]: CompositorBridgeChild receives IPC close with reason=AbnormalShutdown
Exiting due to channel error.
```

**Exit codes observed:**
- `4294967295` (0xFFFFFFFF) — forced kill / abnormal termination
- `3489660927` (0xD00000FF) — GPU/compositor crash
- `1` — clean exit (when MOZ_DISABLE_NONLOCAL_CONNECTIONS blocks OpenH264)
- `127` — MSYS artifact (bash returns this when a Windows process crashes)

## Crash Timing by Profile

| Profile type | Time to crash | Notes |
|-------------|--------------|-------|
| Fresh profile (without prefs) | 2-8s | Crashes before any page loads |
| Fresh profile (all GPU disabled) | 60s+ or never starts BiDi | BiDi doesn't bind at all |
| Old profile (<profile-id>, established) | 40-60s | Lives long enough for some work |

## What Does NOT Help

- `--disable-gpu` — flag ignored, crash still happens
- `--disable-webrender` — does not prevent compositor crash
- `--safe-mode` — suppresses BiDi entirely (safe mode disables remote debugging)
- `--no-e10s` (single process) — still crashes
- GPU-disabling `user.js` prefs (`layers.acceleration.disabled`, `gfx.webrender.force-disabled`, `gfx.direct2d.disabled`, `webgl.disabled`) — no effect on crash
- Patched xul.dll (`${USER_HOME}\firefox-portable\`) — same crash; the issue is GFX, not navigator.webdriver
- `--headless` — avoids crash, but then BiDi never starts (headless blocks BiDi startup on Firefox 151)
- Fresh profile vs old profile — timing differs but crash inevitable

## What Partially Works

- **Old profile (<profile-id>) buys 40-60s**: Use the established profile. Act fast — navigate, extract, and disconnect within the window.
- **Python subprocess** is the only reliable launch method (bash/cmd both introduce quoting/process issues on top of the crash)
- **Between launches, kill ALL processes and wait 35s** for TIME_WAIT ghosts. Orphan `crashreporter.exe` and `crashhelper.exe` processes accumulate with each crash and must be killed.

## Root Cause Hypothesis

`[ERROR shell_windows::limited_access_features] Error generating feature token: NS_ERROR_FAILURE` suggests Firefox's GPU sandbox/access feature token system fails on this Windows 10 machine. This triggers the compositor to shut down (`CompositorBridgeChild` IPC close), which cascades into the full browser crash.

The `limited_access_features` system was introduced in Firefox 135+ for GPU process security. This specific Windows machine may have a driver/compatibility issue with it.

## Workaround for Short BiDi Windows

When you need to get work done within the 40-60s window:

1. Launch via Python subprocess with <profile-id> profile
2. Immediately try the BiDi port check in a tight loop (2s interval)
3. As soon as BiDi is ready, send your commands in rapid succession
4. Expect the crash — design for it. Reconnect if needed.
5. Kill all orphans and wait 35s between launch attempts

## Long-term Fix

- **Update Firefox** to a version past 151.x where this crash may be fixed
- Or investigate the GPU `limited_access_features` token generation failure — may need a driver update or GPU compatibility mode
