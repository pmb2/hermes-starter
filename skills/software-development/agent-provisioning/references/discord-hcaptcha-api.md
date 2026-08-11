# Discord Dev Portal hCaptcha Browser API Reference

> Browser-side hCaptcha interaction when the user is logged into the Discord Developer Portal in Chrome.
> Covers `window.hcaptcha` JS API and Chrome DevTools MCP automation patterns.

## Accessing hCaptcha from Chrome DevTools MCP

When the Discord Developer Portal creates a new application and hCaptcha triggers, the `window.hcaptcha` object is available in the page context. It can be accessed via `mcp_chrome_devtools_mcp_evaluate_script`.

**IMPORTANT: Chrome DevTools MCP evaluate_script runs in an isolated context.**
- `localStorage` is NOT defined — don't try to read/write it
- `document.cookie` only returns non-HttpOnly cookies
- The `authorization` header is NOT automatically included in fetch calls — you must provide it from the extracted token
- However, page-level globals like `window.hcaptcha`, `window.webpackChunkdiscord_developers` ARE accessible

## hCaptcha JS API Methods

Available on `window.hcaptcha`:

| Method | Description |
|--------|-------------|
| `render(parent, opts)` | Renders a captcha widget into an element |
| `execute(widgetId)` | Triggers the captcha challenge (shows image challenge) |
| `getResponse(widgetId?)` | Returns the response token (empty string "" if unsolved) |
| `getRespKey()` | Returns internal response key (JWT-like token, e.g. `E1_eyJhbG...`) |
| `reset(widgetId?)` | Resets the widget |
| `close()` | Closes the captcha dialog |
| `setData(widgetId, data)` | Sets data on the widget |
| `remove(widgetId?)` | Removes the widget |

**Usage pattern for Chrome DevTools MCP evaluate_script:**
```javascript
() => {
  const hc = window.hcaptcha;
  
  // Check if solved
  const resp = hc.getResponse();
  // "" = not solved
  
  // Trigger challenge
  hc.execute();
  
  // Close dialog
  hc.close();
  
  // Check internal key
  const key = hc.getRespKey();
  // e.g. "E1_eyJhbGciOiJIUzI1NiIsInR5cCI..."
}
```

## Challenge Flow

1. User fills name + checks TOS in the "Create a new app" dialog
2. User clicks "Create" — creates the hCaptcha widget
3. `window.hcaptcha.execute()` is called → shows "Wait! Are you human?" dialog
4. User clicks "I am human" checkbox → either passes silently OR shows image challenge
5. If image challenge appears, it renders in a second iframe with `#frame=challenge`
6. User solves the image puzzle → response token generated → Discord API retried

## Challenge Types Observed

| Type | Description |
|------|-------------|
| Checkbox only | Click "I am human" and it passes automatically (rare, depends on fingerprint) |
| Image selection | "Put the TWO food items onto the plate with the same kind of food" — click matching images |

## Accessibility Options

Accessible from the challenge menu ("About hCaptcha & Accessibility Options"):

| Option | Result |
|--------|--------|
| Retrieve hCaptcha Accessibility Cookie | Opens hCaptcha dashboard signup page — requires account, cannot be automated |
| Display hCaptcha Accessibility Challenge | Refreshes to a text-based challenge (still requires solving) |
| Report Image / Report Bug | Opens reporting flow |
| Information | About hCaptcha |

## Discord API Captcha Response

When `POST /api/v9/applications` is blocked by captcha:

```json
{
  "captcha_key": ["captcha-required"],
  "captcha_sitekey": "a9b5fb07-92ff-493f-86fe-352a2803b3df",
  "captcha_service": "hcaptcha",
  "captcha_session_id": "<uuid>",
  "captcha_rqdata": "<base64 string>",
  "captcha_rqtoken": "<base64 string>"
}
```

- `captcha_sitekey`: Discord's hCaptcha sitekey (`a9b5fb07-92ff-493f-86fe-352a2803b3df`)
- `captcha_service`: Always `"hcaptcha"`
- `captcha_rqdata` / `captcha_rqtoken`: Bound challenge tokens — used if a captcha solving service is employed
- These values are **server-enforced** — you must solve the challenge to get a valid response token

## hCaptcha Iframe States

| URL Fragment | State |
|-------------|-------|
| `#frame=checkbox` | Initial state — checkbox-only ("I am human") |
| `#frame=challenge` | Challenge state — image puzzle or text challenge |

Iframes are cross-origin (`newassets.hcaptcha.com` vs `discord.com`), so you CANNOT:
- Access the iframe's contentDocument (throws SecurityError)
- Read captcha images (cross-origin restrictions)
- Inject event listeners into the iframe

But you CAN:
- Click the iframe at coordinates matching the checkbox position
- Use `window.hcaptcha` API to interact (execute, close, getResponse, etc.)

## Chrome DevTools vs Hermes Browser Tools

| Tool | Context | hCaptcha Access | Vision Capability |
|------|---------|----------------|-------------------|
| `mcp_chrome_devtools_mcp_*` | User's logged-in Chrome | Full `window.hcaptcha` API access | Screenshots only (no vision analysis built-in) |
| `browser_*` (Hermes) | Fresh browser | No Discord session — won't reach hCaptcha | `browser_vision` available (needs vision provider configured) |

## Known Limitations

- **`localStorage` is undefined** in Chrome DevTools MCP evaluate_script — this means you cannot access Discord's stored auth token directly. Use the `authorization` header from captured network requests instead.
- **hCaptcha challenge images cannot be programmatically read** — cross-origin iframe restrictions prevent DOM access, and no pre-configured vision model exists on this Hermes setup.
- **Captcha solving services (2captcha, CapSolver) produce tokens Discord rejects** — Discord uses hCaptcha Enterprise with `captcha_rqtoken` binding that invalidates third-party solutions. See `discord-captcha-enterprise.md`.
- **Accessibility cookie** requires signing up for an hCaptcha account (not an automation bypass).
- **No vision provider** is configured in Hermes (config.yaml `auxiliary.vision.provider: auto` with empty fields). Configuring one (e.g., OpenRouter vision model) would unblock automated captcha solving.
