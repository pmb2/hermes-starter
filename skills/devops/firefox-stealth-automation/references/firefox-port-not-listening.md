# Firefox Not Listening on Debug Port — Diagnostic

## Symptom

MCP server (ultimate-firefox-mcp) won't connect. `netstat -ano | grep LISTENING` shows no port 9222, 9223, or 9239. Firefox processes are running in Task Manager.

## Root Cause

Firefox was started **normally** (via Start Menu, taskbar, or file association) — NOT with `--remote-debugging-port`. Normal Firefox starts DO NOT enable the BiDi/CDP WebSocket listeners. The browser works fine for the user but no automation tool can connect.

This is the default state of any normal Firefox launch. It is NOT a bug.

## Diagnostic Commands

```bash
# 1. Check if Firefox is running at all
tasklist //FI "IMAGENAME eq firefox.exe" 2>/dev/null

# 2. Check if remote debugging ports are listening
netstat -ano | grep -E "9222|9223|9239" | grep LISTENING

# If step 2 returns nothing but step 1 shows running Firefox:
# → Firefox is running as a normal browser, not for automation
```

## Fix

Start Firefox with `--remote-debugging-port`:

### Option A: Launcher script
```bash
cmd.exe /c "${USER_HOME}\AppData\Local\hermes\firefox-stealth.bat"
```

### Option B: Direct portable Firefox
```bash
"${USER_HOME}/firefox-portable/firefox.exe" \
  --remote-debugging-port 9239 \
  --no-remote \
  --profile "${USER_HOME}\AppData\Local\hermes\firefox-profile"
```

### Option C: Python subprocess (most reliable on Windows/MSYS)
```python
import subprocess, urllib.request, json, time

def launch_automation_firefox(port=9239, timeout=30):
    """Start Firefox with remote debugging and wait for port."""
    binary = r"${USER_HOME}\firefox-portable\firefox.exe"
    profile = r"${USER_HOME}\AppData\Local\hermes\firefox-profile"
    
    proc = subprocess.Popen([
        binary, "--remote-debugging-port", str(port),
        "--no-remote", "--profile", profile, "--new-window", "about:blank"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    for i in range(timeout):
        time.sleep(1)
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2)
            data = json.loads(resp.read())
            print(f"Firefox ready! {data.get('Browser', '?')}")
            return proc
        except:
            if proc.poll() is not None:
                raise RuntimeError(f"Firefox died with code {proc.returncode}")
    raise TimeoutError(f"Firefox didn't bind port {port} after {timeout}s")

# Usage
proc = launch_automation_firefox()
# ... do work ...
proc.terminate()
```

## Verification

After starting with `--remote-debugging-port`, verify:
```bash
curl http://127.0.0.1:9239/json/version
# Should return JSON with "Browser": "Firefox ..."
```

## Key Insight

`yt-dlp --cookies-from-browser firefox` does NOT need Firefox to be on a debug port. It reads cookie files directly from the Firefox profile directory. This is why YouTube ingestion works with yt-dlp but MCP browser tools don't connect — they use different mechanisms to talk to Firefox.
