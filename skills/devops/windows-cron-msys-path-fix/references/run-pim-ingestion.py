#!/usr/bin/env python3
"""
PIM Ingestion & Sync wrapper — LLM-driven alternative.
Reads the bash ingestion script and pipes to bash via stdin.
Created June 21, 2026 — replaced a paused no_agent cron job that failed due
to environment dependencies in the cron sandbox (E: drive, python PATH,
Firefox portable path).

NOTE: This wrapper works but the underlying script has environment deps that
don't resolve in the cron sandbox. For scripts with such dependencies, convert
the cron job from no_agent to LLM-driven instead (see strategy below).

Strategy 1: Python wrapper + stdin piping (this file)
  - Works when the bash script itself is self-contained (no env deps)
  - Fails when script needs: secondary drives, non-default PATH entries,
    specific user profile files (Firefox cookies), or GUI processes

Strategy 2: LLM-driven cron job (recommended for env-dependent scripts)
  - Create a cron job WITHOUT no_agent=True
  - The agent inherits the full Hermes environment (PATH, drives, python)
  - Use terminal() in the prompt to call the script directly
  - The agent can diagnose failures and retry
  - Example:
    cronjob(
        action='create',
        name='PIM Ingestion -- LLM-driven every 4h',
        prompt='Run the ingestion script with terminal(): bash ${USER_HOME}/...',
        schedule='every 240m',
        enabled_toolsets=['terminal', 'file', 'web']
    )
"""
import subprocess
import sys
import os

SCRIPT_PATH = r"${USER_HOME}\AppData\Local\hermes\scripts\ingest-chatgpt-grok.sh"

def main():
    if not os.path.exists(SCRIPT_PATH):
        print(f"ERROR: Script not found at {SCRIPT_PATH}")
        sys.exit(1)

    with open(SCRIPT_PATH, 'r', newline='\n') as f:
        script_content = f.read()

    print(f"Starting PIM ingestion ({os.path.getsize(SCRIPT_PATH)} bytes)...")

    result = subprocess.run(
        ["bash", "-s"],
        input=script_content.encode("utf-8"),
        capture_output=True,
        text=False,
        timeout=600
    )

    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")

    if stdout:
        lines = stdout.splitlines()
        if len(lines) > 60:
            print("\n".join(lines[:10]))
            print(f"[... {len(lines) - 60} lines omitted ...]")
            print("\n".join(lines[-50:]))
        else:
            print(stdout)
    if stderr:
        stderr_lines = stderr.splitlines()
        if stderr_lines:
            print(f"STDERR ({len(stderr_lines)} lines, last 20):")
            print("\n".join(stderr_lines[-20:]))

    if result.returncode == 0:
        print("PIM ingestion completed successfully.")
        sys.exit(0)
    elif result.returncode == 124:
        print("PIM ingestion timed out (10 min). Will retry next cycle.")
        sys.exit(0)
    else:
        print(f"PIM ingestion failed with exit code {result.returncode}")
        sys.exit(result.returncode)

if __name__ == "__main__":
    main()
