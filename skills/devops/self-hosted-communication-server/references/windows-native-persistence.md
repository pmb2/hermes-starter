# Windows Native Persistence for Spacebar Stack

Full setup walkthrough for making a native (non-Docker) Spacebar server + SSH tunnel survive Windows reboots, using the Startup folder VBS approach.

## Complete File Set

### 1. `start-stack.bat` — Dual auto-restart launcher

```batch
@echo off
REM Spacebar Stack Launcher — runs Spacebar server + SSH tunnel
REM ============================================================================
REM Launched from Startup folder. Runs minimized via VBS wrapper.
REM Each component runs in its own hidden window with auto-restart loop.

cd /d "${MY_REPOS}\Documents\github\spacebar"

REM Ensure logs directory exists
if not exist "logs" mkdir "logs"

REM ── 1. Start SSH Tunnel (autossh-style: reconnect loop) ──────────────────
start /min "SpacebarTunnel" cmd /c ^
  ":tunnel^
  echo [%%date%% %%time%%] Starting SSH tunnel... >> "logs\tunnel.log"^
  "C:\Program Files\Git\usr\bin\ssh.exe" -i "${USER_HOME}\.ssh\oracle_vps" ^
    -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -o TCPKeepAlive=yes ^
    -N -R 0.0.0.0:3001:localhost:3001 ubuntu@129.153.156.190 >> "logs\tunnel.log" 2>&1^
  echo [%%date%% %%time%%] Tunnel exited, reconnecting in 5s... >> "logs\tunnel.log"^
  timeout /t 5 /nobreak >nul^
  goto tunnel"

REM ── 2. Start Spacebar Server (auto-restart loop) ────────────────────────
set NODE_ENV=production
set PORT=3001
set DATABASE=postgres://spacebar_admin:***@127.0.0.1:5432/spacebar

start /min "SpacebarServer" cmd /c ^
  ":server^
  echo [%%date%% %%time%%] Starting Spacebar... >> "logs\server.log"^
  "C:\Program Files\nodejs\node.exe" --enable-source-maps dist/bundle/start.js >> "logs\server.log" 2>&1^
  echo [%%date%% %%time%%] Server exited, restarting in 3s... >> "logs\server.log"^
  timeout /t 3 /nobreak >nul^
  goto server"

echo Spacebar stack launch complete.
exit /b 0
```

**Location:** `${MY_REPOS}\Documents\github\spacebar\start-stack.bat`

### 2. `SpacebarStack.vbs` — Invisible launcher

```vbs
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "${MY_REPOS}\Documents\github\spacebar\start-stack.bat", 0, False
```

**Location:** `C:\Users\<User>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\SpacebarStack.vbs`

### 3. Hermes Gateway `.cmd` files — Agent startup

Each Hermes Dev Team agent has a `.cmd` file in the same Startup folder:

```batch
@echo off
rem Hermes Agent Gateway - Messaging Platform Integration
start "" /min cmd.exe /d /c ${USER_HOME}\AppData\Local\hermes\profiles\<agent>\gateway-service\Hermes_Gateway_<agent>.cmd
```

These reference a second `.cmd` in the agent's gateway-service directory that runs the actual gateway:

```batch
@echo off
rem Hermes Agent Gateway - Messaging Platform Integration
cd /d ${USER_HOME}\AppData\Local\hermes\hermes-agent
set "HERMES_HOME=${USER_HOME}\AppData\Local\hermes\profiles\<agent>"
set "PYTHONIOENCODING=utf-8"
set "HERMES_GATEWAY_DETACHED=1"
set "VIRTUAL_ENV=${USER_HOME}\AppData\Local\hermes\hermes-agent\venv"
${USER_HOME}\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe -m hermes_cli.main --profile <agent> gateway run
exit /b 0
```

**Location:** `${USER_HOME}\AppData\Local\hermes\profiles\<agent>\gateway-service\Hermes_Gateway_<agent>.cmd`

## Boot Sequence

```
Windows boots
  → User logs in
    → Windows processes Startup folder items (alphabetically, no guaranteed order)
      → SpacebarStack.vbs
        → start-stack.bat
          → start /min "SpacebarServer" (auto-restart loop)
          → start /min "SpacebarTunnel" (auto-restart loop)
      → Hermes_Gateway_forge.cmd
        → pythonw.exe -m hermes_cli.main --profile dev-lead gateway run
      → Hermes_Gateway_scribe.cmd (same pattern)
      → Hermes_Gateway_sentry.cmd (same pattern)
      → Hermes_Gateway_skillmate.cmd (same pattern)
      → Hermes_Gateway_weaver.cmd (same pattern)
```

**Timing after login:**
- 0s — Startup scripts launch
- 10s — Hermes gateways attempt connection (may fail if Spacebar not ready yet, auto-reconnect)
- 45-60s — Spacebar finishes route registration, port 3001 opens
- ~60s — API starts responding
- ~90s — Everything operational

