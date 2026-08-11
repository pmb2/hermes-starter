# Passive Scan Methodology — Current Exposure Verification

## The Core Principle

Every finding must be **currently verifiable** using only what a web browser or public DNS infrastructure provides. No port scanning, no vulnerability scanners, no login attempts, no unauthorized access.

## Scan Sequence (Ordered by Stealth Level)

### Level 1: DNS Intelligence (Zero Risk)

```bash
# A record resolution
nslookup domain.com
# Or use Python socket.getaddrinfo()

# SPF/DMARC/DKIM checks
nslookup -type=txt domain.com  # Look for v=spf1
nslookup -type=txt _dmarc.domain.com  # DMARC policy

# MX records (email provider exposure)
nslookup -type=mx domain.com
```

**What you learn:** Whether the domain exists, where it's hosted (IP = cloud provider identification), whether email is spoofable (no SPF = domain spoofable).

### Level 2: HTTP Header Analysis

```python
import http.client, ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

conn = http.client.HTTPSConnection("target.com", timeout=10, context=ctx)
conn.request("GET", "/", headers={"User-Agent": "Mozilla/5.0"})
resp = conn.getresponse()
headers = dict(resp.getheaders())

# Check:
# - Server (version disclosure)
# - X-Powered-By (framework disclosure)
# - X-AspNet-Version, X-AspNetMvc-Version (.NET exposure)
# - Strict-Transport-Security (HSTS enabled/disabled)
# - Content-Security-Policy (CSP enabled/disabled)
# - X-Frame-Options (clickjacking protection)
# - X-Content-Type-Options (MIME-sniffing protection)
# - Set-Cookie (session patterns, Secure/HttpOnly flags)
# - Location (redirect targets)
```

**What you learn:** Web server and framework version, security posture (missing headers = vulnerability), internal server names (X-Portal-Node style), session management patterns.

### Level 3: Response Status Code Mapping

Check common paths and classify by response:
- **200** — Resource exists, accessible
- **301/302** — Resource exists, redirects (may be exploitable)
- **401** — Auth required, but resource exists
- **403** — Resource exists but blocked (valuable recon — 403 vs 404 tells attacker the path is real)
- **404** — Does not exist
- **405** — Wrong HTTP method (check Allow header)
- **500** — Server error (may indicate exploitable condition)

**Key paths to check:**
```
/admin, /api, /api/v1, /api/health, /backup, /config, /debug,
/.env, /.git, /wp-admin, /robots.txt, /sitemap.xml, /crossdomain.xml,
/storage, /logs, /vendor, /swagger, /docs, /openapi.json
```

### Level 4: Subdomain Enumeration (Passive)

Guess common subdomain prefixes against the known domain. Each is tested with a single HTTP GET — indistinguishable from a browser loading a page.

```
mail., webmail., owa., vpn., remote., rdp., sso., okta.,
admin., portal., intranet., hr., api., sftp., ftp., files.,
sharepoint., git., jenkins., dev., stage., test., partner.,
extranet., autodiscover.
```

**How response tells the story:**
- **200/301/302** — Subdomain exists, service is live
- **403** — Exists, blocked (likely has security controls)
- **401** — Exists, requires authentication
- **404/ERR_NAME_NOT_RESOLVED** — Does not exist
- **Multiple 403s on a single domain** = company runs many services, has security in place but naming convention exposed

