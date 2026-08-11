# Fermi Client UI Customization & Server Route Patching

How to add new UI features to the Fermi client and patch Spacebar server route handlers.

## Architecture Overview

```
src/webpage/*.ts  (TypeScript source)
  → swc bundle (node buildnode.js → node build.js)
  → dist/webpage/index.js (single bundle, all .ts files compiled together)

Server: src/api/routes/.../*.ts
  → tsc -b
  → dist/api/ routes/.../*.js
```

There is NO separate `message.js` or `channel.js` in the built output — everything is bundled into `index.js` (client) or individual `*.js` per route (server).

## Fermi Client Customization

### Key Files

| File | Purpose |
|------|---------|
| `src/webpage/message.ts` | Message rendering, context menu, delete, edit, reactions |
| `src/webpage/channel.ts` | Channel state, message list (InfiniteScroller), permissions |
| `src/webpage/permissions.ts` | Guild-level permission checks (guild-scoped MANAGE_MESSAGES, etc.) |
| `src/webpage/rights.ts` | User-level rights checks (OPERATOR, MANAGE_MESSAGES, SELF_DELETE_MESSAGES) |
| `src/webpage/infiniteScroller.ts` | Virtual-scrolling message list with IntersectionObserver |
| `src/webpage/style.css` | All CSS for the client |
| `src/webpage/localuser.ts` | Global app state, user info (includes `this.rights` as Rights instance) |
| `src/webpage/index.ts` | **Node.js HTTP server** — NOT the client bundle. Serves static files, handles routing, redirects. Compiled separately by swc. |

### Two Separate Build Targets

**CRITICAL:** The Fermi project produces TWO compiled outputs from the same source tree:

1. **Client bundle** — `dist/webpage/index.js` (all `src/webpage/*.ts` files bundled into one JS file via swc.bundle)
2. **Node server** — `dist/index.js` (compiled from `src/index.ts` via swc.transformFile)

**These are built by different code paths in `build.ts`.** The `node build.js` command does BOTH, but the server file (`dist/index.js`) is compiled separately. A change to `src/index.ts` (routing, redirect, port) requires verification after build.

### Pitfall: 302 Redirect Lost After Full Build

When `src/index.ts` has a 302 redirect from `/` → `/channels/@me` (for skip-landing behavior), a full `npm run build` SHOULD compile it into `dist/index.js`. However this file is commonly out of date because the build has been observed to produce the old routing (serving `index.html` at `/` instead of redirecting).

**After any `npm run build`, VERIFY the redirect is present:**

```bash
grep -c "/channels/@me" dist/index.js
# Expected: 1 (or more if minified differently)
# If 0: the redirect was lost
```

**To rebuild `dist/index.js` manually:**

```bash
cd /opt/fermi
cat > ./rebuild_server.cjs << 'EOF'
const swc = require("@swc/core");
const fs = require("fs");
swc.transformFile("src/index.ts", {
  minify: true, sourceMaps: true, isModule: true,
  jsc: { minify: { mangle: false } }
}).then(r => {
  fs.writeFileSync("dist/index.js", r.code);
  if (r.map) fs.writeFileSync("dist/index.js.map", r.map);
  console.log("OK, has redirect:", r.code.includes("/channels/@me"));
}).catch(e => console.error(e));
EOF
node ./rebuild_server.cjs && rm ./rebuild_server.cjs
sudo systemctl restart fermi
```

### Message Lifecycle

1. Channel loads via `tryfocusinfinate()` → creates InfiniteScroller
2. InfiniteScroller calls `message.buildhtml()` → `message.generateMessage()`
3. `generateMessage()` creates a `div.messagediv` with avatar, username, content, attachments
4. `messageevents()` attaches swipe gestures (reply/thread drag) and sets `this.div`
5. `bindButtonEvent()` shows hover buttons (reply, emoji, edit, delete)
6. Messages are recycled by IntersectionObserver — removed when scrolled out of view

### Adding a UI Element to Every Message

**Pattern:** Modify `generateMessage()` in message.ts:

```typescript
div.innerHTML = "";
const myElement = document.createElement("div");
// ... configure ...
div.prepend(myElement);
const build = document.createElement("div");
```

To preserve state across scroll recycling, use a static Map/Set:

```typescript
static selectedMessages = new Set<Message>();
// In generateMessage():
if (MyClass.selectedMessages.has(this)) {
    myElement.classList.add("active");
}
```

### Permission/Rights Checks for UI

- **Guild-level permissions:** `this.channel.hasPermission("MANAGE_MESSAGES")` — checks Permissions.ts
- **User-level rights:** `this.localuser.rights.hasPermission("OPERATOR")` — checks Rights.ts
- **Self-check:** `this.author === this.localuser.user`

