#!/usr/bin/env bash
# firefox-watchdog.sh — Self-healing Firefox BiDi watchdog
# Silent when healthy (exit 0, no output). Reports only on restarts.
# Auto-repairs by finding firefox-health.py in multiple fallback paths.
# Uses Windows-native paths to avoid MSYS/Python path mangling.

SCRIPT_DIR_WIN="$(cd "$(dirname "$0")" && pwd -W 2>/dev/null || cygpath -w "$(dirname "$0")" 2>/dev/null || echo "$(dirname "$0")")"
HEALTH_SCRIPT=""

FALLBACK_PATHS=(
    "${SCRIPT_DIR_WIN}/firefox-health.py"
    "${SCRIPT_DIR_WIN}/../firefox-health.py"
    "${USER_HOME}/AppData/Local/hermes/scripts/firefox-health.py"
    "${MY_REPOS}/Documents/github/_project/scripts/firefox-health.py"
)

# Find the health script in any fallback path
for path in "${FALLBACK_PATHS[@]}"; do
    if [ -f "$path" ]; then
        HEALTH_SCRIPT="$path"
        break
    fi
done

# If health script not found, try to copy it from source
if [ -z "$HEALTH_SCRIPT" ]; then
    SOURCE="${MY_REPOS}/Documents/github/_project/scripts/firefox-health.py"
    if [ -f "$SOURCE" ]; then
        cp "$SOURCE" "${SCRIPT_DIR_WIN}/firefox-health.py"
        HEALTH_SCRIPT="${SCRIPT_DIR_WIN}/firefox-health.py"
        echo "[FF-HEAL] Self-repaired: copied firefox-health.py from source"
    else
        echo "[FF-HEAL] CRITICAL: firefox-health.py not found in any location"
        exit 1
    fi
fi

# Run the health check in watchdog mode using Windows path
python "$HEALTH_SCRIPT" watchdog
