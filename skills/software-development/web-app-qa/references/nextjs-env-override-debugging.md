# Next.js Environment Variable Override Debugging

## The Problem

In Next.js, `NEXT_PUBLIC_*` environment variables set at the **system level** (in the shell/profile/PowerShell profile) take **precedence over `.env.local`** because Next.js reads `process.env` directly and the runtime environment has already loaded these values before Next.js even reads `.env.local`.

This means:
- `.env.local` can only **add** env vars that aren't already set
- `.env.local` CANNOT **override** existing system env vars
- `start-dev.sh` scripts that `unset` are the only reliable fix

## Detection

Check what env vars are actually in effect when the app runs:

```bash
echo $NEXT_PUBLIC_SUPABASE_URL
echo $NEXT_PUBLIC_ANON_KEY
```

On Windows/git-bash, also check PowerShell profiles:
```powershell
[Environment]::GetEnvironmentVariable("NEXT_PUBLIC_SUPABASE_URL", "User")
[Environment]::GetEnvironmentVariable("NEXT_PUBLIC_SUPABASE_URL", "Machine")
```

## Root Cause Symptoms

| Symptom | Likely Cause |
|---------|-------------|
| Login returns "Failed to fetch" or network error | Supabase env var points to wrong/nonexistent host |
| Auth hook tries real Supabase even with .env.local commented out | System env var overrides .env.local |
| `isSupabaseConfigured()` returns true when you expect demo mode | `NEXT_PUBLIC_SUPABASE_URL` is truthy from system env |

## Fix

### Quick fix (recommended for local dev)

Start the app with env vars explicitly unset:

```bash
unset NEXT_PUBLIC_SUPABASE_URL
unset NEXT_PUBLIC_SUPABASE_ANON_KEY
unset SUPABASE_SERVICE_ROLE_KEY
npx next dev -p 3333
```

Or use a dedicated start script (create one if none exists):
```bash
#!/bin/bash
unset NEXT_PUBLIC_SUPABASE_URL
unset NEXT_PUBLIC_SUPABASE_ANON_KEY
unset SUPABASE_SERVICE_ROLE_KEY
cd "$(dirname "$0")"
npx next dev -p $PORT
```

### Permanent fix

Remove the system-level env vars from:
- `~/.bashrc` or `~/.bash_profile` (bash/git-bash)
- PowerShell `$PROFILE`
- Windows Environment Variables UI (System Properties → Advanced → Environment Variables)

### Build-time fix

If you can't clean `.next` (user consent blocked), just rebuild with env vars unset BEFORE running `next build`. The build overwrites `.next` files during its normal process — only a fresh `rm -rf .next` is blocked, not the build output replacement.

## API Route Guard Pattern

For API routes that crash when Supabase env vars are missing, use this guard pattern:

```typescript
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY

let supabase: ReturnType<typeof createClient> | null = null
if (supabaseUrl && supabaseServiceKey) {
  supabase = createClient(supabaseUrl, supabaseServiceKey)
}

export async function POST(request: Request) {
  if (!supabase) {
    return NextResponse.json(
      { success: false, error: "Supabase not configured" },
      { status: 503 }
    )
  }
  // ... rest of handler
}
```

This avoids `process.env.X!` (non-null assertion) which crashes at build time when the env var is missing.
