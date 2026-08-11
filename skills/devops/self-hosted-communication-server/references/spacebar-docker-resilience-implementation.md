# Spacebar Docker Resilience Implementation (May 2026)

How the 5-layer Windows Docker resilience pattern was applied to the Spacebar deployment at `spacebar.your-domain.example`.

## Project Layout

```
${MY_REPOS}\Documents\github\spacebar\
├── docker-compose.yml       # Self-contained: postgres + spacebar
├── docker-start.bat         # Windows startup script
├── .env                     # Postgres credentials (git-ignored)
├── config.production.json   # Production Spacebar config
├── Dockerfile               # Multi-stage Node.js build
└── .dockerignore
```

## Layer 1: Container Restart Policies

Both services use `restart: unless-stopped`:
- **postgres** (`spacebar-postgres`): `image: postgres:16-alpine` with healthcheck
- **spacebar**: custom Dockerfile build with healthcheck pinging `http://localhost:3001/api/v9/gateway`

Spacebar's `depends_on` waits for postgres to be healthy.

## Layer 2: Self-Contained Compose

The original compose file referenced postgres as an external service — the `depends_on` pointed to a service that didn't exist in the same file. Fixed by adding postgres inline:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: spacebar-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-spacebar}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB:-spacebar}
    volumes:
      - spacebar_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-spacebar} -d ${POSTGRES_DB:-spacebar}"]
    networks:
      - backend_edge

networks:
  backend_edge:
    external: true
    name: backend_edge
```

The `backend_edge` network remains external — it's shared with Traefik (which handles SSL/Let's Encrypt for `spacebar.your-domain.example`).

## Layer 3: Docker Desktop Auto-Start

Docker Desktop.exe was already in `HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run` pointing to `C:\Program Files\Docker\Docker\Docker Desktop.exe`. The `com.docker.service` Windows service was set to Manual (stopped) but Docker Desktop manages the daemon internally — its startup folder entry is sufficient.

## Layer 4: Startup Folder Shortcut

Created `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Spacebar.lnk`:

```powershell
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath('Startup') + '\Spacebar.lnk')
$Shortcut.TargetPath = '${MY_REPOS}\Documents\github\spacebar\docker-start.bat'
$Shortcut.WorkingDirectory = '${MY_REPOS}\Documents\github\spacebar'
$Shortcut.WindowStyle = 7
$Shortcut.Description = 'Spacebar Docker stack — auto-start on Windows boot'
$Shortcut.Save()
```

The `docker-start.bat` script:
1. Changes to the project directory
2. Checks if Docker is running — launches Desktop if needed (30s wait)
3. Runs `docker compose -f docker-compose.yml --env-file .env up -d`

## Layer 5: Hermes Cron Heartbeat

```bash
cronjob action=create \
  name="Spacebar heartbeat" \
  schedule="every 5m" \
  toolsets=["terminal"] \
  workdir="${MY_REPOS}\Documents\github\spacebar" \
  prompt="Check if the Spacebar Docker stack is running. If any container is missing or unhealthy, restart the stack. If Docker Desktop isn't running, launch it first and wait 30s."
```

Checks every 5 minutes for `spacebar-postgres` and `spacebar` container health. Self-heals on failure.

## Production Config Highlights

Config at `config.production.json`:
- Registration **disabled** (`register.disabled: true`)
- Password **required** (min 8 chars)
- Rate limiting **enabled**
- WebSocket gateway: `wss://spacebar.your-domain.example/`
- API: `https://spacebar.your-domain.example/api/v9`
- CDN: `https://spacebar.your-domain.example/`
- Traefik handles SSL with Let's Encrypt via docker labels
