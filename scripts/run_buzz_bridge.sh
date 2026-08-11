#!/usr/bin/env bash
# Buzz Agent Bridge — persistent runner (DEPRECATED in favor of buzz_watchdog.py)
#
# NOTE: This wrapper is no longer used by the cron job. The cron job now runs
# buzz_watchdog.py (no_agent=true, every 15m) which spawns the bridge DETACHED
# so the cron 3-minute hard interrupt cannot kill it. This script is kept for
# manual foreground use only — DO NOT launch it from cron (it caused the
# duplicate-bridge explosion on 2026-08-01 where 6 bridge instances ran at once).
#
# Manual use:
#   bash run_buzz_bridge.sh
PYTHON="${USER_HOME}/AppData/Local/Programs/Python/Python311/python.exe"
SCRIPT="${USER_HOME}/AppData/Local/hermes/scripts/buzz_agent_bridge.py"
LOG="${USER_HOME}/AppData/Local/hermes/logs/buzz_bridge.log"

mkdir -p "$(dirname "$LOG")"

echo "=== Buzz Bridge (manual run) started $(date -Iseconds) ===" >> "$LOG"

# Single foreground run — no respawn loop. Use buzz_watchdog.py for persistence.
exec "$PYTHON" -u "$SCRIPT" >> "$LOG" 2>&1
