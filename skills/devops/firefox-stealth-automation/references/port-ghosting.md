# Port Ghosting — TIME_WAIT on Firefox Remote Debug Ports

## Problem

When Firefox is force-killed (`taskkill.exe //F //IM firefox.exe`) while running with `--remote-debugging-port`, the TCP port enters TIME_WAIT state for up to 2 minutes on Windows. Any subsequent attempt to start Firefox on the same port within this window will either:

- Fail immediately (`Address already in use`), or
- The port check (`socket.create_connection`) returns True (TIME_WAIT allows connection to non-LISTENER sockets), fooling our startup logic into thinking Firefox is ready when it's really a ghost

## Orphan Process Accumulation

Repeated force-killing of Firefox (`taskkill /F /IM firefox.exe`) leaves behind `crashreporter.exe` and `crashhelper.exe` processes that also hold port ghosts. These accumulate across sessions.

### Symptoms
- `tasklist | findstr firefox` shows 10-30+ processes including `crashreporter.exe` and `crashhelper.exe`
- Port checks return 404 (httpd.js ghost) despite no visible LISTENING entry
- Fresh Firefox launches fail silently or bind to unexpected ports

### Cleanup pattern

```python
import os
# Kill ALL Firefox-related processes, not just firefox.exe
os.system('taskkill /F /IM firefox.exe 2>nul')
os.system('taskkill /F /IM crashreporter.exe 2>nul')
os.system('taskkill /F /IM crashhelper.exe 2>nul')
time.sleep(35)  # wait out TIME_WAIT ghosts
```

### Detection

```bash
# Check for ghost: if no LISTENING entry but port_open returns True
netstat -ano | grep ':9228' | grep LISTENING || echo "No listener -- ghost port"

# Count orphan processes
ps -W | grep -c -E 'firefox|crashreport|crashhelper'
# If >5, cleanup needed

- Firefox starts in <1 second (impossible — real Firefox takes 2-5 seconds to open a debug port)
- `port_open()` returns True but BiDi session connection fails
- Netstat shows `TIME_WAIT` entries on the target port but no `LISTENING` entry

## Detection

```bash
# Check for ghost: if no LISTENING entry but port_open returns True
netstat -ano | grep ':9228' | grep LISTENING || echo "No listener — ghost port"
```

## Solutions

### 1. Use a fresh port each time (preferred)

Pick a high unused port (9227+). Avoid ports that were used recently.

```python
BIDI_PORT = 9228  # Or 9230, 9231, etc.
```

### 2. Wait for port to release (30-40s is usually enough)

After killing Firefox, wait 30-40 seconds for TIME_WAIT to expire:

```python
time.sleep(35)  # 30-40s clears most TIME_WAIT ghosts
```

### 3. Kill parent process cleanly

Instead of `taskkill /f`, try graceful termination first:

```python
proc.terminate()  # SIGTERM
try:
    proc.wait(timeout=15)
except:
    proc.kill()  # SIGKILL if graceful fails
```

### 4. Stop all Firefox processes before changing ports

```bash
taskkill.exe //F //IM firefox.exe
# Wait for TIME_WAIT to clear
sleep 5
```
