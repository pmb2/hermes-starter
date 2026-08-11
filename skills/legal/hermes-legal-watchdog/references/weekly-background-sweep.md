# Weekly Background Sweep — Site Access Matrix

> Last updated: 2026-06-19 (sweep date)
> Maintained for use by the Weekly Background Sweep cron job (Mon 10AM)

---

## Search Engines

| Engine | URL Pattern | Access | Notes |
|--------|------------|--------|-------|
| DuckDuckGo Lite | `lite.duckduckgo.com/lite/?q=<query>` | ✅ curl + browser | Best primary option. Simple HTML table output. No CAPTCHA. |
| DuckDuckGo HTML | `html.duckduckgo.com/html/?q=<query>` | ✅ curl + browser | Richer results but harder to parse. |
| DuckDuckGo API | `api.duckduckgo.com/?q=<query>&format=json` | ✅ curl | Zero-hit API for most person queries (returns empty). Not useful. |
| Bing | `bing.com/search?q=<query>` | ❌ CAPTCHA | Turnstile captcha blocks automated requests from this IP. |
| Google | `google.com/search?q=<query>` | ❌ CAPTCHA | reCAPTCHA blocks every automated request. Avoid. |

---

## County / Local Court & Property Records

### Lee County, FL

| Site | URL | Access | Purpose |
|------|-----|--------|---------|
| Clerk of Court Records | `matrix.leeclerk.org/` | ✅ CDP browser | Court case search (felony, civil, small claims, traffic, etc.) |
| Official Records Search | `or.leeclerk.org/LandMarkWeb/` | ✅ CDP browser | Deeds, liens, judgments, official documents |
| Property Appraiser | `leepa.org/` | ✅ curl + browser | Owner name search for property/tax info |
| Clerk Home | `leeclerk.org/` | ✅ curl + browser | General information |

**Lee Clerk search form fields** (matrix.leeclerk.org):
- First Name: wildcard `*` or specific
- Last Name: required
- Middle Name: optional
- Case Number or Citation Number: optional
- Date range: optional
- All case types checked by default
- Max results: 500

### Lee County, FL — Official Records Search (LandMarkWeb):

Search types available:
- **Name Search** — search by grantor/grantee name
- **Document Search** — by document type (deed, mortgage, lien, etc.)
- **Case Number Search**
- **Record Date Search** — date range
- **Consideration Search** — by dollar amount

---

### New York

| Site | URL | Access | Notes |
|------|-----|--------|-------|
| NY Unified Court System (ecourts) | `iapps.courts.state.ny.us/webcivil/ecourtsMain` | ⚠️ Cloudflare | Blocked from curl. Try CDP browser and accept challenge. |
| NY Court of Appeals | `nycourts.gov/courts/appeals/` | ✅ curl | General info only |
| Albany County Clerk | `albanycountyny.gov/departments/county-clerk` | ❌ 403 | Blocked at network level. |
| Albany County Real Property | `albanycountyny.gov/departments/real-property-tax-service` | ❌ 403 | Blocked at network level. |

---

### Florida Statewide

| Site | URL | Access | Notes |
|------|-----|--------|-------|
| Florida Courts eDocket | `courtwebprod.flcourts.org/oss` | ❌ Unreachable | DNS/network failure from this environment. |
| FL Online Services | `onlineservices.flcourts.org/ezDPS/` | ❌ Unreachable | Same. |
| FL Clerks of Court | `flclerks.com/` | ✅ curl + browser | General portal with county links. |
| FL Supreme Court | `floridasupremecourt.org/` | ✅ curl | Docket search available. |
| FL Court Public Records | `publicfiles.flcourts.gov/` | ❌ Unreachable | HTTP 000 — no route. |

---

### Federal Courts

| Site | URL | Access | Notes |
|------|-----|--------|-------|
| PACER Case Locator | `pcl.uscourts.gov/pcl/index.jsf` | 🔒 Login required | Anonymous browsing limited. Party search available after login. |
| PACER Home | `pacer.uscourts.gov` | 🔒 Login required | Registration free; per-page fees apply ($0.10). |
| CourtListener | `courtlistener.com` | ✅ curl + browser | Free alternative. Search by name for federal cases. |

---

## People Search / Data Broker Sites

| Site | Access | Data Quality | Notes |
|------|--------|-------------|-------|
| `mylife.com/the operator-backus/` | ⚠️ Cloudflare (browser) | LOW | Shows ~35 records for the operator across US. Boilerplate text repeated per entry. "At least 1 Lawsuit" is generic — same text on every profile. |
| `spokeo.com/the operator-Backus` | ✅ curl (indexed) | LOW | 52 matches. Generic people-search directory. Paywalled for details. |
| `ny.allrecentarrests.org/arrest-report/the operator-Backus/*` | ✅ curl | VERY LOW | Auto-generated pages. Key indicators of false positive: no inmate ID, no photo, "Unknown" facility, no charges. See data broker reliability table in SKILL.md. |
| `familytreenow.com` | ⚠️ Requires interaction | LOW | Genealogy-based people search. |

---

## Data Broker Reliability: allrecentarrests.org Profile

```
Page URL:     ny.allrecentarrests.org/arrest-report/the operator-Backus/1649468/
Schema.org data:
  - Name: the operator
  - Gender: Male
  - Inmate ID: Unknown
  - Photo: None (placeholder)
  - Facility: Unknown (Schenectady, NY)
  - Description: "currently incarcerated at Unknown in Schenectady, New York"
  - Date modified: 2026-03-10
  - Charges: None listed
  - Booking/arrest dates: None

Assessment: FALSE POSITIVE — no verifiable identifiers. The site auto-generates 
pages for scraped names. Without an inmate ID, booking photo, or charges, this 
is speculative data aggregation, not an actual arrest record.
```

---

## Refresh Notes

- This matrix should be refreshed quarterly or whenever a major site changes its access pattern.
- When a previously-accessible site becomes blocked, note it here and try alternative access methods (CDP browser vs curl, different User-Agent, etc.).
- When a new jurisdiction becomes active, add it to this matrix and the SKILL.md procedure.
