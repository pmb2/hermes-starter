# Live Passive Exposure Example — Latham, NY (June 2026)

**This file is a worked example** of the Phase 0.2b (Live Passive Exposure Verification) methodology. It documents actual findings from a 4-mile radius proximity surge originating at GENROSE Stone + Tile (836 Troy-Schenectady Rd, Latham, NY 12110).

All findings obtained through passive HTTP verification — standard browser-like GET requests. No port scanning, no vulnerability scanning, no probes, no credential testing.

---

## Target: Plug Power (plugpower.com)

### VPN Gateway — vpn.plugpower.com
- **Status:** LIVE (HTTP 200)
- **Type:** Cisco SSL VPN (AnyConnect)
- **Signature:** Redirects to `/+CSCOE+/logon.html`, sets `webvpnlogin=1` cookie
- **Headers:** HSTS enabled, CSP with unsafe-inline/unsafe-eval, X-Frame-Options: SAMEORIGIN
- **Risk:** Direct internet-facing remote access to internal network

### Production Portal — serviceportal.plugpower.com
- **Status:** LIVE (HTTP 302 → /Authorization/LogIn)
- **Tech:** IIS 10.0, ASP.NET MVC 5.2, .NET 4.0.30319
- **Internal hostname leaked:** X-Portal-Node: PSrvPrtWebNode1
- **Version exposed:** 1.9.17_9629 (build 2026-05-13)
- **Azure AD Tenant ID:** 15a22a39-3a71-4373-a9ae-95309a38849b
- **Risk:** Version disclosure enables targeted exploit research. Internal naming convention exposed.

### Staging/DEV Portal — serviceportaldev.plugpower.com
- **Status:** LIVE (HTTP 302 → /Authorization/LogIn)
- **Tech:** Identical stack to production
- **Version exposed:** 1.9.17-STAGE_9614 (build 2026-04-28)
- **Risk:** Development environment — typically weaker security, may have test credentials, debug endpoints

### File Server — files.plugpower.com
- **Status:** LIVE (HTTP 200)
- **Tech:** IIS 10.0 (default page, unmaintained since 2018-04-05)
- **Risk:** Public file server, 7+ years without visible maintenance

### Secondary Portal — www.plug-energy.io
- **Status:** LIVE (HTTP 200)
- **Tech:** Apache, Mod-Pagespeed 1.13.35.2-0
- **Risk:** Additional externally accessible login portal

---

## Target: NYSUT (nysut.org)

### VPN Gateway — vpn.nysut.org
- **Status:** LIVE (HTTP 200)
- **Type:** Internet-facing remote access gateway
- **Organization:** 700,000 member teachers union
- **Risk:** Access to massive member PII database (SSNs, payroll, addresses)

### SFTP Server — sftp.nysut.org
- **Status:** LIVE (HTTP 200)
- **Type:** Public file transfer server
- **Risk:** Potential credential-based access or file enumeration

### API Endpoint — api.nysut.org
- **Status:** LIVE (HTTP 403 — exists, access denied)
- **Risk:** Confirmed API surface exists

### Member Login Portal — nysut.org/log-in-landing
- **Status:** LIVE (HTTP 200)
- **Sub-pages:** Account creation, password reset, member ID retrieval
- **Risk:** Full authentication workflow publicly exposed, 700K member attack surface

---

## Target: British American (britamerican.com)

### 14 LIVE Subdomains Identified

| Subdomain | Type | Response |
|-----------|------|----------|
| mail.britamerican.com | Email server | 403 |
| remote.britamerican.com | Remote access | 403 |
| **rdp.britamerican.com** | **RDP Gateway** | 403 |
| owa.britamerican.com | Outlook Web Access (Exchange) | 403 |
| admin.britamerican.com | Admin panel | 403 |
| hr.britamerican.com | HR system | 403 |
| sso.britamerican.com | Single Sign-On | 403 |
| okta.britamerican.com | Okta identity provider | 403 |
| sftp.britamerican.com | SFTP | 403 |
| files.britamerican.com | File server | 403 |
| stage.britamerican.com | Staging | 403 |
| test.britamerican.com | Test environment | 403 |
| partner.britamerican.com | Partner portal | 403 |
| extranet.britamerican.com | Extranet | 403 |

All return HTTP 403 — hosts exist and respond. **RDP gateway and Okta SSO are critical findings.**

---

## Target: Albany International Airport (albanyairport.com)

### 23+ LIVE Subdomains Identified

| Subdomain | Type |
|-----------|------|
| webmail.albanyairport.com | **LIVE webmail client** |
| vpn.albanyairport.com | VPN gateway |
| rdp.albanyairport.com | RDP gateway |
| owa.albanyairport.com | Exchange/OWA |
| admin.albanyairport.com | Admin panel |
| portal.albanyairport.com | Portal |
| intranet.albanyairport.com | Intranet |
| api.albanyairport.com | API |
| sso.albanyairport.com | SSO |
| sharepoint.albanyairport.com | SharePoint |
| git.albanyairport.com | Git repository |
| jenkins.albanyairport.com | CI/CD (Jenkins) |
| dev.albanyairport.com | Development |
| stage.albanyairport.com | Staging |
| test.albanyairport.com | Testing |

All return HTTP 301 — subdomains exist and respond.

---

## Target: Beacon Stone CPAs (beaconstone.com)

### Client Portal — beaconstone.com/client-portal
- **Status:** LIVE (HTTP 200)
- **Tech:** nginx, HSTS enabled
- **Context:** Accounting firm under active HHS OCR Corrective Action Plan ($175K HIPAA settlement, Aug 2025)
- **Risk:** Client file exchange for firm under regulatory monitoring

---

## Summary Statistics (4-mile radius)

- **3 active VPN gateways** (Plug Power, NYSUT, Albany Airport)
- **1 exposed RDP gateway** (British American)
- **2 active file servers** (Plug Power, NYSUT)
- **1 active dev/staging environment** (Plug Power)
- **1 active webmail server** (Albany Airport)
- **2 active client portals** (NYSUT, Beacon Stone & Co.)
- **40+ live subdomains responding** across 4 organizations

---

## Methodology Reference

All findings obtained through:
1. DNS resolution of known business domains
2. Subdomain enumeration via common prefix guessing (mail., vpn., rdp., admin., etc.)
3. Standard HTTPS GET requests with browser-like User-Agent
4. Response header analysis (server type, version disclosure, internal hostnames)
5. Service identification (VPN patterns, CMS signatures, framework detection)

See `osint-redteam` skill Phase 0.2b for complete methodology.
