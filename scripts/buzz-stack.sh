#!/bin/bash
# Buzz Relay + Hermes Integration — Start/Status/Stop
# Usage: ./buzz-stack.sh [start|stop|status|setup]

BUZZ_DIR="${USER_HOME}/buzz"
COMPOSE_DIR="$BUZZ_DIR/deploy/compose"
BUZZ_RELAY_PORT=3000

cmd=${1:-status}

case "$cmd" in
  start)
    echo "===== Starting Buzz Stack ====="
    cd "$COMPOSE_DIR"
    docker compose up -d relay postgres redis minio 2>&1 | tail -3
    echo "Waiting for relay..."
    for i in $(seq 1 12); do
      sleep 2
      if curl -s -o /dev/null -w "" http://localhost:$BUZZ_RELAY_PORT/ 2>/dev/null; then
        echo "✓ Buzz relay running on ws://localhost:$BUZZ_RELAY_PORT"
        exit 0
      fi
    done
    echo "✗ Relay not ready after 30s — check 'docker logs buzz-prod-relay-1'"
    ;;
    
  stop)
    echo "===== Stopping Buzz Stack ====="
    cd "$COMPOSE_DIR"
    docker compose down 2>&1 | tail -3
    echo "✓ Buzz stack stopped"
    ;;
    
  status)
    echo "===== Buzz Stack Status ====="
    cd "$COMPOSE_DIR" 2>/dev/null
    docker ps --filter "name=buzz-prod" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "No buzz containers running"
    echo ""
    if curl -s -o /dev/null -w "Relay: HTTP %{http_code}\n" http://localhost:$BUZZ_RELAY_PORT/ 2>/dev/null; then
      echo "✓ Relay reachable"
    else
      echo "✗ Relay NOT reachable"
    fi
    ;;
    
  setup)
    echo "===== Setup Buzz Channels & Keys ====="
    cd "${HERMES_HOME}/scripts"
    python create_buzz_channels.py
    python update_buzz_env.py
    echo "✓ Buzz setup complete"
    echo "  Keys: buzz_keys.json (47 profiles)"
    echo "  Channels: buzz_channels.json"
    echo "  Profile .env files updated"
    ;;
    
  test)
    echo "===== Test Buzz Connection ====="
    cd "${HERMES_HOME}/scripts"
    python -c "
from buzz_client import BuzzClient, load_profile_key
client = BuzzClient(load_profile_key('dev-lead'))
if client.connect():
    eid = client.send_channel_message('engineering', 'Buzz bridge test ✓')
    client.close()
    print('✓ Buzz operational!' if eid else '✗ Message rejected')
else:
    print('✗ Auth failed')
"
    ;;
    
  *)
    echo "Usage: $0 {start|stop|status|setup|test}"
    ;;
esac
