#!/usr/bin/env bash
# Pulse Check Script — Agent Heartbeat Monitor
# Usage: ./pulse-check.sh <agent-name>
# Checks gateway status, reads recent logs, appends to PULSE.md
# Designed for cron: no_agent=true mode — output delivered verbatim

set -euo pipefail

NAME="${1:-}"
if [ -z "$NAME" ]; then
  echo "Usage: pulse-check.sh <agent-name>"
  exit 1
fi

HERMES_HOME="$HOME/AppData/Local/hermes"
PROFILE_DIR="$HERMES_HOME/profiles/$NAME"
LOG_FILE="$HERMES_HOME/logs/gateway-${NAME}.log"
PULSE_FILE="$PROFILE_DIR/PULSE.md"
NOW=$(date -u +"%Y-%m-%d %H:%M UTC")

# ─── Status Check ───
PID=""
STATUS="🔴 Offline"
UPTIME="N/A"
LAST_LOG="No logs found"

if pgrep -f "hermes.*profile.*$NAME.*gateway" > /dev/null 2>&1; then
  PID=$(pgrep -f "hermes.*profile.*$NAME.*gateway" | head -1)
  STATUS="🟢 Online"
  # Rough uptime from process start
  if [ -d "/proc/$PID" ]; then
    START_SEC=$(stat -c %Y /proc/$PID 2>/dev/null || echo 0)
    NOW_SEC=$(date +%s)
    UPTIME_SEC=$((NOW_SEC - START_SEC))
    if [ $UPTIME_SEC -gt 86400 ]; then
      UPTIME="$((UPTIME_SEC / 86400))d $(((UPTIME_SEC % 86400) / 3600))h"
    elif [ $UPTIME_SEC -gt 3600 ]; then
      UPTIME="$((UPTIME_SEC / 3600))h $(((UPTIME_SEC % 3600) / 60))m"
    else
      UPTIME="$((UPTIME_SEC / 60))m"
    fi
  fi
fi

# ─── Recent Logs ───
if [ -f "$LOG_FILE" ]; then
  LAST_LOG=$(tail -3 "$LOG_FILE" 2>/dev/null || echo "Cannot read log")
fi

# ─── SOUL.md check ───
HAS_SOUL="❌ Missing"
[ -f "$PROFILE_DIR/SOUL.md" ] && HAS_SOUL="✅ Present"

# ─── Config check ───
CONFIG_STATUS="❌ Missing"
[ -f "$PROFILE_DIR/config.yaml" ] && CONFIG_STATUS="✅ Present"

# ─── Build Pulse Entry ───
PULSE=$(cat <<PULSE
## Pulse @ ${NOW}

- **Status**: ${STATUS}
- **PID**: ${PID:-N/A}
- **Uptime**: ${UPTIME}
- **SOUL.md**: ${HAS_SOUL}
- **Config**: ${CONFIG_STATUS}
- **Last Log**: \`\`\`
${LAST_LOG}
\`\`\`

---
PULSE
)

# ─── Append to PULSE.md ───
mkdir -p "$PROFILE_DIR"

if [ ! -f "$PULSE_FILE" ]; then
  cat > "$PULSE_FILE" <<HEADER
# PULSE.md — ${NAME}

> Continuous heartbeat log for the ${NAME} agent.
> Each entry records status, uptime, and recent activity.
> Appended automatically by pulse-check.sh every cycle.

HEADER
fi

echo "$PULSE" >> "$PULSE_FILE"

# ─── Output (delivered via cron) ───
echo "━━━ Pulse: ${NAME} @ ${NOW} ━━━"
echo "${STATUS}  PID: ${PID:-N/A}  Uptime: ${UPTIME}"
echo ""
echo "Recent log:"
echo "${LAST_LOG}"
echo ""
echo "PULSE.md entries: $(grep -c '^## Pulse' "$PULSE_FILE" 2>/dev/null || echo 0)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
