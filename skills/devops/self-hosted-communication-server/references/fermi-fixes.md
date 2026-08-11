# Additional Fermi & Spacebar Fixes

## Root `/` Redirect — Causes Retry Loop
Fermi server redirects `/` → `/channels/@me`. The app at `/channels/@me` tries WebSocket with no token → rejected → retry loop.
**Fix:** Patch `dist/index.js`:
```javascript
// Replace: if(s==="/"){r.writeHead(302,{"Location":"/channels/@me"});r.end();return}
// With:
if(s==="/"){const ip=await e.readFile(n.join(p,"webpage","index.html"));r.writeHead(200,{"Content-Type":"text/html"});r.write(ip);r.end();return}
```
Restart Fermi after patching.

## Login Schema Rejects `email` Field
Fermi sends `{"email":"...","password":"..."}` but Spacebar expects `login`.
**Fix 1:** Add `"LoginSchema"` to `ignoredRequestSchemas` in `route.js`.
**Fix 2:** In `login.js`: `let { login, password, captcha_key, undelete, email } = req.body; if (!login && email) { login = email; }`

## READY Payload Missing Members
Fermi needs top-level `members` array in READY event.
**Fix:** After `guilds: remappedGuilds,` in `Identify.js`:
```javascript
members: members.map(function(m) { var pm = m.toPublicMember(); pm.user = user.toPublicUser(); return pm; }),
```
Restart Spacebar.

## @everyone Permissions Varchar
`roles.permissions` is varchar. `|` does string concat, not bitwise OR.
**Fix:** Cast to bigint: `SET permissions = (permissions::bigint | 1024)::text`
