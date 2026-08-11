#!/usr/bin/env python3
"""
Stealth Browser Watchdog — Ensures Camoufox browser is running.
Reads the bash script and pipes to bash via stdin to avoid MSYS path translation.
Created June 21, 2026 — replaced a no_agent cron that errored every 30m due to
MSYS backslash stripping when cron passed C:\Users\... paths to bash.

Usage in cron: cronjob(action='update', job_id='...', script='watchdog-browser.py')
"""
import subprocess
import sys
import os
import json

SCRIPT_PATH = r"${USER_HOME}\AppData\Local\hermes\scripts\start-stealth-browser.sh"
CAMOFOX_URL = "http://localhost:9377"

def check_health():
    try:
        import urllib.request
        resp = urllib.request.urlopen(f"{CAMOFOX_URL}/health", timeout=5)
        data = json.loads(resp.read())
        engine = data.get("engine", "?")
        tabs = data.get("activeTabs", "?")
        print(f"Camofox already running: engine={engine}, tabs={tabs}")
        return True
    except Exception:
        return False

def main():
    if check_health():
        sys.exit(0)

    if not os.path.exists(SCRIPT_PATH):
        print(f"ERROR: Script not found at {SCRIPT_PATH}")
        sys.exit(1)

    with open(SCRIPT_PATH, 'r', newline='\n') as f:
        script_content = f.read()

    print(f"Starting stealth browser via bash stdin...")
    result = subprocess.run(
        ["bash", "-s"],
        input=script_content.encode("utf-8"),
        capture_output=True,
        text=False,
        timeout=60
    )

    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")

    if stdout:
        print(stdout[:2000])
    if stderr:
        print(stderr[:1000])

    if check_health():
        print("Stealth browser is running.")
        sys.exit(0)
    else:
        print(f"Script failed (exit {result.returncode}) or Camofox didn't start.")
        sys.exit(1)

if __name__ == "__main__":
    main()
