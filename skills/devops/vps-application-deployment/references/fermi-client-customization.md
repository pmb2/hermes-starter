# Fermi Web Client — the operator Customization

This reference documents the complete customization of the Fermi (Harmony) web chat client for the operator branding, deployed at `https://gc.your-domain.example`.

## Architecture

```
Browser → gc.your-domain.example → Caddy (Docker) → fermiclient:8081 (Node.js)
                      discy.your-domain.example → Caddy → spacebar-api:3100 (Docker)
```

- **Fermi client source:** `/opt/fermi/` on VPS (129.153.156.190)
- **Server runtime:** Node.js, `node dist/index.js` on port 8081
- **Git remote:** `https://github.com/pmb2/Fermi.git` (HTTPS, no SSH key)
- **Build:** `npm run build` (SWC bundler — compiles TS from `src/` to `dist/`)

## Key Files Modified

| File | Purpose | Change |
|------|---------|--------|
| `src/index.ts` | Server routing | Root `/` → 302 redirect to `/channels/@me` |
| `src/webpage/logo.svg` | App logo | Replaced Fermi logo with custom SVG |
| `src/webpage/favicon.ico` | Browser favicon | Replaced with SVG-based favicon |
| `src/webpage/app.html` | Loading screen | Title, meta, logo size, theme color |
| `src/webpage/index.html` | Landing page | Full rebrand (Fermi → the operator) |
| `translations/en.json` | All i18n strings | 19 visible strings updated |
| `src/webpage/instances.json` | Server list | Added `image: "/logo.svg"`, updated name/desc |
| `src/webpage/manifest.json` | PWA manifest | Name, short_name, description |
| Plus: invite/login/register/reset/404/template/audio/oauth pages | Individual HTML | Title, meta tags updated |

### CRITICAL: Dual Directory Pattern

Fermi has TWO copies of the webpage directory that must BOTH be updated:

| Directory | Purpose | Updated automatically? |
|-----------|---------|----------------------|
| `src/webpage/` | Source files (pre-build) | No |
| `dist/webpage/` | Runtime files (what Node serves) | No |

The server loads files from `dist/webpage/` at runtime using a recursive file-walk cache. Changes to `src/webpage/` have no effect unless ALSO copied to `dist/webpage/`.

**Even worse: instances.json is loaded into Node.js memory at startup.** Changing the file in `dist/webpage/` is not enough — Fermi must be RESTARTED for new instances to appear in the login selector.

```bash
# Apply changes to BOTH directories
cp /opt/fermi/src/webpage/instances.json /opt/fermi/dist/webpage/instances.json
sed -i 's|old-text|new-text|g' /opt/fermi/src/webpage/app.html /opt/fermi/dist/webpage/app.html

# Restart Fermi for instances.json to take effect
kill $(pgrep -f 'node dist/index') 2>/dev/null
sleep 2
cd /opt/fermi && nohup node dist/index.js >> fermi.log 2>&1 &
```

### Pitfall — Only updating src/webpage/
The running server never sees changes to `src/webpage/`. Always VERIFY by curling the public URL — not by checking files on disk. If curl shows old content, you missed `dist/`.

## Custom SVG Logo

The logo is a **chat-bubble-with-wings motif** with:
- Deep purple (#6C3CE1) → vibrant teal (#00D4AA) gradient
- Stylized wing curves on each side (Hermes/messenger theme)
- Subtle "B" monogram integrated into the chat bubble
- 135.5×135.5 viewBox

## Known Issues

- **No SSH key on VPS** for GitHub — must use HTTPS + token auth for pushes
- **Server auto-restart not configured** — currently started manually; use `systemd` or a supervisor for production
- **Fermi upstream changes** may conflict with custom instances.json on `git pull --rebase`
- **dist rebuild is required** after any source change; `npm run build` handles this
