# Small Business POC Pipeline
## Converting Passive Findings into Client Demonstrations

---

## Overview

This reference covers the end-to-end process of taking passive exposure findings (Phase 0.2b) and converting them into a demonstrable Proof of Concept that closes small business clients. The POC must be:

1. **Verifiable** — The client can see it work with their own eyes
2. **Read-only** — No data access, no modification, no exploitation
3. **Immediately understandable** — A non-technical business owner gets it in 30 seconds
4. **Actionable** — Points directly to a fix they can pay for

---

## POC #1: Google API Key Exposure (Most Common)

### Detection
Google Maps API keys are typically 39 characters starting with `AIzaSy`. They appear in:
- `<script>` tags loading the Google Maps JavaScript API
- `<img>` tags for static map images
- Hidden config objects in page source

### Verification
```bash
# Test if the key is unrestricted against Geocoding API
curl -s "https://maps.googleapis.com/maps/api/geocode/json?address=Test&key=AIzaSy..."
# Response "status": "OK" means the key is valid and unrestricted
# Response "status": "REQUEST_DENIED" means restricted to different API
# Response 404 means invalid key
```

### Client Script
> "I opened your website and found a Google API key in the code. I tested it -- it works from my computer. Anyone who visits your site and views the page source can copy this key and use it to make Google API calls on your billing account. You're paying for whatever someone decides to run on this key."

---

## POC #2: Email Spoofing

### Detection
Check SPF and DMARC DNS records for the target domain.

### Verification
```bash
nslookup -type=txt targetdomain.com
# No "v=spf1" = no SPF

nslookup -type=txt _dmarc.targetdomain.com  
# No DMARC or "p=none" = no enforcement
```

### Client Script
> "Your domain has no email authentication. I could send an email right now that looks like it comes from your business, and most email providers would deliver it. Your suppliers, your delivery partners -- anyone who gets emails from you is at risk of impersonation."

---

## POC #3: Missing Security Headers

### Detection
```bash
curl -sI https://order.targetbusiness.com/
# Check for: Strict-Transport-Security, Content-Security-Policy,
# X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy
```

### Client Script
> "Your ordering portal has none of the standard security headers. That means customer sessions could be intercepted on public WiFi, or your checkout page could be embedded in a fake site. For a site where people enter payment information, these should all be in place."

---

## POC #4: Exposed WordPress Admin Panel

### Detection
Check for the WordPress login page and associated exposure endpoints:

```bash
# Check wp-admin path
curl -s -o /dev/null -w "HTTP %{http_code}" https://target.com/wp-admin
# 200 = exposed login page
# 403 = exists but IP-restricted
# 404 = no WordPress at standard path

# Check for additional WP exposure
for path in /xmlrpc.php /wp-json /readme.html /license.txt /wp-content/debug.log /wp-config.php; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://target.com$path")
  echo "$code $path"
done
```

**Response interpretation:**
- `/wp-admin` returns 200 = WordPress login page is publicly accessible
- `/xmlrpc.php` returns 200 = XML-RPC enabled (brute force vector for password guessing)
- `/wp-json` returns 200 = WordPress REST API exposed (can enumerate users, posts, plugins)
- `/readme.html` returns 200 = WordPress version disclosure
- `/wp-config.php` returns anything other than 404 = file EXISTS and should be protected (contains database credentials)
- `/wp-content/debug.log` returns anything other than 404 = debug logging enabled (may contain PHP errors, SQL queries, stack traces)

### Client Script
> "Your website's admin login page is accessible at [domain]/wp-admin. Anyone on the internet can see this. They can try to guess your password, exploit known WordPress vulnerabilities, or use the XML-RPC endpoint to brute-force credentials. For a [title company / medical practice] that handles sensitive data, this is the most common entry point for attackers."

---

## POC #5: Exposed VPN/Remote Access Gateway

### Detection (passive HTTP check)

