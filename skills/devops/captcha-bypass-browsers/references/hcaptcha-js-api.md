# hCaptcha JS API — Direct Interaction Pattern

Found on Discord's Developer Portal (and likely on other sites using the standard hCaptcha widget). The `window.hcaptcha` object is available after the hCaptcha script loads and provides programmatic control of the captcha widget.

## Discovery

The hCaptcha object is available as `window.hcaptcha` on any page where the standard hCaptcha widget is rendered. On Discord's Developer Portal (`discord.com/developers/applications`), it exists when the "Create a new app" dialog triggers a captcha challenge.

**Detection:**
```javascript
if (window.hcaptcha) {
  console.log('hCaptcha API available:', Object.getOwnPropertyNames(Object.getPrototypeOf(window.hcaptcha)));
}
```

## Available Methods (from hCaptcha v1)

| Method | Purpose | Notes |
|--------|---------|-------|
| `render(container, params)` | Render a new captcha widget | params: {sitekey, callback, theme, size, ...} |
| `execute(widgetId)` | Programmatically trigger the challenge | Can be called without widgetId if only one widget |
| `getResponse(widgetId)` | Get the captcha response token | Returns empty string `""` if not yet solved |
| `getRespKey()` | Get internal response key | Returns a JWT-like key (e.g. `E1_eyJhbG...`) even before solve |
| `reset(widgetId)` | Reset the widget to unsolved state | |
| `close()` | Close the challenge dialog | Hides the challenge overlay |
| `setData(widgetId, data)` | Set custom data on the widget | Unknown effect in standard Discord usage |
| `remove(widgetId)` | Remove the widget from DOM | |

## Challenge Types Encountered

hCaptcha can show different challenge types. Examples encountered on Discord:

- **Image selection:** "Put the TWO food items onto the plate with the same kind of food" — select matching food item images and place them onto the correct plate
- **Accessibility text challenge:** Available via `About hCaptcha → Display hCaptcha Accessibility Challenge` (menu item 2 of 5). This requests a text-based alternative, but Discord's implementation may simply refresh to a new image challenge instead.

## Accessibility Menu Options

The About/Accessibility menu (triggered by clicking the hCaptcha logo button + the About link, or the dedicated button labeled "About hCaptcha & Accessibility Options") contains:

1. **Retrieve hCaptcha Accessibility Cookie** — Opens `dashboard.hcaptcha.com/signup?type=accessibility`. Requires signing up for an hCaptcha account with accessibility status. NOT a quick bypass.
2. **Display hCaptcha Accessibility Challenge** — Requests a text challenge. Effectiveness depends on the site's hCaptcha configuration.
3. **Report Image to hCaptcha**
4. **Report Bug to hCaptcha**
5. **Information About hCaptcha**

## Triggering a Challenge Programmatically

On Discord's Developer Portal, after clicking "New Application" and filling the form:

```javascript
// This triggers the hCaptcha challenge popup
window.hcaptcha.execute();

// After execution, the challenge appears as a new iframe
// with URL containing #frame=challenge
// The "Skip Challenge" button is typically disabled at this point
```

## Closing the Challenge

```javascript
// Dismisses the challenge overlay — returns to checkbox state
window.hcaptcha.close();
// The challenge iframe is removed; the checkbox iframe remains
// Use this to recover from a stuck challenge state before retrying
```

## Checking Solve State

```javascript
const response = window.hcaptcha.getResponse();
if (response && response.length > 10) {
  // Captcha is solved — response is the token
}
```

## Gotchas

- **Cross-origin iframe:** The hCaptcha iframe is hosted at `newassets.hcaptcha.com` — you CANNOT access its contentDocument from the parent page due to same-origin policy.
- **Accessibility options:** hCaptcha offers "Display hCaptcha Accessibility Challenge" (text-based) and "Retrieve hCaptcha Accessibility Cookie" options through the About menu. The accessibility cookie requires registering at `dashboard.hcaptcha.com/signup?type=accessibility`.
- **getRespKey returns a value even before solve:** This is NOT the solve token — it's an internal session identifier. Only `getResponse()` returns the actual solve token.
- **Discord captcha response shape:** When Discord's API rejects a creation with captcha-required, the response includes:
  ```json
  {
    "captcha_key": ["captcha-required"],
    "captcha_sitekey": "a9b5fb07-92ff-493f-86fe-352a2803b3df",
    "captcha_service": "hcaptcha",
    "captcha_session_id": "<uuid>",
    "captcha_rqdata": "<base64 token>",
    "captcha_rqtoken": "<base64 token>"
  }
  ```
  These tokens are used to reconstruct the captcha state in the widget. The `captcha_rqdata` and `captcha_rqtoken` are consumed by the hCaptcha widget internally.

## Use Cases

- Programmatically triggering the challenge (e.g. to take a timed screenshot)
- Resetting after a failed solve without refreshing the page
- Detecting solve state from automation scripts
- Closing the challenge overlay to recover from a stuck state
