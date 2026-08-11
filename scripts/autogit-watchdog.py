#!/usr/bin/env python3
"""autogit-watchdog.py — periodic autogit ship for all opted-in repos.
Called as a no_agent cron job — stdout is delivered verbatim."""

import subprocess
import sys
import os

REPOS = [
    r"${MY_REPOS}\Documents\github\yt-animations",
    r"${MY_REPOS}\Documents\github\agent-fleet",
    r"${MY_REPOS}\Documents\github\spacebar",
    r"${MY_REPOS}\Documents\github\auto-resume",
    r"${MY_REPOS}\Documents\github\Fermi",
    r"${MY_REPOS}\Documents\github\git-mcp",
]

AUTOGIT = r"${USER_HOME}\AppData\Roaming\npm\node_modules\@davidondrej\autogit\index.js"
AUTOGIT_CMD = ["node", AUTOGIT]
GIT = "git"

def main():
    shipped = 0
    errors = []
    for repo in REPOS:
        config_file = os.path.join(repo, ".autogit.json")
        if not os.path.isfile(config_file):
            continue
        try:
            orig_dir = os.getcwd()
            os.chdir(repo)
            # Check for uncommitted changes
            result = subprocess.run(
                [GIT, "status", "--porcelain"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                errors.append(f"{repo}: git status failed")
                continue
            if not result.stdout.strip():
                continue  # nothing to ship
            # Ship it
            ship = subprocess.run(
                AUTOGIT_CMD + ["ship"],
                capture_output=True, text=True, timeout=60
            )
            if ship.returncode == 0:
                shipped += 1
                print(f"✓ {os.path.basename(repo)}: shipped")
            else:
                msg = ship.stderr.strip() or ship.stdout.strip()
                print(f"⚠ {os.path.basename(repo)}: {msg[:200]}")
        except subprocess.TimeoutExpired:
            errors.append(f"{repo}: timed out")
        except Exception as e:
            errors.append(f"{repo}: {e}")
        finally:
            os.chdir(orig_dir)

    if shipped == 0 and not errors:
        print("autogit-watchdog: nothing to ship")

    for err in errors:
        print(f"✗ {err}", file=sys.stderr)

if __name__ == "__main__":
    main()
