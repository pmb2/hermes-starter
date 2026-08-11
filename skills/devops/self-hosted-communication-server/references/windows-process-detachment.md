# Windows Process Management for Hermes Gateways

## The Problem

`subprocess.Popen` children on Windows **do not survive parent process exit**. Even with `creationflags=subprocess.CREATE_NO_WINDOW`, Windows job objects attach child processes to the parent's job — when the parent exits, all children are terminated.

## Solutions

### 1. VBScript WshShell.Run (Most Reliable)

```vbscript
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\path\to\hermes-agent"
cmd = """" & pythonExe & """ """ & gatewayScript & """ " & botName
WshShell.Run cmd, 0, False  ' 0=hidden, False=async/detached
```

**Caveat:** Environment variables are NOT inherited. Gateway must read token from `.env.spacebar` file.

### 2. PowerShell Start-Process

```powershell
Start-Process -WindowStyle Hidden -FilePath $pythonExe `
    -ArgumentList @($gateway, $name) -WorkingDirectory $cwd
```

**Pitfall:** Do NOT combine `-NoNewWindow` with `-WindowStyle Hidden` — they conflict.

### 3. Terminal foreground (Dev/Debug)

```bash
terminal(command="python gateway-script.py <name>", timeout=300)
```

### 4. What Does NOT Work on Windows

| Method | Why It Fails |
|--------|-------------|
| `subprocess.Popen(creationflags=CREATE_NO_WINDOW)` | Children die when parent exits |
| `shell &` (backgrounding) | Same job-object issue |
| `nohup python ... &` | No nohup equivalent on Windows |
| `terminal(background=true)` | Dies when Hermes session ends |

## Token File Fallback

Detached processes do NOT inherit env vars. Resolution order in gateway script:

1. `SPACEBAR_BOT_TOKEN` env var
2. `DISCORD_BOT_TOKEN` env var
3. Profile `.env` file
4. Profile `.env.spacebar` file

Option 4 is the critical fallback for detached launch.

## Resource Usage

39 gateways idle: ~600MB RAM (~15MB per process, Python interpreter shared).
3-4 actively reasoning: ~+200MB.
CPU: near-zero (WebSocket heartbeat every 40s).