**Interpretation patterns:**
- `vpn.domain.com` → Remote access gateway (critical finding)
- `rdp.domain.com` → Direct RDP exposed (most dangerous — #1 ransomware vector)
- `owa.domain.com` → Exchange/OWA (email accessible from internet)
- `okta.domain.com` → Identity provider exposed
- `files.domain.com` → File server
- `git.domain.com` / `jenkins.domain.com` → Dev infrastructure (CI/CD pipeline exposed)
- `stage.domain.com` / `dev.domain.com` → Staging environment (weaker security)

### Level 5: Page Source Analysis

Download the full HTML + JS for each live service and check:
1. **Google API keys** — Search for `AIza[0-9A-Za-z\-_]{35}` in the source
2. **Other API keys** — Look for `key=`, `token=`, `secret=`, `api_key=` in URLs and scripts
3. **Third-party integrations** — Toast, Clover, Stripe, Square, Braintree references
4. **Internal endpoints** — Fetch/AJAX calls to `/api/` paths not exposed in navigation
5. **Email/phone data** — Business contact info in the source
6. **Version strings** — jQuery, Vue, React, Laravel, ASP.NET versions

### Level 6: Google API Key Verification

When you find a key in page source, test it against Google's free Geocoding API:

```python
# This is a standard API call with a publicly-disclosed key
import urllib.request, json
url = f"https://maps.googleapis.com/maps/api/geocode/json?address=Latham+NY&key={exposed_key}"
resp = json.loads(urllib.request.urlopen(url).read())

if resp['status'] == 'OK':
    print("Key is VALID AND UNRESTRICTED")
elif resp['status'] == 'REQUEST_DENIED':
    print("Key exists but restricted to specific APIs")
```

**Why this is legal:** The key was voluntarily published in the page source by the website owner. You're making a standard API call with it — the same way any visitor's browser does when loading the page's embedded Google Map. You're just reading the response.

### Level 7: Platform Identification

From page source, JS bundle analysis, and response headers, identify the technology stack:
- **Server headers** → nginx, Apache, IIS, Cloudflare, AWS
- **Cookies** → laravel_session (Laravel), PHPSESSID (PHP), ASP.NET_SessionId, JSESSIONID
- **JS framework** → Vue, React, Angular
- **POS/ordering platform** → Toast, Clover, Square, Mealeo, Orders & Rewards
- **E-commerce** → WooCommerce, Shopify, Magento
- **CMS** → WordPress, Drupal, Joomla

## Response Interpretation Map

| What You See | What It Means | Severity |
|-------------|---------------|----------|
| `vpn.domain.com` returns 200 | VPN gateway exposed | CRITICAL |
| `rdp.domain.com` returns 200 | RDP gateway exposed | CRITICAL |
| `okta.domain.com` returns 200 | Identity provider exposed | CRITICAL |
| `files.domain.com` returns 200 (IIS default) | File server, unmaintained | HIGH |
| `owa.domain.com` returns 200 | Exchange/OWA exposed | HIGH |
| No SPF record | Domain is spoofable | HIGH |
| Google API key in source + verified working | Unauthorized API usage possible | HIGH |
| `X-AspNet-Version: 4.0.30319` in headers | .NET version disclosure | MODERATE |
| Missing HSTS header | No HTTPS enforcement | MODERATE |
| No CSP header | No XSS protection | MODERATE |
| `X-Portal-Node: PSrvPrtWebNode1` | Internal server name leaked | MODERATE |
| `robots.txt` with disallowed paths | Hidden paths revealed | LOW |

## The Must-Not-Do List

| Activity | Why Not |
|----------|---------|
| nmap/masscan port scan | Unsolicited packets, CFAA risk, distinguishable from normal traffic |
| gobuster/ffuf directory brute force | Hundreds of requests in seconds, triggers WAF/IDS |
| Nuclei/OpenVAS vulnerability scan | Actively probes for CVEs, attempts to trigger exploits |
| Login/password attempts | Clear unauthorized access attempt |
| Automated crawling at high speed | DoS-adjacent, ToS violation |
| POST/PUT/DELETE to production APIs | Creates records, audit trails, can trigger alerts |
| Running found API keys against paid services | Could generate charges — verify with free services only |

## POC Package Builder

When you find a verified exposure and need to present it to a client:

```markdown
# POC: [Business Name] — [Finding Title]

## What Was Found
[1-2 sentence description of the finding]

## How to Reproduce (Live Demo)
1. [Step-by-step reproduction]
2. [Should take under 60 seconds]
3. [Ends with visible proof]

## The Proof
- [curl/nslookup/browser command that produced the result]
- [Expected output showing the finding]

## Why It Matters
[Business impact in plain English — money, trust, compliance]

## The Ask
"$750 and I show you everything else that's exposed."
```

## Platform-Specific Notes

### Toast POS
- Ordering at `order.businessname.com` or `business.toasttab.com`
- Page source contains Google Maps API keys (common across Toast-based sites)
- Login modal with member ID retrieval
- Mealeo front-end commonly pairs with Toast backend

### POS terminal
- API at `api.clover.com/v3/merchants/{mid}`
- Auth via OAuth token or API key
- Test mode available (`testMode: true`)
- Employee PINs readable from API
- Payment gateway config at `/gateway` endpoint

### Mealeo
- Restaurant ordering front-end for Toast/Clover backends
- Subdomain pattern: `order.businessname.com`
- API paths typically under `/onlineorder/`
- Uses `X-Requested-With: XMLHttpRequest` header
- Session-sensitive: requires `laravel_session` cookie

### Orders & Rewards (OAR)
- Admin at `{restaurant}.cportal.ordersandrewards.com` (restaurant-specific subdomain)
- Frontend at `{subdomain}.ordersandrewards.com`
- Guest checkout available when enabled
- Checkout flow: locations → categories → items → create_and_place → finish
- Payment via third-party integration (Clover, etc.)

## Directory Layout (Reference)

For the full session-specific detail of a worked example (Manhattan Bagel assessment), see `web-application-security-assessment` skill's `references/web-app-pentest-session.md`.

For the full proximity scanning automation script, see `local-biz-scanner-workflow` skill.
