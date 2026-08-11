# Compliance Framework — Legal Recon & Outreach Protocol

**Purpose:** Define the legal boundary between pre-engagement public OSINT and post-engagement authorized testing.

## The Golden Rule

**Before a signed contract of engagement:** Passive public data only. Anything a normal person with a web browser could find.
**After:** Full authorized testing within the scope defined in the contract.

## Phase 1 Data Sources (Always Legal)

Shodan.io, crt.sh, DNS records, WHOIS, HTTP headers (curl -I), SSL cert inspection, website public pages, login pages (HTTP 200), social media, Google/Bing search, job postings, state business registrations, Google Maps/Street View, news articles, OpenStreetMap APIs.

## The Gray Zone

| Activity | Why Risky | Alternative |
|----------|-----------|-------------|
| Active port scanning (nmap) | Unsolicited packets, CFAA risk | Use Shodan |
| Directory brute-forcing (gobuster) | Many requests guessing hidden pages | Google dork results |
| Vulnerability scanning (Nuclei) | Probes for CVEs, CFAA violation | Wait for contract |
| Login attempts | Clear CFAA violation | Show login page exists |
| Exploitation | Felony | Never |
| Automated scraping | ToS breaches | Manual browsing |
| Social engineering | Fraud | Call as yourself |

## The "Publicly Indexed" Safe Harbor

Safe: "I found this on Shodan" / "I checked crt.sh" / "Your web server returned this URL with a 200."
NOT safe: "I scanned your network" / "I tried logging in" / "I ran exploit code."

## Documentation Rule

Every finding gets: source, URL, date. Protects you if anyone questions the methodology.

Full document: `data/recon/COMPLIANCE-FRAMEWORK.md` in land-agent repo.