### canDelete() Pattern

```typescript
canDelete() {
    return this.channel.hasPermission("MANAGE_MESSAGES")
        || this.author === this.localuser.user
        || this.localuser.rights.hasPermission("OPERATOR");
}
```

The OPERATOR check allows superusers to delete in DMs where hasPermission returns false.

### Build & Deploy

```bash
npm install && node buildnode.js && node build.js
tar czf dist.tar.gz dist/
scp dist.tar.gz user@vps:/tmp/
ssh user@vps "cd /opt/fermi && rm -rf dist && tar xzf /tmp/dist.tar.gz"
# Then: rebuild dist/index.js redirect + restore branding (see pitfall below) + restart
```

### Critical: Branding Destroyed on Full Dist Deploy

The VPS Fermi instance often has custom branding (instances.json, HTML titles, logos, translations) that exist ONLY on the VPS. Running `rm -rf dist && tar xzf dist.tar.gz` obliterates them.

**Before deploying a new dist build, ALWAYS:**

1. **Check for uncommitted changes on VPS:**
   ```bash
   ssh user@vps "cd /opt/fermi && git status --short"
   ```
   Modified/untracked files = customizations to preserve.

2. **Backup custom files**: instances.json, index.html, app.html, login.html, register.html, reset.html, invite.html, 404.html, template.html, manifest.json, translations/en.json, backus-*.*, favicon.*, logo.*

3. **Deploy new dist**

4. **Restore branding** from backup

5. **Rebuild dist/index.js** with 302 redirect (see above)

6. **Restart**: `sudo systemctl restart fermi`

7. **Commit VPS customizations to survive future deploys:**
   ```bash
   ssh user@vps "cd /opt/fermi && git add <files> && git commit -m '..."'
   # git push will FAIL on VPS (no creds). Pull locally then push.
   ```

### CSS Changes

Add styles to `src/webpage/style.css`, then rebuild. CSS custom properties from themes.css: `--accent`, `--primary-bg`, `--primary-hover`, `--background-secondary`, `--danger`, `--text-normal`.

## Spacebar Server Route Patching

### Key Route Files

| Route | File |
|-------|------|
| Single message DELETE | `src/api/routes/channels/#channel_id/messages/#message_id/index.ts` |
| Bulk message DELETE | `src/api/routes/channels/#channel_id/messages/bulk-delete.ts` |
| Message creation | `src/api/util/handlers/Message.ts` |

### Permission Flow (Delete)

Single message delete:
```typescript
if (message.author_id !== req.user_id) {
    if (!rights.has("MANAGE_MESSAGES")) {
        const permission = await getPermission(req.user_id, channel.guild_id, channel_id);
        permission.hasThrow("MANAGE_MESSAGES");
    }
} else rights.hasThrow("SELF_DELETE_MESSAGES");
```

Bulk delete checks rights before DM restriction — superusers can bulk-delete anywhere.

### Build & Deploy (Server)

```bash
npm run build:src  # tsc -b -v
# Deploy single changed file:
scp dist/api/routes/channels/\#channel_id/messages/bulk-delete.js user@vps:/opt/spacebar/dist/api/...
# Restart
ssh user@vps "sudo systemctl restart spacebar"
```

### VPS Deployment Topology (gc.your-domain.example)

Internet → Caddy (Docker container, caddy:2, port 443, config /home/ubuntu/Caddyfile)
├── /api/* → proxy 172.17.0.1:3100 (Spacebar server)
├── /avatars/*, /cdn/*, /files/* → proxy 172.17.0.1:3100
├── /.well-known/spacebar* → proxy 172.17.0.1:3100
├── websocket → proxy 172.17.0.1:3100
└── /* (everything else) → proxy 172.17.0.1:8081 (Fermi UI)

Host processes:
  - Spacebar: systemd spacebar.service, /opt/spacebar, node dist/bundle/start.js, port 3100
  - Fermi: systemd fermi.service, /opt/fermi, node dist/index.js, port 8081
  - PostgreSQL: Docker container, port 5432

### Pitfalls

- Server caches route handlers in memory — full restart required after patches
- No type-checking in swc — run `npx tsc --noEmit` separately for Fermi checks
- VPS git push always fails — no credentials configured. Commit on VPS, pull locally, push from local.
- Hard refresh required (Ctrl+Shift+R) after client deploy — browser caches index.js
- dist/index.js 302 redirect must be verified after every build (`grep -c "/channels/@me" dist/index.js`)
- Before ANY dist deploy, check VPS git status for uncommitted customizations
