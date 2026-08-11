# CORS + System Env Var Override — Debugging Path

Reproduced from a constructManage debugging session (2026-05-23).

## Symptom

User reported "it's not working" in Firefox. API routes all returned HTTP 200 via curl. Server logs showed all compilations successful. But in a real browser:

1. Login form submitted → stayed on login page (no redirect)
2. Console showed `Cross-Origin Request Blocked` errors to `https://bookends.your-domain.example/auth/v1/token`
3. The `signIn` function threw a `Sign in error: Error` (caught and swallowed by the UI)

## Root Cause Chain

```
Windows system env vars set:
  NEXT_PUBLIC_SUPABASE_URL=https://bookends.your-domain.example

                 ↓
isSupabaseConfigured() returns true (both vars exist in process.env)
                 ↓
Demo mode NOT activated
                 ↓
signIn() tries real Supabase auth against remote URL from localhost
                 ↓
Firefox blocks cross-origin POST (CORS)
                 ↓
signIn() catches error, returns { error }
                 ↓
Login page catches error, shows toast, stays on /login
```

## Why `.env.local` Did Not Work

Next.js load order for env vars:
1. `process.env` (system/windows env vars) ← FOUND FIRST
2. `.env.$(NODE_ENV).local`
3. `.env.local`
4. etc.

Since `NEXT_PUBLIC_SUPABASE_URL` exists in `process.env` (set globally in Windows), Next.js never reads the `.env.local` value.

## Fix

Create a startup script that explicitly unsets the env vars before starting Next.js:

```bash
#!/bin/bash
unset NEXT_PUBLIC_SUPABASE_URL
unset NEXT_PUBLIC_SUPABASE_ANON_KEY
unset SUPABASE_SERVICE_ROLE_KEY
cd "$(dirname "$0")"
NODE_OPTIONS="--max-old-space-size=2048" exec npx next dev -p 3333
```

Add to package.json:
```json
"dev:demo": "bash start-dev.sh"
```

### Nuclear Option: Hardcode in Source

When the startup-script approach isn't practical (background processes that don't inherit shell unset, or system-wide env vars you can't modify), hardcode the URL directly in source files:

```javascript
// BEFORE:
const API = process.env.NEXT_PUBLIC_SUPABASE_URL || 'http://localhost:44444'

// AFTER:
const API = 'http://localhost:44444'
```

This prevents Next.js from inlining the wrong system value at compile time. Use only for local-dev-only files. The same pattern fixes truncated `SUPABASE_SERVICE_ROLE_KEY` values that get mangled by tooling display.

**Warning:** Do NOT apply to files deployed to production — it removes configurability.

## Tell-Tale Signs

- `env | grep NEXT_PUBLIC_SUPABASE` returns a URL you don't expect
- The URL in the env var belongs to a DIFFERENT project (e.g., bookends vs constructManage)
- Login works with curl-generated POST but not in a real browser
- Firefox shows CORS error; Chrome may silently fail
- `isSupabaseConfigured()` returns `true` when you expect `false`
