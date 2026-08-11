# Docker + Next.js Deployment Reference

## Peer Dependency Conflicts

**Common issue:** `react-day-picker@^8.x.x` requires `date-fns@^2.28.0 || ^3.0.0` but the project has `date-fns@^4.x.x`.

**Fix:** Use `--legacy-peer-deps` in the Dockerfile's npm install step:
```dockerfile
RUN npm install --legacy-peer-deps
```

## Required next.config.mjs for Docker

For a standalone Docker build, `next.config.mjs` MUST include:
```javascript
const nextConfig = {
  output: 'standalone',
  // ... other config
}
```

Without `output: 'standalone'`, there is no `.next/standalone/` directory for the Docker build to copy.

## Missing Package Dependencies

If a build fails with `Module not found: Can't resolve '<package>'`, check if the code imports a package not listed in `package.json`. Common culprits:
- `leaflet` / `react-leaflet` / `leaflet-defaulticon-compatibility` — used by map components
- `@types/leaflet` — dev dependency for TypeScript projects

Fix:
```bash
npm pkg set dependencies.leaflet="^1.9.4"
npm pkg set dependencies.react-leaflet="^4.2.1"
```

## Multi-stage Build

The standard pattern uses three stages:
1. **deps** — Install all dependencies
2. **builder** — Build the Next.js app
3. **runner** — Minimal production image with standalone output
