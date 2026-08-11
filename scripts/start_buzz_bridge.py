#!/usr/bin/env python3
"""Buzz Bridge Wrapper - keeps the bridge running, logs to file."""
import subprocess, sys, time
from pathlib import Path

BRIDGE = Path(r"${USER_HOME}\AppData\Local\hermes\scripts\buzz_agent_bridge.py")
LOG = Path(r"${USER_HOME}\AppData\Local\hermes\scripts\bridge.log")
PYTHON = sys.executable

def log(msg):
    t = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{t}] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def main():
    delay = 1
    while True:
        log("Starting bridge...")
        try:
            r = subprocess.run([PYTHON, str(BRIDGE)], timeout=86400, capture_output=True, text=True)
            log(f"Exited code={r.returncode}, stdout={len(r.stdout)}c, stderr={len(r.stderr)}c")
            if r.stdout:
                with open(LOG, "a") as f:
                    f.write(r.stdout[-1000:] + "\n")
            if r.stderr:
                with open(LOG, "a") as f:
                    f.write("STDERR: " + r.stderr[-1000:] + "\n")
        except subprocess.TimeoutExpired:
            log("24h timeout - restarting")
        except Exception as e:
            log(f"Error: {e}")
        
        log(f"Restart in {delay}s...")
        time.sleep(delay)
        delay = min(delay * 2, 30)

if __name__ == "__main__":
    main()
