# Google Cloud OAuth Client Setup via Browser

Pattern for creating/editing Google OAuth client credentials when deploying a self-hosted web app that needs Google sign-in or Google API access (YouTube, GMB, Gmail, etc.).

## When Needed
- App needs Google OAuth for user sign-in
- App needs to access Google APIs (YouTube uploads, GMB posts, Gmail)
- Deploying a new or existing app to a new domain

## One-Time Prerequisites
1. **Google Cloud Project** — exists or create at https://console.cloud.google.com
2. **API enabled** — YouTube Data API v3, GMB API, etc. in APIs & Services → Library
3. **OAuth consent screen configured** — External user type, add test user emails

## Creating a Web Application OAuth Client

### Step 1: Navigate
https://console.cloud.google.com/apis/credentials?project={PROJECT_ID}

### Step 2: Create Credentials
Click "Create Credentials" → "OAuth client ID"

### Step 3: Configure
- **Application type:** Web application
- **Name:** Descriptive name
- **Authorized JavaScript origins:** `https://app.yourdomain.com`
- **Authorized redirect URIs:** One per platform callback endpoint

### Step 4: Determine Redirect URIs
Apps define callback paths in their source code. Search for:
```bash
grep -r "redirectUri\|redirect_uri\|FRONTEND_URL" apps/backend/src/ libraries/
```

Common patterns:
- `{FRONTEND_URL}/integrations/social/{platform}` (Postiz: youtube, gmb)
- `{FRONTEND_URL}/api/auth/callback/google` for general auth

### Step 5: Add to App Config
```yaml
YOUTUBE_CLIENT_ID: '***.apps.googleusercontent.com'
YOUTUBE_CLIENT_SECRET: 'GOCSPX-***'
```

### Step 6: Add Test Users
In Google Auth Platform → Audience, add all test email addresses. Required while app is in "Testing" status.

## Common Pitfalls
- **Redirect URI mismatch:** Must match EXACTLY including protocol and trailing slashes
- **Testing mode blocks non-test-users:** Add every testing email
- **Secret is shown once only** — download or save immediately on creation
- **API must be enabled** for the OAuth-scoped features to work
