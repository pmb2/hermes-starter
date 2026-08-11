# Fermi Client Login Flow: Skipping the Loading Screen

The Fermi client has two distinct "skip the landing page" mechanisms. They complement each other.

## Server-Side Redirect (Already Documented)

The root `/` handler redirects to `/channels/@me` — this is documented in section 6b of `devops/spacebar-deployment` SKILL.md.

## Client-Side Loading Screen Skip (For Unauthenticated Users)

**Problem:** Even after the server redirect, the `/channels/@me` route serves `app.html` which shows the "the operator is loading" loading screen (with the large brand logo). Only THEN does the client-side JS check for a saved session and show the login dialog — with a **transparent** background that lets the loading screen show through.

The user sees: loading logo → translucent login appearing on top — a "welcome page" flash.

**Fix location:** `src/webpage/index.ts` (in the client-side TypeScript bundle)

**The change at the `makeLogin()` call:**

```typescript
// BEFORE: transparent background — loading screen visible through dialog
thisUser = new Localuser(await new Promise<Specialuser>((res) => makeLogin(true, "", res)));

// AFTER: hide loading screen immediately, then show solid login dialog
const loading = document.getElementById("loading") as HTMLDivElement;
if (loading) {
    loading.classList.add("doneloading");
    loading.classList.remove("loading");
}
thisUser = new Localuser(await new Promise<Specialuser>((res) => makeLogin(false, "", res)));
```

**What changed:**
1. **`makeLogin(true, ...)` → `makeLogin(false, ...)`**: The first parameter (`trasparentBg`) controls whether the dialog has a transparent (show-through) or solid background. `false` = solid background with `"solidBackground"` CSS class.
2. **Hide loading div before showing dialog**: Calls `classList.add("doneloading")` and removes `"loading"` to hide the element before the user ever sees it.

**Result:**
- **Not logged in:** Solid login dialog appears immediately — no loading/welcome page flash
- **Logged in:** Loading screen shows briefly while WebSocket connects, then goes to channels

**Implementation details:**
- The loading screen HTML lives in `app.html` (`<div id="loading">`)
- The `"loading"` CSS class controls visibility (flex layout, centered)
- The `"doneloading"` CSS class sets `display: none`
- `makeLogin()` creates a `Dialog` instance and shows it with `dialog.show(trasparentBg)`
- `trasparentBg=false` adds `"solidBackground"` class to the dialog backdrop (opaque overlay)

**Build and deploy:** After modifying `src/webpage/index.ts`, run `npm run build` which bundles it into `dist/webpage/index.js`. Then deploy dist to VPS and restart the fermi service.

**Verification:** Check the built bundle for the correct `makeLogin` call:
```bash
grep -c 'makeLogin(false' dist/webpage/index.js
# Expected: ≥1
```
