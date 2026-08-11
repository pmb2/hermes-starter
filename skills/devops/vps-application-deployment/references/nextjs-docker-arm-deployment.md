# Next.js Docker Deployment on ARM VPS

Specific steps for deploying a Next.js 15 app on an Oracle Ampere A1 (ARM64) VPS.

## Transfer Project (Without rsync)

On Windows git-bash, rsync is unavailable. Use tar-over-SSH:

```bash
cd /path/to/project/
tar czf - --exclude='node_modules' --exclude='.next' --exclude='.git' \
  --exclude='*.log' --exclude='dist' . | \
  ssh -i ~/.ssh/key ubuntu@<vps-ip> \
  "tar xzf - -C /home/ubuntu/app/"
```

## Dockerfile (standalone output)

The `next.config.mjs` MUST set `output: 'standalone'`:

```javascript
const nextConfig = {
  output: 'standalone',
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  images: { unoptimized: true },
}
```

For the Dockerfile, see the main skill — the critical line for deps is:

```dockerfile
RUN npm install --legacy-peer-deps
```

Without `--legacy-peer-deps`, `react-day-picker@8.x` conflicts with `date-fns@4.x`.

## Missing Dependencies

If the build fails with `Module not found: Can't resolve 'leaflet'`:

```bash
# On the VPS (or fix in package.json before transfer):
cd /home/ubuntu/app/
npm pkg set dependencies.leaflet="^1.9.4"
npm pkg set dependencies."leaflet-defaulticon-compatibility"="^0.1.2"
npm pkg set dependencies."react-leaflet"="^4.2.1"
```

Then rebuild: `docker compose build app --no-cache`

## Build & Run

```bash
# Build the image
docker compose build app --no-cache

# Start all services
docker compose up -d

# Verify
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
docker compose logs -f app
```

## Caddy Reverse Proxy

Caddy runs on the HOST, not in Docker. Install it system-wide:

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
  sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
  sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

Caddyfile (`/etc/caddy/Caddyfile`):

```
your-domain.com {
    reverse_proxy 127.0.0.1:3000
}
```

The `app` container exposes `3000:3000` — accessible as `127.0.0.1:3000` on the host.

```bash
sudo systemctl reload caddy
```

## DNS

1. Set up A record at your DNS provider pointing to the VPS public IP
2. Caddy auto-provisions Let's Encrypt TLS once DNS resolves
3. Verify: `curl -v https://your-domain.com`

## Env File (.env.production)

```env
NEXT_PUBLIC_APP_URL=https://your-domain.com
NEXT_PUBLIC_APP_NAME=MyApp
NODE_ENV=production
```

Place in the project root alongside the Dockerfile. Reference in docker-compose.yml:

```yaml
services:
  app:
    env_file: .env.production
```

## Limitations on ARM VPS

- All Docker images must have ARM64 builds. Most official images do (node, postgres, redis, nginx).
- Some native npm packages with C++ addons may need `--build-from-source`. Prefer packages with prebuilt ARM64 binaries.
- `canvaskit`, `sharp`, `isolated-vm` are known to have ARM64 prebuilds.
