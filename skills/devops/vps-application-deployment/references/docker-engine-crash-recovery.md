# Docker Desktop 500 Error + WSL2 Lockup Recovery

> Context: Docker Desktop engine returned HTTP 500 Internal Server Error on all named pipes (`dockerDesktopLinuxEngine`, `dockerDesktopWindowsEngine`, `docker_engine`). Attempting any `docker version` or `docker ps` call hung indefinitely, and the backend crash locked the WSL2 VM so that `wsl --list` also hung.

## Symptoms

```
$ docker version
Client: 29.5.2
Server:
  request returned 500 Internal Server Error for API route and version
  http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.54/version
  check if the server supports the requested API version
```

All three Docker contexts return the same error:
- `desktop-linux` (npipe://dockerDesktopLinuxEngine)
- `desktop-windows` (npipe://dockerDesktopWindowsEngine)
- `default` (npipe://docker_engine)

WSL also hangs:
```
$ wsl --list
[ hangs indefinitely ]
$ wsl -d Ubuntu -- hostname
[ hangs indefinitely ]
```

Docker processes appear alive but unresponsive:
```
$ powershell Get-Process docker*,com.docker*
com.docker.backend   (Running)
com.docker.build     (Running)
docker               (Running)
Docker Desktop       (Running)
docker-sandbox       (Running)
```

## Root Cause

Docker Desktop's WSL2 backend VM enters a corrupted state — the Linux engine inside the VM can't start, but the Windows-side processes still think it's running. This blocks WSL2 entirely because Docker holds the WSL VM lock.

## Recovery Procedure

### Step 1: Kill ALL Docker processes

```powershell
Get-Process Docker*,com.docker* -ErrorAction SilentlyContinue |
  Stop-Process -Force -ErrorAction SilentlyContinue
```

### Step 2: Shut down WSL

```powershell
wsl --shutdown
```

If `wsl --shutdown` also hangs (because Docker still holds the lock from Step 1 not fully completing):

```cmd
REM Run as Administrator:
net stop LxssManager
net start LxssManager
```

### Step 3: Verify WSL is released

```powershell
wsl --list --verbose
# Should return quickly with "Stopped" status for all distros
```

### Step 4: Start WSL distro directly (without Docker)

```powershell
wsl -d Ubuntu -u root -- bash -c 'hostname'
# Should return the hostname quickly
```

### Step 5: Restart Docker Desktop

```powershell
Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
```

Or with admin prompt (triggers UAC):
```powershell
Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe' -Verb RunAs
```

### Step 6: Verify Docker engine is healthy

```powershell
# Wait 30-60 seconds for engine to initialize
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' version
# Should show both Client and Server sections
```

## Prevention

- **Don't kill `com.docker.service` while containers are running** — this can corrupt the WSL2 VM state
- **Use Docker Desktop tray menu → Troubleshoot → Restart** rather than force-killing processes
- **Keep Docker Desktop updated** — older versions are more prone to engine crashes
- **If the 500 error recurs**, try `Reset to factory defaults` from Docker Desktop → Troubleshoot → Reset

## If Recovery Fails (Nuclear Option)

```powershell
# 1. Uninstall Docker Desktop (preserves images in Docker Desktop's WSL2 data distro)
# 2. Reset WSL: wsl --shutdown && wsl --unregister Ubuntu && wsl --unregister docker-desktop
# 3. Reinstall Docker Desktop
# 4. Re-import WSL distro if needed: wsl --import Ubuntu <install-path> <tar-file>
```

## Key Diagnostics

```powershell
# Check Docker contexts
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' context ls

# Check WSL VM mode error
wsl --set-version Ubuntu 2
# Error: Wsl/Service/WSL_E_VM_MODE_INVALID_STATE means VM is corrupted

# Check Docker Desktop logs
Get-Content "$env:LOCALAPPDATA\Docker\log.txt" -Tail 50

# Check Windows event log
Get-WinEvent -LogName Application | Where-Object { $_.ProviderName -like "*Docker*" } | Select-Object -First 10
```
