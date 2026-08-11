# Windows Gateway Lock Troubleshooting

## Symptom

`gateway.lock` at `HERMES_HOME` (e.g. `C:\Users\<user>\AppData\Local\hermes\gateway.lock`)
can't be deleted — `WinError 32: The process cannot access the file because it
is being used by another process`. Running `acquire_gateway_runtime_lock()`
returns False even though no Python/Heres process is running.

## Root Cause

The gateway lock uses `msvcrt.locking(handle, LK_NBLCK, 1)` at byte offset
**1,048,576 (1MB)** on the lock file. When the owning process terminates
abnormally, the Windows kernel can orphan the byte-range lock even after the
process handle is closed. The file handle itself may be held by:
- A zombie process (unreachable via taskkill)
- A bash.exe/MSYS2 process that inherited the handle
- A Windows kernel-mode driver (antivirus, filesystem filter)

The lock is **at the kernel level** — it persists across:
- Killing all user-mode processes
- Opening, truncating, or overwriting the file (only the lock byte at 1MB matters)
- Deleting via cmd.exe, PowerShell, or Python `os.remove()` (all blocked)

## Detection

```python
from gateway.status import is_gateway_runtime_lock_active
# Returns True when lock is held by SOMEONE (alive or orphaned)
is_gateway_runtime_lock_active()
```

```python
from gateway.status import acquire_gateway_runtime_lock
# Returns False when lock can't be acquired (orphaned)
acquire_gateway_runtime_lock()
```

The file may be writable (truncation works) but the lock byte stays locked.

## Solutions

### Solution 1: Reboot (Most Reliable)

The lock is a kernel object. Rebooting clears all kernel locks. After reboot:
```bash
# Verify lock is gone
hermes gateway run
```

This is the **only guaranteed fix** for truly orphaned kernel locks.

### Solution 2: Schedule Deletion on Reboot

If immediate reboot isn't possible, schedule the file for deletion on next boot:

```powershell
# Requires Administrator privileges
$path = "C:\Users\<user>\AppData\Local\hermes\gateway.lock"
$regPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager"
$valueName = "PendingFileRenameOperations"
$current = @()
$registry = Get-ItemProperty -Path $regPath -Name $valueName -ErrorAction SilentlyContinue
if ($registry) { $current = $registry.$valueName }
$current += "\??\$path"
$current += ""
Set-ItemProperty -Path $regPath -Name $valueName -Value $current
```

Verify: `Get-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager -Name PendingFileRenameOperations`

### Solution 3: Find and Kill the Holding Process

```powershell
# Find all processes with potentially high handle counts
Get-Process | Sort-Object HandleCount -Descending | Select-Object -First 20

# Kill all Python/Pythonw processes
Get-Process python, pythonw | Stop-Process -Force

# Kill bash.exe processes (may inherit handles)
Get-Process bash | Stop-Process -Force

# Kill hermes-agent.exe (desktop app may hold handles)
Get-Process hermes-agent | Stop-Process -Force
```

### Solution 4: Bypass via Alternative HERMES_HOME

Create a temporary HERMES_HOME with symlinks to the real config:

```bash
mkdir C:\tmp\hermes-home
# Copy config and .env
copy C:\Users\<user>\AppData\Local\hermes\config.yaml C:\tmp\hermes-home\
copy C:\Users\<user>\AppData\Local\hermes\.env C:\tmp\hermes-home\
# Run gateway with temp home
set HERMES_HOME=C:\tmp\hermes-home
hermes gateway run --replace
```

## Prevention

To avoid this in the future:
1. **Always use `--replace`** when starting the gateway to cleanly terminate
   old instances before acquiring the lock.
2. **Don't kill the gateway with Task Manager** — use `hermes gateway stop`
   or `scripts/fleet-deploy.py --stop`.
3. **Multiple Python interpreters** (Python311 + venv Python) can create
   conflicting locks. Stick to one Python for gateway processes.
4. The lock byte at 1MB prevents accidental corruption from short writes
   but makes orphan recovery harder — this is a known tradeoff.
5. **Use a separate lock file for Spacebar gateways.** The adapter's
   `_apply_spacebar_patches()` method (patch #16) redirects the gateway lock
   to `gateway.lock.spacebar` when Spacebar mode is active. This completely
   avoids the stale `gateway.lock` problem on Windows because the Spacebar
   lock file is only used by the Spacebar gateway and is never contaminated
   by old real-Discord gateway processes. No reboot required when switching
   between Spacebar and Discord gateway modes.
