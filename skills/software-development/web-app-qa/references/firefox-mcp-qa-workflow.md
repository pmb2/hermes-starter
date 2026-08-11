# Firefox MCP DevTools QA Workflow

**When to use this instead of Playwright:** the operator explicitly demands browser UI verification before you report anything as "working." Use Firefox MCP DevTools when:
- You need to verify **actual rendered UI** (not just HTTP status codes)
- The app has **multi-role dashboards** (admin, client, contractor)
- the operator is online and you want to show him **screenshots as proof**
- You need to catch **JS hydration errors** or **CORS issues** that curl doesn't surface
- You're verifying a **Next.js app** where the server may serve HTML but the client-side JS crashes

## Prerequisites

- Make sure the dev server is running first (e.g., `npx next dev -p 3333`)
- Firefox MCP DevTools server must be connected (the `mcp_firefox_devtools_*` tools)

## Workflow Steps

### 1. Navigate to the Login Page

```python
mcp_firefox_devtools_navigate_page(url="http://localhost:PORT/login")
```

Take a snapshot to confirm the page loaded:
```python
mcp_firefox_devtools_take_snapshot()
```

### 2. Log in as Each Role

For demo-mode apps that use localStorage for auth, **clear localStorage between roles** to force a fresh login:

```python
mcp_firefox_devtools_evaluate_script(function="() => { localStorage.clear(); return 'cleared'; }")
```

Then navigate back to `/login`, fill in credentials, submit:

```python
mcp_firefox_devtools_navigate_page(url="http://localhost:PORT/login")
# Wait for page to load, then fill:
mcp_firefox_devtools_fill_by_uid(uid="...", value="admin@demo.com")
mcp_firefox_devtools_fill_by_uid(uid="...", value="demo123")
mcp_firefox_devtools_click_by_uid(uid="...")
```

### 3. Verify the Redirect

After clicking submit, the page should redirect to the correct dashboard. Check the URL:

```python
mcp_firefox_devtools_evaluate_script(function="() => window.location.href")
```

Expected URLs:
- Admin: `http://localhost:PORT/dashboard/admin`
- Client: `http://localhost:PORT/dashboard/client`
- Contractor: `http://localhost:PORT/dashboard/contractor`

If the URL still shows `/login` after login attempt, the auth failed.

### 4. Take a Screenshot of Each Dashboard

```python
mcp_firefox_devtools_screenshot_page(saveTo="${MY_REPOS}/PROJECT/screenshots/01-admin-dashboard.png")
```

Save screenshots to a dedicated `screenshots/` directory in the project.

### 5. Check for JS Errors and Network Failures

```python
# Collect console messages (errors, warnings)
mcp_firefox_devtools_list_console_messages(level="error", limit=20)

# Collect network requests
mcp_firefox_devtools_list_network_requests(limit=20, statusMin=400)
```

Look for:
- **Console errors**: JS exceptions, CORS violations, 404 fetch errors
- **Network 400+/500+**: API endpoints failing
- **Mixed content warnings**: HTTPS page loading HTTP resources

### 6. Repeat for Each Role

Do NOT assume that because one role works, they all work. Each role has a different dashboard with different data queries. Test every role separately:

```python
roles = [
    {"email": "admin@demo.com", "password": "demo123", "path": "/dashboard/admin"},
    {"email": "client@demo.com", "password": "demo123", "path": "/dashboard/client"},
    {"email": "contractor@demo.com", "password": "demo123", "path": "/dashboard/contractor"},
]
```

### 7. Send Screenshots as Evidence

Include the screenshots in your response using MEDIA: paths so the operator can see you actually tested:

```
MEDIA:C:\path\to\screenshots\admin-dashboard.png
MEDIA:C:\path\to\screenshots\client-dashboard.png
MEDIA:C:\path\to\screenshots\contractor-dashboard.png
```

## Common Issues & How to Detect Them via Firefox

| Issue | Firefox Symptom | Detection |
|-------|----------------|-----------|
| **CORS error on login** | Login page stays on `/login` after submit. Console shows "Cross-Origin Request Blocked" | `list_console_messages(level="error")` |
| **JS hydration crash** | Page appears blank. Console shows `TypeError: Cannot read properties of undefined (reading 'X')` | `list_console_messages(level="error")` + try small page interaction |
| **Auth redirect loop** | URL keeps alternating between `/login` and `/dashboard` | `evaluate_script("() => window.location.href")` after a 2s wait |
| **Stale compiled code** | Login returns 500 / "Internal Server Error" toast even though the API code looks correct | Check if you need to restart the dev server (especially after env var changes) |
| **Empty dashboard** | Dashboard loads but shows no data. API returns 200 with `[]` | Compare the actual page content — is it truly empty or just loading? |

## Key Differences from Playwright Headless

| Aspect | Playwright Headless | Firefox MCP DevTools |
|--------|-------------------|---------------------|
| **Rendering** | Headless (may differ from real browser) | the operator's actual Firefox window |
| **Auth state** | Fresh profile each time | Can use the operator's existing session cookies |
| **Speed** | Faster (no GUI rendering) | Slower (real browser) |
| **Evidence** | Need to save screenshots separately | Screenshots capture what the operator would actually see |
| **Console access** | Via `page.on('console')` events | Via `list_console_messages()` tool |
| **Network monitoring** | Via `page.on('requestfailed')` | Via `list_network_requests()` tool |

## Pitfalls

- **localStorage persists between role tests.** If you logged in as admin, clicking "login" for contractor may re-authenticate as admin because the auth token is already in localStorage. Always call `localStorage.clear()` before testing a new role.
- **Firefox may be slow to start.** The first navigation after a page load sometimes takes ~5s. Be patient — use `list_console_messages()` to check if anything loaded.
- **UIDs change between snapshots.** Take a fresh `take_snapshot()` before trying to click/fill elements. Old UIDs from a previous snapshot will fail.
- **Port conflicts.** If the dev server isn't starting, check if an old process is still holding the port: `netstat -ano | grep ':PORT' | grep LISTEN`.
- **CORS in Firefox is stricter than Chrome.** Firefox blocks cross-origin POST to Supabase from localhost, while Chrome may silently allow it. If login works in Chrome but not Firefox, check the CORS headers from the server.
