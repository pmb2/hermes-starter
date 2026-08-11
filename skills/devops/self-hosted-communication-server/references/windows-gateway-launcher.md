# Windows Persistent Gateway Launcher

Batch-file approach for running a Hermes gateway continuously on Windows without depending on Hermes background terminal (which kills processes when the parent session ends).

## The Pattern

```batch
@echo off
set HERMES_HOME_BASE=%USERPROFILE%\AppData\Local\hermes
cd /d %~dp0..\..\Documents\github\agent-fleet

:restart
echo [%date% %time%] Starting gateway...
set DISCORD_BOT_TOKEN=
set SPACEBAR_BOT_TOKEN=
set SPACEBAR_GATEWAY_URL=
set SPACEBAR_API_URL=

for /f "tokens=1,* delims==" %%a in ('type "%HERMES_HOME_BASE%\profiles\<profile>\.env"') do set "%%a=%%b"

del /f /q "%HERMES_HOME_BASE%\profiles\<profile>\gateway.pid" 2>nul
del /f /q "%HERMES_HOME_BASE%\profiles\<profile>\gateway_state.json" 2>nul

start /B /WAIT python scripts/spacebar-gateway.py <profile>

echo [%date% %time%] Gateway exited - restarting in 5 seconds...
timeout /t 5 /nobreak >nul
goto restart
```

## How It Works

| Component | Purpose |
|-----------|---------|
| `:restart` loop label | Infinite restart — no external supervisor process needed |
| `set VAR=` at top | Clears stale env vars that might bleed from previous iteration |
| `for /f` loop reads `.env` | Loads per-profile environment (DISCORD_BOT_TOKEN, SPACEBAR_API_BASE, etc.) |
| `del /f /q gateway.pid` | Prevents stale-PID lock from blocking restart |
| `del /f /q gateway_state.json` | Prevents stale-connection-state confusion |
| `start /B` | Creates a detached child process that survives the parent shell |
| `/WAIT` | Makes the batch script block until the gateway exits |
| `goto :restart` | Loops back after a 5-second pause |

## Installation

1. Save the `.bat` file to `%USERPROFILE%\AppData\Local\hermes\start-<profile>-gateway.bat`
2. Create a shortcut in `shell:startup` (Windows + R, shell:startup):
   ```
   Target: %USERPROFILE%\AppData\Local\hermes\start-<profile>-gateway.bat
   Start in: %USERPROFILE%\Documents\github\agent-fleet
   Run: Minimized
   ```
3. Or run it manually from a terminal (it will survive closing the terminal)

## Troubleshooting

### Gateway crashes immediately (stale lock file)
```batch
del /f /q "%HERMES_HOME_BASE%\profiles\<profile>\gateway.lock*"
del /f /q "%HERMES_HOME_BASE%\profiles\<profile>\gateway.pid"
del /f /q "%HERMES_HOME_BASE%\profiles\<profile>\gateway_state.json"
```

### Token is stale (JWT expired)
Generate a fresh token via the Spacebar login endpoint:
```batch
curl -s -X POST https://gc.your-domain.example/api/v9/auth/login -H "Content-Type: application/json" -d "{\"login\":\"<username>\",\"password\":\"<password>\"}"
```
Copy the `token` field from the response, then update the profile `.env`:
```
DISCORD_BOT_TOKEN=<fresh-token>
```

### Gateway starts but shows wrong user ID
Environment bleed from a previous run. Add explicit `set VAR=` lines for every Spacebar env var before the `for /f` loop that reads `.env`.

## Vs. Alternative Approaches

| Approach | Survives Terminal Close | Auto-Restarts | Requires External Supervisor |
|----------|------------------------|---------------|------------------------------|
| `nohup python ... &` | No (Windows MSYS kills on parent exit) | No | Yes |
| `terminal(background=true)` | No (Hermes kills on session end) | No | Yes |
| Windows Task Scheduler | Yes | Yes (via trigger) | No |
| **Batch `:restart` loop** | **Yes** (`start /B` detaches) | **Yes** (infinite loop) | **No** |
| NSSM (service wrapper) | Yes | Yes | Yes (installed) |

The batch restart loop is the simplest zero-dependency approach that survives terminal closure and auto-restarts.
