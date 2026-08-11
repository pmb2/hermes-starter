# Auth System Landscape — the operator's Infrastructure (July 2026)

## What Already Exists

### Authgear (Postgres-backed, OIDC/OAuth2 platform)
- **Image**: `quay.io/theauthgear/authgear`
- **Status**: Containers stopped (full profile, need `docker compose up`)
- **Config**: `${MY_REPOS}\Documents\github\n8n\data\authgear\config\`
- **Portal**: `auth-admin.your-domain.example` (admin UI for managing users/OAuth apps)
- **Auth endpoint**: `auth.your-domain.example` (Traefik route already configured)
- **Backend**: Postgres + Redis (both already running)
- **Email**: Mailjet SMTP configured (Mailjet API key/secret in .env)
- **Capabilities**:
  - Email/password registration with verification
  - Google OAuth (built-in provider config)
  - Custom OAuth providers (can register any OIDC/OAuth2 provider — useful for sportsbook mapping)
  - OTP, magic link, passkeys
  - Admin portal for user management
  - OIDC-compliant tokens

### Supabase Auth (GoTrue, tied to BookEnds)
- **Image**: `public.ecr.aws/supabase/gotrue:v2.188.1`
- **Status**: ✅ Running healthy (part of BookEnds stack)
- **Port**: 9999 (internal)
- **Access**: Through Supabase Kong gateway on port 54321
- **Capabilities**:
  - Email/password + magic link
  - Google, GitHub, Apple OAuth
  - Row-level security
  - User management through Supabase Studio (port 54323)
- **Downside**: Tied to BookEnds stack — sharing auth between BookEnds and another app can get messy

### Custom JWT (TAC Odds — what's actually in use)
- **File**: `backend/auth.py`
- **Method**: PBKDF2-HMAC-SHA256 (100K iterations), HS256 JWT
- **Storage**: Flat JSON file (`data/users.json`)
- **Features**: Register, login, me, profile update
- **Missing**: OAuth, email verification, password reset, 2FA, rate limiting, refresh tokens

## What TAC Odds Needs

1. **Email/password registration** — basic signup
2. **Google OAuth** — "Login with Google"
3. **Sportsbook auth** — custom module for DraftKings/FanDuel credential exchange (these don't offer OAuth — uses session cookies/credentials)
4. **Secure** — HTTPS, proper password hashing, brute-force protection
5. **Professional looking** — branded login UI, not plain forms
6. **Account retention** — profile, bankroll, bet history, settings

## Recommendation Ranking

### 1. Authgear — Turn it on
**Best fit because:**
- Already deployed (postgres-backed, Mailjet SMTP, Redis sessions, admin portal)
- Covers email/pw + Google OAuth natively
- Custom OAuth provider registration can map sportsbook auth flow
- Admin portal gives the operator a UI to manage users without coding
- OIDC-compliant — any future service can consume the same auth
- Traefik route already exists at `auth.your-domain.example`
- What's needed: `docker compose up`, configure the admin portal, point TAC Odds login to redirect to auth.your-domain.example

### 2. FastAPI Users + Authlib — Python-native, zero new infra
- Drops into existing FastAPI backend as a pip install
- Authlib handles Google OAuth protocol
- FastAPI Users gives registration, email verification, password reset as route decorators
- SQLAlchemy → existing SQLite or upgrade to Postgres
- No new containers
- Gap: No admin UI, no hosted login page

### 3. Supabase Auth — Already running, share with BookEnds
- Gotrue is healthy on port 9999
- Full OAuth catalog
- User management via Supabase Studio
- Gap: Tied to BookEnds stack; sharing auth between stacks is messy

## Key Insight: Sportsbook Auth Is Always Custom

No FOSS auth system supports DraftKings/FanDuel OAuth because these platforms don't offer public OAuth. The sportsbook credential exchange (username/password → session cookies → verify) is a custom module regardless of which auth system is chosen. Authgear handles the *user* auth layer; the sportsbook module is a separate Python integration that lives in TAC Odds' backend.

## DNS / Domain

- **Domain registrar**: `registrar-servers.com` (Namecheap)
- **Public IP**: `74.76.35.96`
- **Auth domain**: `auth.your-domain.example` (already resolves, handled by Traefik)
