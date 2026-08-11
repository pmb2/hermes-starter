# Docker Desktop Diagnostic Chain — Session Detail

Date: 2026-05-30
Setup: Windows 10, git-bash (MSYS), Docker Desktop 29.5.2 (WSL2 backend)

## Presentation

`docker ps` times out (exit code 124 after 15s). Docker Desktop GUI processes are running. `docker context ls` shows `desktop-linux *` pointing to `npipe:////./pipe/dockerDesktopLinuxEngine`.

## The Full Diagnostic Chain

### Step 1: Is Docker Desktop running?

```bash
powershell -Command "Get-Process 'Docker Desktop','com.docker.backend' -ErrorAction SilentlyContinue | Format-Table Name, Id"
# → Multiple Docker Desktop.exe + com.docker.backend.exe processes → GUI IS running
```

If no Docker processes found, Docker Desktop isn't launched. Start it:
```bash
"C:\Program Files\Docker\Docker\Docker Desktop.exe"
```
Wait 30-120s for the engine to initialize.

### Step 2: Check WSL distro state

```bash
wsl -l -v
# Expected:
#   docker-desktop    Running    2
#   Ubuntu           Stopped     2   (optional — Docker Desktop uses its own distro)
```

If `docker-desktop` is Stopped, the WSL2 VM hasn't booted. Start it:
```bash
wsl -d docker-desktop -e /bin/true
# Or kill Docker processes + relaunch (see Phase 5 Recovery Path B)
```

### Step 3: Enumerate named pipes

```powershell
[System.IO.Directory]::GetFiles("\\.\pipe\") | Where-Object { $_ -match 'docker' }
```

Expected: `dockerDesktopLinuxEngine` should appear. Also see `dockerBackendApiServer`, `docker_engine`, etc.

If no docker pipes exist, the Docker Desktop backend process isn't running its pipe server. This is a deeper failure.

### Step 4: Test pipe connectivity

```powershell
$client = New-Object System.IO.Pipes.NamedPipeClientStream('.', 'dockerDesktopLinuxEngine', [System.IO.Pipes.PipeDirection]::InOut)
$client.Connect(5000)
Write-Host "PIPE_CONNECTED: $($client.IsConnected)"
$client.Close()
```

If this connects, the named pipe server is alive at the transport level. The failure is further up — the backend can't reach the engine.

If this fails with timeout, the pipe server isn't accepting connections.

### Step 5: Docker Python SDK diagnostics

The Docker Python SDK connects through the same named pipe as the CLI but returns proper error messages instead of hanging:

```bash
python -c "
import docker
try:
    c = docker.DockerClient(base_url='npipe:////./pipe/dockerDesktopLinuxEngine')
    print('Connected. Containers:', len(c.containers.list(all=True)))
except Exception as e:
    print(f'Error: {e}')
"
```

**On this session the result was:** `docker.errors.APIError: 500 Server Error for http+docker://localnpipe/version: Internal Server Error`

The 500 error means the pipe bridge is up but the backend can't reach the engine. The Docker CLI in git-bash also hangs for the same reason.

### Step 6: Backend log — confirm "no route to host"

```bash
grep "no route to host" "$LOCALAPPDATA/Docker/log/host/com.docker.backend.exe.log" | tail -3
```

**On this session:**
```
[com.docker.backend.exe.apiproxy] still dialing 192.168.65.7:2376 after 7.8041719s: connect tcp 192.168.65.7:2376: no route to host
```

