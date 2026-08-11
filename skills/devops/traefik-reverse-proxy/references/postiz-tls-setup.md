# Adding Postiz to Traefik (June 26, 2026)

## Goal
Serve Postiz (localhost:4007 Docker container) at `https://sg.your-domain.example` with a Let's Encrypt cert.

## Config Changes

### 1. File Provider Router + Service

In `${MY_REPOS}\Documents\github\n8n\data\traefik\config\docker-fallback.yml`:

```yaml
http:
  routers:
    # Added as a new router entry:
    postiz:
      rule: 'Host(`sg.your-domain.example`)'
      entryPoints:
        - 'websecure'
      service: 'postiz'
      tls:
        certresolver: 'letsencrypt'

  services:
    # Added as a new service entry:
    postiz:
      loadBalancer:
        servers:
          - url: 'http://host.docker.internal:4007'
        passHostHeader: true
```

**Why `host.docker.internal:4007` instead of `postiz:5000`?**  
The Postiz container is on network `postiz-app_postiz-network`. Traefik is on networks `backend_core` + `backend_edge`. Since they're on different Docker networks, container name resolution doesn't work. `host.docker.internal` reaches the Docker host's port 4007, which Docker forwards to the Postiz container's port 5000.

### 2. ACME Challenge: HTTP-01 → TLS-ALPN-01

In `${MY_REPOS}\Documents\github\n8n\docker-compose.yml`:

```yaml
command:
  # Removed:
  # - --certificatesresolvers.letsencrypt.acme.httpchallenge=true
  # - --certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web
  # Added:
  - --certificatesresolvers.letsencrypt.acme.tlschallenge=true
```

**Why?** The `web` entrypoint has `http.redirections.entryPoint.to=websecure` which redirects all HTTP to HTTPS. This intercepts the HTTP-01 ACME challenge before Traefik can serve the challenge file, causing Let's Encrypt to get a 404 and fail.

### 3. Restart

```bash
cd ${MY_REPOS}\Documents\github\n8n
docker compose rm -sf traefik
docker compose create traefik
docker compose start traefik
```

## Verification

```bash
curl -sk https://sg.your-domain.example/auth        # → 200, returns Postiz login page
curl -skI http://sg.your-domain.example/             # → 308 → https://sg.your-domain.example/
echo | openssl s_client -connect sg.your-domain.example:443 -servername sg.your-domain.example | openssl x509 -noout -text
```

## Certificate Details
- **Subject**: CN=sg.your-domain.example
- **Issuer**: Let's Encrypt (CN=YR2)
- **Key size**: 4096 bit RSA
- **Validity**: Jun 26 → Sep 24, 2026 (89 days)
- **Auto-renewal**: Handled by Traefik's ACME provider

## Postiz Env Vars for Reverse Proxy

When Postiz is served behind a reverse proxy at a public URL instead of `localhost:4007`,
the following environment variables in `${USER_HOME}\postiz-app\docker-compose.yaml` **must** be
updated so the frontend JS makes API calls to the correct origin:

```yaml
MAIN_URL: 'https://sg.your-domain.example'
FRONTEND_URL: 'https://sg.your-domain.example'
NEXT_PUBLIC_BACKEND_URL: 'https://sg.your-domain.example/api'
```

**Without this fix**, the browser loads the page from `https://sg.your-domain.example` but
the frontend tries to `fetch()` from `http://localhost:4007/api/…` (the build-time default).
From any machine other than the Docker host, `localhost` resolves to the user's own machine,
producing CORS errors:

```
Cross-Origin Request Blocked: … http://localhost:4007/api/auth/oauth/GOOGLE
```

**Why this works**: Postiz's `(provider)/layout.tsx` reads `process.env.NEXT_PUBLIC_BACKEND_URL`
at **request time** on the server and passes it as a React prop to `VariableContextComponent`.
The client-side JS references the value from the React context (not a baked-in literal)
via the `useVariables()` hook. A container restart (`docker compose down postiz && docker compose create postiz && docker compose start postiz`) is sufficient — no rebuild needed.

After changing the env vars, verify with:
```bash
# Check server-rendered HTML has correct URL
curl -sk https://sg.your-domain.example/auth | grep -oP 'backendUrl\\":[^,]*'
# Should show: backendUrl":"https://sg.your-domain.example/api"
```
