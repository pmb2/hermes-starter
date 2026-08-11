# SMTP Wiring for App Stacks (Poste.io)

**Context:** The agency stack runs poste.io at `mail.your-domain.example:587`. Multiple app containers (backend, Cal.com, Fonoster, watchdogs) need SMTP credentials to send mail. This reference covers the wiring pattern proven live on 2026-08-04.

## The Core Pattern

Every app container uses the same poste.io SMTP server but with a **different mailbox** (each service sends from a different address). The shared env vars are:

```
SMTP_HOST=mail.your-domain.example
SMTP_PORT=587
SMTP_SECURE=false
SMTP_TLS_REJECT_UNAUTHORIZED=false
```

Each service has its own `SMTP_USER` + `SMTP_PASS` for its mailbox.

## Mailbox Creation

```bash
# MUST run as UID 8 inside the poste container
docker exec -u 8 agency-stack-agency-poste-1 \
  /opt/admin/bin/mailserver email:create <email> <password> [display-name]
```

For example:
```
notifications@your-domain.example    → LEADS_SMTP_PASS
watchdog@your-domain.example         → STACK_WATCHDOG_SMTP_PASS
calcom@your-domain.example           → CALCOM_EMAIL_SERVER_PASSWORD
fonoster@your-domain.example         → FONOSTER_SMTP_PASSWORD
```

## The Dedicated Transport Pattern

The shared backend transporter may have `SMTP_IGNORE_TLS=true` (Haraka quirk) that breaks AUTH. Onboarding email uses a **dedicated STARTTLS transport**:

```js
const nodemailer = require("nodemailer");
const transport = nodemailer.createTransport({
  host: "mail.your-domain.example",
  port: 587,
  secure: false,
  requireTLS: true,
  ignoreTLS: false,
  tls: { rejectUnauthorized: false },
  auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS }
});
```

Key points:
- `requireTLS: true` is required on port 587 (poste announces STARTTLS and refuses AUTH without it)
- `ignoreTLS: false` ensures TLS is actually used
- `rejectUnauthorized: false` is needed because poste uses a self-signed cert

## SMTP_FROM Resolution

The `FROM` address must match the authenticated mailbox or the SMTP server may reject `MAIL FROM`:

```js
function resolveFromEmail() {
  const configured = process.env.SMTP_FROM;
  const user = process.env.SMTP_USER;
  if (user && configured && configuredAddr !== user.toLowerCase()) {
    return `Brand Name <${user}>`;  // override to match authenticated mailbox
  }
  return configured || `Brand Name <${user}>`;  // fallback
}
```

## Mailbox-to-Service Mapping

| Service | Mailbox | Env Var | Purpose |
|---------|---------|---------|---------|
| Leads backend (onboarding) | leads@your-domain.example | SMTP_USER/PASS | Partner welcome, owner alerts |
| Leads backend (notifications) | notifications@your-domain.example | LEADS_SMTP_PASS | Lead notifications |
| Watchdog | watchdog@your-domain.example | STACK_WATCHDOG_SMTP_PASS | System alerts |
| Cal.com bookings | calcom@your-domain.example | CALCOM_EMAIL_SERVER_PASSWORD | Booking confirmations |
| Fonoster voice | fonoster@your-domain.example | FONOSTER_SMTP_PASSWORD | Call transcripts, voicemail |

## Testing a Real Send (from app container)

```bash
docker exec -it agency-stack-agency-leads-backend-1 node -e "
const nodemailer = require('nodemailer');
const t = nodemailer.createTransport({
  host: 'mail.your-domain.example', port: 587, secure: false,
  requireTLS: true, ignoreTLS: false,
  tls: { rejectUnauthorized: false },
  auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS }
});
t.sendMail({
  from: process.env.SMTP_FROM,
  to: '<your-email>@gmail.com',
  subject: 'SMTP test ' + Date.now(),
  text: 'Poste SMTP is working'
}).then(r => console.log('sent', r.messageId)).catch(e => console.error(e));
"
```

## Pitfalls

1. **AUTH requires the full email address** — `leads` fails with 535; use `leads@your-domain.example`.
2. **STARTTLS is required before AUTH on 587** — raw EHLO then AUTH LOGIN hangs. Nodemailer handles this, but verify with the app's own library, not a raw socket.
3. **Self-signed cert** — set `tls: { rejectUnauthorized: false }` or `SMTP_TLS_REJECT_UNAUTHORIZED=false`.
4. **MAIL FROM mismatch** — if FROM address does not match the authenticated mailbox, Haraka returns `550 Authentication required`. The `resolveFromEmail()` pattern above fixes this.
5. **Guard blacklists Docker gateway** — if you see `554 Blacklisted [172.x.x.x]`, the poste guard plugin is blocking the Docker bridge. Whitelist it with an INSERT into the `guard` table (see `poste-mailserver-ops` skill for the hex pattern).