This is the root cause. The backend proxy tries to forward named pipe requests to the Docker engine at `192.168.65.7:2376` (the WSL2 VM's internal network), but gets "no route to host" — the WSL2 network bridge is broken.

### Step 7: VM init log — was engine ever alive?

```bash
tail -30 "$LOCALAPPDATA/Docker/log/vm/init.log"
```

**On this session:** The log showed active apiproxy traffic with container stats requests (`GET /v1.54/containers/*/stats`) from a previous session where the engine was working. The engine had been alive and was processing API calls, but the named pipe bridge died during a WSL2 network outage.

### Step 8: Check `com.docker.service`

```bash
powershell -Command "Get-Service com.docker.service | Format-Table Name, Status, StartType"
```

**On this session:** `com.docker.service → Stopped, Manual`. Starting it requires admin:
```bash
powershell -Command "Start-Service com.docker.service"  # → Access Denied
```

This is a common bottleneck — the service that manages the Windows↔WSL2 named pipe bridge requires elevation. Docker Desktop normally manages this itself, but when the bridge breaks, only an admin restart or the full kill+relaunch cycle can reset it.

## What Did NOT Work

| Attempt | Result |
|---------|--------|
| `wsl --terminate docker-desktop` | WSL responded "completed successfully" but Docker respawned it immediately |
| `wsl --shutdown` + restart | Docker Desktop relaunched but engine never came back |
| `MSYS_NO_PATHCONV=1` docker ps | Path now resolves but pipe isn't available → "file not found" |
| Context switching (`default`, `desktop-windows`) | Default hangs, desktop-windows returns 500 |
| Killing Docker processes + restarting (once) | Engine returned 500 after restart (6+ minutes waiting) |
| Wait 120+ seconds after restart | Engine never became accessible |
| Docker Python SDK | Connected but returned 500 |

## What Eventually Fixed It (in previous successful sessions)

From the existing Phase 5 skill:

**Path B: Full Recovery (Kill + Relaunch)** — Kill ALL Docker processes (including respawns), `wsl --shutdown`, wait 30s, launch Docker Desktop fresh, wait 120-180s.

**Path D: Nuclear Recovery** — The `docker-desktop` WSL distro persists even after `wsl -t` because Docker's watchdog respawns it. Kill ALL Docker processes first, THEN terminate the distro, THEN restart Docker Desktop. See `references/docker-desktop-wsl-wedge-recovery.md` in the `self-hosted-communication-server` skill.

## Session 2026-05-30 (Successful Recovery via Path B)

**Scenario:** Cron job health check. Docker Desktop processes were running but `docker ps` timed out in git-bash (exit 124 after 15s). `docker context ls` worked (client-only, no daemon contact).

**Diagnosis:**
- WSL distros: `docker-desktop Running`, `Ubuntu Stopped` — the Ubuntu distro (used as the WSL integration distro) wasn't booted
- `tasklist | grep docker`: 10+ Docker processes present — GUI was running
- Named pipe `dockerDesktopLinuxEngine` existed per PowerShell enumeration
- Engine PID inside docker-desktop WSL distro: alive but unreachable via named pipe bridge
- Backend logs showed active traffic from Docker Desktop UI — engine was actually functional

**Action taken:**
1. Killed all Docker processes via `taskkill //F`
2. `wsl --shutdown` (both distros stopped)
3. Waited 5s
4. Launched Docker Desktop fresh
5. Waited 120s
6. Started Ubuntu WSL distro: `wsl -d Ubuntu -e bash -c "echo alive"` (kicked the WSL2 VM)
7. Waited another 120s (240s total)

**Result after recovery:** `docker ps` still hung in git-bash (MSYS path issue), but `powershell.exe -Command "docker ps --format '{{.Names}} {{.Status}}'"` worked immediately — returned the full container list. The engine was fully healthy.

**Key takeaway for this environment:** After a clean Path B recovery with adequate wait time (≈4 min total), the Docker engine comes back. The git-bash CLI will still hang due to MSYS named pipe path corruption — PowerShell is the reliable access method. Run `docker` commands via `powershell.exe -Command "docker ..."` to bypass the MSYS path issue entirely. This is not a sign that the engine is still down.

## Key Insight: The 500 Error on `/version`

The Docker Python SDK connects to the named pipe and gets `500 Internal Server Error` for the `/version` endpoint. This is the same error that `docker ps` would return if it could connect through the pipe at all. In git-bash, the MSYS path translation causes `docker ps` to hang instead of returning the 500, masking the real error.

The fix for the CLI hang in git-bash is either:
1. Use PowerShell's native `docker.exe` (same binary, no MSYS path interference)
2. Use the Docker Python SDK for diagnostics
3. Use `docker --context desktop-windows ps` — returns the 500 directly instead of hanging
