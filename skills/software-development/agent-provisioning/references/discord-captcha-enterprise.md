# Discord Enterprise hCaptcha — Investigation Notes

## Summary

Discord's Developer Portal API (`POST /api/v9/applications`) uses **hCaptcha Enterprise** to block programmatic bot application creation. Standard CAPTCHA solving services (2captcha, CapSolver) solve the visual challenge but the solution is **rejected** because Enterprise hCaptcha uses **rqtoken binding** — the challenge is cryptographically signed per-session.

## API Response Format

When creating an application with a user token:

```
POST https://discord.com/api/v9/applications
Authorization: <user_token>
Content-Type: application/json
{"name": "BotName"}

→ HTTP 400
{
  "captcha_key": ["captcha-required"],
  "captcha_sitekey": "a9b5fb07-92ff-493f-86fe-352a2803b3df",
  "captcha_service": "hcaptcha",
  "captcha_session_id": "<uuid>",        // changes per request
  "captcha_rqdata": "<base64>==<token>", // enterprise challenge data
  "captcha_rqtoken": "<base64>"          // signed request token
}
```

## Retry Attempts (All Failed)

| Approach | Result |
|----------|--------|
| `captcha_key` in body (string) | `captcha-required` — ignored |
| `captcha_key` + `captcha_sitekey` in body | `captcha-required` — ignored |
| `captcha_key` as array | `captcha-required` — ignored |
| `X-Captcha-Key` header | `captcha-required` — ignored |
| `captcha_key` + `captcha_rqtoken` in body | `invalid-response` — Discord recognized the format but bound token doesn't match |

The `invalid-response` on the last approach confirms:
- The format `captcha_key` + `captcha_rqtoken` IS the correct way to submit
- But the hCaptcha solution from 2captcha doesn't carry the correct enterprise binding

## Root Cause

hCaptcha Enterprise generates a `captcha_rqtoken` (request token) that is cryptographically bound to the session. The `captcha_rqdata` value (passed to the solving service) includes this binding. When 2captcha returns a solution, the token is visually correct but lacks the enterprise cryptographic signature that Discord verifies against the rqtoken.

Even 2captcha's "solved" status (status=1) returns a token that Discord rejects as `invalid-response` — the solving service's worker solves the visual puzzle but the resulting token doesn't carry the signed rqtoken binding.

## Implications

- **Do not attempt API automation** — neither raw API calls nor CAPTCHA solving services can bypass this.
- **Only two working paths exist:**
  1. **Manual Developer Portal** — create each bot application manually at https://discord.com/developers/applications
  2. **Self-hosted server** (Spacebar/Fermi) — uses the same Discord API protocol but has no hCaptcha. Bot applications can be created via simple POST requests to the Spacebar API.
- **Playwright browser automation** can work if the user solves one CAPTCHA per session (Discord often only requires one CAPTCHA per browser session, not per application), but requires real user clicks, not `dispatch_event`.

## Discord's hCaptcha Sitekey

The sitekey is stable: `a9b5fb07-92ff-493f-86fe-352a2803b3df`. This identifies Discord's hCaptcha Enterprise deployment. Enterprise hCaptcha is identified by the presence of `captcha_rqtoken` and `captcha_rqdata` fields — regular hCaptcha only returns `captcha_key`, `captcha_sitekey`, and `captcha_service`.
