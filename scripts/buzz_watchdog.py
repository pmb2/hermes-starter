#!/usr/bin/env python3
"""Buzz Bridge Watchdog — no_agent cron script.

Checks whether the Buzz Agent Bridge is alive (via PID file + process
liveness). If it's dead, spawns it DETACHED so the cron 3-minute hard
interrupt cannot kill it. Prints a status line ONLY when it took action
(empty stdout = silent = no delivery), per the no_agent watchdog pattern.

Cron: script=buzz_watchdog.py, no_agent=true, every 15m
"""
import os, subprocess, sys, time
from pathlib import Path

HERMES_HOME = Path(r"${USER_HOME}\AppData\Local\hermes")
SCRIPTS = HERMES_HOME / "scripts"
LOGS = HERMES_HOME / "logs"
BRIDGE = SCRIPTS / "buzz_agent_bridge.py"
PIDFILE = LOGS / "buzz_bridge.pid"
LOG = LOGS / "buzz_bridge.log"

PYTHON = r"${USER_HOME}\AppData\Local\Programs\Python\Python311\python.exe"
if not Path(PYTHON).exists():
    PYTHON = sys.executable


def is_alive(pid: int) -> bool:
    """Windows-safe process liveness check."""
    if not pid or pid <= 0:
        return False
    try:
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        kernel32 = ctypes.windll.kernel32
        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            return False
        try:
            # 0x103 = STILL_ACTIVE
            exit_code = ctypes.c_ulong()
            ok = kernel32.GetExitCodeProcess(h, ctypes.byref(exit_code))
            kernel32.CloseHandle(h)
            return bool(ok) and exit_code.value == 0x103
        except Exception:
            kernel32.CloseHandle(h)
            return False
    except Exception:
        # Fallback: tasklist check
        try:
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                                 capture_output=True, text=True, timeout=10).stdout
            return str(pid) in out and "No tasks" not in out
        except Exception:
            return False


def spawn_bridge():
    """Launch the bridge fully detached (new process group, no console)."""
    LOGS.mkdir(parents=True, exist_ok=True)
    log_handle = open(LOG, "a", encoding="utf-8")
    flags = (
        subprocess.CREATE_NEW_PROCESS_GROUP
        | getattr(subprocess, "DETACHED_PROCESS", 0)
        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )
    proc = subprocess.Popen(
        [PYTHON, "-u", str(BRIDGE)],
        cwd=str(SCRIPTS),
        stdout=log_handle,
        stderr=log_handle,
        stdin=subprocess.DEVNULL,
        creationflags=flags,
        close_fds=True,
    )
    return proc


def main():
    pid = None
    if PIDFILE.exists():
        try:
            pid = int(PIDFILE.read_text().strip())
        except Exception:
            pid = None

    if pid and is_alive(pid):
        # Bridge is healthy — stay silent (no_agent: empty stdout = no delivery)
        return

    # Bridge dead or missing — spawn it
    try:
        proc = spawn_bridge()
        time.sleep(2)
        alive = proc.poll() is None
        if alive:
            # Record actual spawned PID
            PIDFILE.write_text(str(proc.pid))
            print(f"[buzz-watchdog] Bridge was down — restarted (pid {proc.pid}).")
        else:
            print(f"[buzz-watchdog] Bridge spawn FAILED (exit {proc.returncode}). Check {LOG}")
    except Exception as e:
        print(f"[buzz-watchdog] ERROR spawning bridge: {e}")


if __name__ == "__main__":
    main()