The Hermes gateway auto-reconnects on disconnect, so it will connect as soon as Spacebar is ready.

## Troubleshooting "502 Bad Gateway" / "res.errors is undefined"

The Fermi client in the browser shows `TypeError: can't access property "at", res.errors is undefined` when the API response is not valid JSON (e.g., Caddy returns an HTML 502 page because the upstream is down).

**Diagnosis flow:**

```
Browser sees "can't access property at, res.errors is undefined"
  ↓
Open DevTools Console — the real issue is the failed fetch before that error
  ↓
Check https://discy.your-domain.example/api/v9/auth/login
  → 401 = OK (server running, need auth)
  → 502 = Caddy can't reach backend
  → 000 = DNS/Caddy down
  ↓
If 502, check VPS port 3001:
  ssh ... "ss -tlnp | grep 3001"
  → sshd listening = tunnel port claimed (good)
  → nothing = tunnel not claimed
  ↓
Check local port 3001:
  netstat -ano | grep LISTENING | grep 3001
  → node.exe = Spacebar running
  → nothing = Spacebar dead — restart
  ↓
Check port mismatch:
  netstat -ano | grep LISTENING | grep -E "3001|3100"
  Server on 3100 but tunnel/R forwards 3001? → need PORT=3001
```

**Common root causes:**

| Symptom | Cause | Fix |
|---------|-------|-----|
| discy returns 502, localhost:3001 works | SSH tunnel died | Restart tunnel or wait for auto-restart |
| discy returns 502, localhost:3001 also dead | Spacebar crashed | Check logs, restart; auto-restart loop should catch it within 3s |
| discy returns 502, localhost:3001 dead, localhost:3100 works | Port mismatch | Kill 3100 process, start Spacebar on PORT=3001 |
| SSH tunnel won't claim port on VPS | GatewayPorts not enabled on VPS sshd | `sudo sed -i 's/^#GatewayPorts no/GatewayPorts yes/' /etc/ssh/sshd_config && sudo systemctl restart sshd` |
| Caddy returns 404 for /api/* | Caddy config uses handle_path instead of handle @api | Use `@api path /api/*` + `handle @api` — NOT `handle_path /api/*` (which strips the prefix) |

## If Port 3001 is Already in Use

```bash
# Find the PID
netstat -ano | grep LISTENING | grep 3001

# Kill it
taskkill //F //PID <pid>

# On Windows, also check for wslrelay.exe (Docker WSL port relay) which may hold the port
tasklist //FI "IMAGENAME eq wslrelay.exe"
```

## SSH Tunnel Details

The existing tunnel commands as observed from running processes:

```bash
# Tunnel 1: Spacebar API
ssh -i ${USER_HOME}/.ssh/oracle_vps \
  -o StrictHostKeyChecking=no \
  -o ServerAliveInterval=60 \
  -o ExitOnForwardFailure=yes \
  -N -R 0.0.0.0:3001:localhost:3001 ubuntu@129.153.156.190

# Tunnel 2: Fermi UI  
ssh -i ${USER_HOME}/.ssh/oracle_vps \
  -o StrictHostKeyChecking=no \
  -o ServerAliveInterval=60 \
  -o ExitOnForwardFailure=yes \
  -N -R 0.0.0.0:8081:localhost:8080 ubuntu@129.153.156.190
```

Note the Fermi UI tunnel maps VPS:8081 → localhost:8080 (not 8081 locally). This is because the Fermi dev server runs on 8080.

## Caddy Config on VPS (for reference)

The Caddy container (`hmac-caddy`) runs the config from `/home/ubuntu/Caddyfile`:

```caddy
discy.your-domain.example {
  encode gzip

  # Well-known auto-discovery for Fermi
  @wellknown path /.well-known/spacebar*
  handle @wellknown {
    header Content-Type application/json
    respond {"api":"https://discy.your-domain.example/api/v9"}
  }

  # API + WebSocket — use handle @api, NOT handle_path
  @api path /api/*
  handle @api {
    reverse_proxy 172.17.0.1:3001
  }

  # Fermi UI
  handle {
    reverse_proxy 172.17.0.1:8081
  }
}
```

Where `172.17.0.1` is the Docker bridge gateway (host machine accessible from inside Docker containers). The SSH tunnels bind to `0.0.0.0` on the VPS (requires `GatewayPorts yes`), allowing Docker containers to reach them.

## VPS iptables Rules

Docker containers CANNOT reach SSH reverse tunnel ports on the host by default — iptables blocks them. The ACCEPT rule must be inserted **BEFORE** the REJECT rule in the INPUT chain:

```bash
sudo iptables -I INPUT 7 -i docker0 -p tcp --dport 3001 -j ACCEPT
sudo iptables -I INPUT 7 -i docker0 -p tcp --dport 8081 -j ACCEPT
```

Check existing rules with `sudo iptables -L INPUT -n -v --line-numbers` to find the right insertion point (typically just before the final REJECT).
