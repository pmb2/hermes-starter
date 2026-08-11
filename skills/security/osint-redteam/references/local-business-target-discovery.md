# Local Business Target Discovery

> Methodology for identifying and cataloging physical small businesses in a geographic area as potential recon targets. Covers the pre-Phase-1 step that feeds domain-level recon.

## Source Effectiveness Matrix

| Source | Automation Viable | Data Quality | Notes |
|--------|-----------------|-------------|-------|
| YellowPages (yellowpages.com) | Yes (curl + JSON-LD) | Moderate | Structured data in LD+JSON script tags. Cloudflare kicks in after ~3-5 queries. |
| ChamberOfCommerce.com | Yes (curl + JSON-LD) | Low - Moderate | LD+JSON in page source. Category filters return same defaults regardless. |
| Google Maps | Blocked - CAPTCHA | High | Requires residential IP or paid API key. |
| Yelp | Blocked - DataDome | High | Enterprise bot protection. |
| BBB (bbb.org) | Partial | Moderate | Some structured data, CAPTCHA on repeated queries. |
| Local Chamber of Commerce sites | Varies | High | Some have member directories; many use ASP.NET or WordPress. |

## Data Extraction Methods

### Method 1: YellowPages JSON-LD (Best for initial harvest)

```bash
# Fetch a YellowPages category listing page
curl -s "https://www.yellowpages.com/schenectady-ny/restaurants" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  -o /tmp/yp_raw.html

# Extract JSON-LD structured data (contains business name, address, phone, category)
python3 -c "
import json, re
html = open('/tmp/yp_raw.html').read()
match = re.search(r'<script[^>]*type=\"application/ld+json\"[^>]*>(.*?)</script>', html, re.DOTALL)
if match:
    data = json.loads(match.group(1))
    items = data if isinstance(data, list) else [data]
    if isinstance(items[0], dict) and 'itemListElement' in items[0]:
        for item in items[0]['itemListElement']:
            biz = item.get('item', {})
            print(f\"{biz.get('name','?')} | {biz.get('address',{}).get('addressLocality','?')} | {biz.get('telephone','?')}\")
"
```

### Method 2: ChamberOfCommerce JSON-LD

```bash
# Fetch pages across multiple cities
for city in "schenectady" "saratoga-springs" "albany" "clifton-park" "your city" "troy"; do
  curl -s "https://www.chamberofcommerce.com/search?what=Business&where=${city}%2C+NY" \
    -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
    -o "/tmp/chamber_${city}.html"
  sleep 1
done

# Extract names from results (note: many results may be filler/spam listings)
grep -oP '"name":"[^"]*"' /tmp/chamber_*.html | sort -u
```

### Method 3: Delegate subagent for parallel scrape (when browser tools unavailable)

When web_search tool is missing and browser CDP is down, use `delegate_task` with `toolsets=["terminal","file"]` to run scraper subagents. The subagent can use curl + jq + grep to extract from business directories.

**Workflow:**
1. Identify target municipalities in the geographic area
2. For each city, fetch YellowPages category pages (restaurants, dentists, real estate, etc.)
3. Extract JSON-LD from each page
4. Deduplicate and categorize
5. Cross-reference with Google Maps API (if key available) for phone/website enrichment

## Categorization & Prioritization Framework

After collection, rank targets by likely attack surface:

| Priority | Category | Rationale |
|----------|----------|-----------|
| **HIGH** | Healthcare providers (medical/dental) | PHI data, patient portals, EMR systems |
| **HIGH** | Law firms | Confidential client data, settlements |
| **HIGH** | Real estate agencies | MLS access, client databases, payment processing |
| **HIGH** | Hotels / Hospitality | POS systems, guest CC data, booking engines |
| **MEDIUM** | Restaurants (independently owned) | POS systems, online ordering platforms |
| **MEDIUM** | Insurance agencies | Client PII, policy management portals |
| **MEDIUM** | Property management | Tenant databases, rent payment systems |
| **MEDIUM** | Gyms / Fitness | Member databases, billing systems |
| **MEDIUM** | IT services / Computer repair | Client network access, privileged credentials |
| **LOW** | Salons, barbers, retail shops | Often minimal digital footprint |
| **LOW** | Auto repair shops | Typically weak IT but limited data value |

## Digital Footprint Indicators by Business Type

Use these to quickly gauge the attack surface of a newly discovered business:

**Has Website?** → Check if HTTPS, CMS type (WordPress is high-value), contact forms, login portals
**Has Online Ordering/Booking?** → Payment processing, user accounts, API integrations
**Has Patient/Client Portal?** → Authentication systems, PII/PHI data
**Has Social Media?** → Employee info, operational patterns, trust-building for social engineering
**Third-party integrations?** → ScheduleOnce, Calendly, Toast, Clover, Square - these have known CVEs and config issues

## Next Step: Per-Business Technical Recon

After target discovery, proceed to per-business technical recon. Each business needs:
- Domain discovery and DNS enumeration (A, MX, NS, TXT)
- HTTP header fingerprinting (server type, CMS, framework detection)
- SSL certificate inspection (validity, issuer, subject, self-signed issues)
- Admin path probing (/admin, /wp-admin, /.git, /.env, /wp-login.php, etc.)
- Email security assessment (SPF/DMARC/DKIM)
- Physical location mapping (Google Maps)

For mass recon on 50+ targets, use batch parallel subagents (15-20 per batch) with terminal-only tools (curl, nslookup, openssl).

> **See `references/batch-terminal-recon.md`** for the full batch recon methodology, documentation template, command templates, and timeout handling.

## The scrapers.json in Action

For production-grade collection, the compiled directory at `references/capital-region-business-directory.md` demonstrates:
- 200+ businesses across 12 municipalities
- 22 business categories
- High-value target identification by category
- Recon methodology workflow (passive → web app → network → social → physical → wireless)

New area methodology:
1. Define geo boundary (zip codes, county, metro area)
2. Identify municipalities within scope
3. For each municipality, scrape YellowPages + ChamberOfCommerce across all relevant categories
4. Merge and deduplicate
5. Categorize by type and priority tier
6. For high-priority targets, proceed to Phase 1 (domain recon)
