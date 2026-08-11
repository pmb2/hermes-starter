# Chrome DevTools MCP: Angular SPA Automation Patterns

> Workflow for interacting with Angular SPAs using the `mcp_chrome_devtools_mcp_*` tools. Based on reverse-engineering the Securus Online portal (`securustech.online`) on June 17, 2026.

## When to Use Chrome DevTools MCP over Playwright

| Situation | Use |
|-----------|-----|
| SPA with complex auth (Angular, React, Vue) | Chrome DevTools MCP — can inspect running JS state, localStorage, sessionStorage |
| Multiple tabs already open in user's browser | Chrome DevTools MCP — list_pages + select_page to leverage existing sessions |
| CAPTCHA or visual verification needed | Chrome DevTools MCP — screenshot + respond to dialogs |
| CI / fully automated pipeline | Playwright (headless, no UI needed) |
| Need to extract auth tokens or API calls | Chrome DevTools MCP — console evaluate + network request inspection |
| Simple smoke test with no login | Either works fine |

## Key Flow

```
1. mcp_chrome_devtools_mcp_navigate_page(type="url", url="https://example.com")
2. mcp_chrome_devtools_mcp_take_snapshot()     -- get UIDs of interactive elements
3. mcp_chrome_devtools_mcp_fill_form()          -- fill multiple fields at once
4. mcp_chrome_devtools_mcp_click(uid=...)       -- submit
5. mcp_chrome_devtools_mcp_evaluate_script()    -- check current URL / page state
6. mcp_chrome_devtools_mcp_list_console_messages() -- check for errors
```

## Critical: Angular SPA Auth Pitfall

**DO NOT navigate to hash-based routes via `mcp_chrome_devtools_mcp_navigate_page` when already authenticated.** Angular stores auth tokens in in-memory JavaScript state only (not localStorage/cookies in many deployments). Loading a URL like `https://example.com/#/products/emessage/inbox` causes a full page reload, which destroys the Angular app and its auth state, dropping you back at the login page.

**Correct approach:** Use `mcp_chrome_devtools_mcp_click` on an in-page link element (e.g., a "LAUNCH" button, nav link, or any `<a>` tag within the SPA) to trigger Angular's router navigation. This keeps the Angular app alive and the auth token intact.

```
// WRONG -- loses auth:
mcp_chrome_devtools_mcp_navigate_page(type="url", url="https://securustech.online/#/products/emessage/inbox")

// RIGHT -- click an in-page link:
// 1. Find the LAUNCH button in the snapshot
// 2. mcp_chrome_devtools_mcp_click(uid="236_24")
// 3. Verify: evaluate_script returns new hash route, app is still logged in
```

**How to tell you have been logged out:**
- `mcp_chrome_devtools_mcp_evaluate_script` returns `{url: ".../#/login"}` instead of `/#/my-account` or `/#/products/emessage/inbox`
- The snapshot shows the login form (Email Address + Password fields + SIGN IN button)
- The URL may have a `?returnUrl=` parameter appended

**Recovery:** Fill the login form again and re-authenticate. If the TOS was already accepted in a prior session, the modal will not reappear (acceptance is tracked server-side).

## Form Filling

Use `mcp_chrome_devtools_mcp_fill_form` to fill multiple form fields in a single call -- it is significantly faster than clicking each field individually:

```
elements: [
  {"uid": "230_16", "value": "user@email.com"},
  {"uid": "230_18", "value": "password123"}
]
```

After filling, use `mcp_chrome_devtools_mcp_click(uid=...)` on the submit button OR `mcp_chrome_devtools_mcp_press_key(key="Enter")` to submit. If the form does not submit with click, try Enter.

## Snapshot Timeouts and Verbosity

- Taking a snapshot with `verbose=true` on complex Angular SPAs can return 250,000+ characters -- the string is so large it may be truncated by the sandbox
- Prefer `verbose=false` (default) for most interactions
- For finding specific interactive elements, use `mcp_chrome_devtools_mcp_evaluate_script` with CSS selectors or XPath instead of parsing the massive snapshot

## Checking Page State After Actions

After clicking a button or submitting a form, always verify where you landed:

```
mcp_chrome_devtools_mcp_evaluate_script(function="() => { return { url: window.location.href, title: document.title }; }")

mcp_chrome_devtools_mcp_list_console_messages(pageSize=30)
```

## Handling Modals and Dialogs

SPAs often present modals (TOS acceptance, cookie consent, chat widgets) after login. The modal elements appear in the snapshot. Find the "ACCEPT" / "Close" button UID and click it.

**TOS Modal pattern (Securus-specific):** After login, a TERMS & CONDITIONS dialog appears with an ACCEPT button at the bottom of a long scrollable section. The snapshot shows the full TOS text followed by the button UID. Clicking ACCEPT dismisses the modal and the acceptance is server-side persisted -- subsequent logins will not re-prompt.

**Chat widget pattern:** A floating "Close Accessible Modal" button and "LET'S CHAT" button appear on most pages. Close it if it obscures UI elements.

## Multi-Page Workflow for Angular SPAs

For workflows that span multiple SPA routes (login, dashboard, inbox, compose, send):

```
1. Navigate to login page (URL navigation is fine here since you are not authenticated yet)
2. Fill credentials + submit
3. Handle any modals (TOS, chat)
4. Verify dashboard loaded (check URL includes /#/my-account)
5. Click in-page link to navigate to next route (e.g. LAUNCH, inbox)
6. Verify inbox loaded (check URL includes /#/products/emessage/inbox)
7. Continue via in-page clicks only -- never navigate by URL again
```

## Extracting API Endpoints

When you need to reverse-engineer the backend API (no public documentation), use Chrome DevTools MCP to capture network requests while interacting with the SPA:

1. After logging in, use `mcp_chrome_devtools_mcp_list_network_requests` to see the API calls the Angular app makes
2. Useful endpoints: `/api/auth/login`, `/api/auth/token`, `/api/messages`, `/api/contacts`
3. Use `mcp_chrome_devtools_mcp_get_network_request(reqid=...)` to inspect request/response details including headers, auth tokens, and request bodies
4. Note: `mcp_chrome_devtools_mcp_navigate_page` resets the network request log -- capture traffic before navigating away

## Tool Reference

| Tool | Purpose | Key Args |
|------|---------|----------|
| mcp_chrome_devtools_mcp_navigate_page | Load URL or reload | type="url", url="..." or type="reload" |
| mcp_chrome_devtools_mcp_take_snapshot | Get page UIDs | verbose=false (default) or true |
| mcp_chrome_devtools_mcp_fill_form | Fill multiple fields | elements=[{uid, value}] |
| mcp_chrome_devtools_mcp_click | Click element | uid, dblClick, includeSnapshot |
| mcp_chrome_devtools_mcp_press_key | Keyboard input | key="Enter", "Tab", "Escape" |
| mcp_chrome_devtools_mcp_evaluate_script | Run JS in page | function="() => { ... }" |
| mcp_chrome_devtools_mcp_list_console_messages | Check errors | pageSize, types |
| mcp_chrome_devtools_mcp_list_network_requests | See API calls | pageSize, resourceTypes |
| mcp_chrome_devtools_mcp_take_screenshot | Visual evidence | format="png", fullPage=true |
| mcp_chrome_devtools_mcp_list_pages | See all open tabs | (no args) |
| mcp_chrome_devtools_mcp_select_page | Switch to a tab | pageId, bringToFront |
