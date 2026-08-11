# Programmatic API Key Registration (mail.tm)

When a service requires email verification to generate an API key (The Odds API, etc.), use the **mail.tm API** to create a disposable inbox that can be checked programmatically. This avoids the time-pressure issue of browser-based verification codes that expire in 30-60 seconds.

## Steps

### 1. Get a valid domain

```bash
curl -s https://api.mail.tm/domains
```

Returns one or more valid domains (e.g., `web-library.net`).

### 2. Create a mailbox

```bash
DOMAIN="web-library.net"
RAND_ID=$(date +%s | tail -c 8)
EMAIL="${RAND_ID}@${DOMAIN}"

curl -s https://api.mail.tm/accounts -X POST \
  -H "Content-Type: application/json" \
  -d "{\"address\":\"${EMAIL}\",\"password\":\"TempPass123!\"}"
```

### 3. Get auth token

```bash
TOKEN=$(curl -s https://api.mail.tm/token -X POST \
  -H "Content-Type: application/json" \
  -d "{\"address\":\"${EMAIL}\",\"password\":\"TempPass123!\"}" | \
  python -c "import sys,json; print(json.load(sys.stdin).get('token',''))")
```

### 4. Register at the service (via browser)

Use the `@${DOMAIN}` email when registering. The verification code will arrive in the mail.tm inbox.

### 5. Fetch the verification code

```bash
# Check for messages
curl -s https://api.mail.tm/messages \
  -H "Authorization: Bearer ${TOKEN}"

# Get the latest message ID
MSG_ID=$(curl -s https://api.mail.tm/messages \
  -H "Authorization: Bearer ${TOKEN}" | \
  python -c "import sys,json; m=json.load(sys.stdin).get('hydra:member',[]); print(m[0]['id'] if m else '')")

# Read the verification code
curl -s "https://api.mail.tm/messages/${MSG_ID}" \
  -H "Authorization: Bearer ${TOKEN}" | \
  python -c "import sys,json; print(json.load(sys.stdin).get('text',''))"
```

### 6. Paste the code in the browser

Codes expire in ~30-60 seconds, so have the browser ready on the confirmation screen before fetching.

## Why not temp-mail.io?

temp-mail.io is more popular but has blockers:
- The email field is **read-only** — you can't type a custom email
- Changing the address requires their widget with domain selection
- The free tier doesn't let you pick a custom email prefix
- No official API for scriptable access

mail.tm has a clean REST API with full CRUD on accounts and messages.