```bash
curl -sI https://vpn.target.com/ | head -20
# Look for: Location: /+CSCOE+/logon.html (Cisco VPN)
# Look for: webvpnlogin=1 cookie (Cisco AnyConnect)
# Look for: /Remote/ or /RDWeb/ in redirect (Microsoft RDP Gateway)
```

### Client Script (for enterprises)
> "Your VPN gateway is publicly accessible at vpn.yourcompany.com. VPNs are the #1 initial access vector in every major breach report — attackers don't hack in through firewalls, they log in through VPNs. If a single employee's credentials get phished, the attacker has full network access."

---

## Key Verification Details

### Google API Key Referrer Restrictions
When testing Google API keys, verify whether HTTP referrer restrictions are actually enforced:

```bash
# Test WITHOUT referer header (most restrictive test)
curl -s "https://maps.googleapis.com/maps/api/geocode/json?address=Test&key=KEY"

# Test WITH a matching referer
curl -s -H "Referer: https://target.com/" "https://maps.googleapis.com/maps/api/geocode/json?address=Test&key=KEY"

# Test WITH a non-matching referer (should fail if restricted)
curl -s -H "Referer: https://evil.com/" "https://maps.googleapis.com/maps/api/geocode/json?address=Test&key=KEY"
```

A key that says "HTTP referrer restricted" in the Google Cloud Console but works WITHOUT any referer header is effectively unrestricted. A key that works with a non-matching referer is completely open.

### Multi-Sample Rule for Re-Verification
Run each check 3 times over 30 seconds. A single fluke 401 on a token that normally returns 200 could be a transient auth issue. Three 401s in a row = definitive revocation.

---

## The 5-Minute Demo Script

This is the core of the pitch. Learn it.

```
:00  Open the target's website in a browser
:15  Right-click -> "View Page Source"
:25  Search for "AIzaSy" (or whatever pattern fits)
:35  Copy the API key
:45  Open a new tab with the test URL including the key
:55  Show the JSON response — "status": "OK"
1:05  "This key works from any computer, anywhere."
1:15  "I found this in 30 seconds by looking at your website."

1:30  "Your domain doesn't have email authentication either."
1:40  "I could send emails that look like they're from you."
1:50  "And your ordering portal has no security headers."
2:00  "Three things. Found without any hacking tools."

2:30  "For $750 I do a full scan of your entire digital footprint."
2:45  "You get a one-page report with exactly what needs fixing."
3:00  "Most fixes take an afternoon once you know what to fix."

4:00  Hand them the one-page summary
5:00  Close
```

---

## Pricing Table (for the one-pager)

| Service | Price | What You Get |
|---------|-------|-------------|
| Surface Scan | $750 | Full digital footprint, API keys, email security, headers |
| Standard Assessment | $2,500 | Surface scan + phishing test + written report |
| Annual Protection | $1,500/yr | Quarterly scans + dark web monitoring + phone support |

---

## Common Pitfalls

- **PITFALL:** Testing Google API keys against a write endpoint (Maps API write, Sheets API). Only test read-only endpoints to avoid creating or modifying data.

- **PITFALL:** A 403 response from a subdomain doesn't mean nothing is there. 403 means the endpoint exists and is blocking you. Document it as "confirmed live, access restricted."

- **PITFALL:** Small business owners don't care about CVEs or CVSS scores. Translate everything into money: "This could cost you $" not "This is a CVE-2024-XXXXX with CVSS 7.5."

- **PITFALL:** Don't lead with worst-case. Start with the simplest, most visual finding (API key in page source). Build to the more abstract ones (email spoofing, headers) only if they're still engaged.

- **PITFALL:** If the client gets defensive ("we use [vendor], they handle security"), don't argue. Say "I'm sure they do. This is just what I found from the outside. Would you like me to send you the details?" and leave the ball in their court.

---

## Example: Latham Bagel Shop

A fully worked example is available at:
`${USER_HOME}\hermes-output\latham-bagel-poc-package.md` (POC demonstrations)
`${USER_HOME}\hermes-output\latham-bagel-shop-pitch-package.md` (Full pitch package)
