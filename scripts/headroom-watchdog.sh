#!/bin/bash
# Headroom Proxy Watchdog - starts if not running
# Runs every 15min via cron

PORT=8787

if ! netstat -ano 2>/dev/null | grep -q ":$PORT .* LISTENING"; then
  # Proxy is down - restart it
  cd ~/AppData/Local/hermes || true
  headroom proxy --host 127.0.0.1 --port $PORT &
  echo "Headroom proxy restarted on port $PORT at $(date)"
else
  echo "Headroom proxy OK on port $PORT"
fi
