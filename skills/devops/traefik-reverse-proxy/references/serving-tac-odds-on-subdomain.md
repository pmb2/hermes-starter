# Serving TAC Odds on 25.your-domain.example

## Setup (July 2026)

- **App**: TAC Odds dashboard + API, running on `localhost:9091` (FastAPI/uvicorn, NOT in Docker)
- **Traefik**: Running in Docker, ports 80/443, Let's Encrypt TLS-ALPN-01
- **Config file**: `${MY_REPOS}\Documents\github\n8n\data\traefik\config\docker-fallback.yml`
- **Target URL pattern**: `http://host.docker.internal:9091` (service on host, not in Docker)

## Config Added

```yaml
# Under http.routers:
    tac-odds:
      rule: 'Host(`25.your-domain.example`)'
      entryPoints:
        - 'websecure'
      service: 'tac-odds'
      tls:
        certresolver: 'letsencrypt'

# Under http.services:
    tac-odds:
      loadBalancer:
        servers:
          - url: 'http://host.docker.internal:9091'
        passHostHeader: true
```

## Reload

File watch didn't pick up the change. Forced reload with:
```bash
docker kill -s HUP traefik
```

## DNS

Provider: `registrar-servers.com` (Namecheap)
Need A record: `25` → `74.76.35.96`
All existing subdomains (`auth`, `crm`, `n8n`, `sg`, etc.) already point to this IP.

## Verification

```bash
# Route check
docker exec traefik wget -q -O- http://localhost:8080/api/http/routers | python -c "import json,sys; data=json.load(sys.stdin); [print(r['name'],r['status']) for r in data if 'tac' in r['name'].lower()]"

# Full chain test
curl -sk --resolve "25.your-domain.example:443:127.0.0.1" https://25.your-domain.example/api/health
curl -sk --resolve "25.your-domain.example:443:127.0.0.1" https://25.your-domain.example/ | head -5

# Cert check
echo | openssl s_client -connect 127.0.0.1:443 -servername 25.your-domain.example 2>/dev/null | openssl x509 -noout -subject -issuer -dates
```

## Cert Status

- Issued by: Let's Encrypt YR2
- Subject: CN=25.your-domain.example
- Valid: Jul 9 – Oct 7, 2026
- Auto-renewed by Traefik
