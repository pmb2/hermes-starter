# Court Docket & Record Access Guide

## Lee County, FL

### Court Cases — Matrix (matrix.leeclerk.org)
- **URL:** https://matrix.leeclerk.org/
- **Access method:** `mcp_chrome_devtools_mcp_new_page(url)` — works without registration for party name searches
- **Form fields:** First Name (`Pa*` wildcard), Last Name (`Backus`)
- **Validation:** First name requires ≥2 chars + wildcard (e.g. `Pa*`). Bare `*` rejected.
- **Case types:** All checked by default (Adult Felony, Appeals, Circuit/County Civil, etc.)
- **Search tips:** Wildcard searches — enter part of name then `*`. Search by last name only: put `*` in First Name, last name in Last Name.
- **Business search:** Requires free registered user account at matrix.leeclerk.org/UserAccount/NewUser
- **Limits:** 500 case results max; 200 hearing results max
- **Date format:** MM/DD/YYYY

### Official Records — LandMarkWeb (or.leeclerk.org/LandMarkWeb/)
- **URL:** https://or.leeclerk.org/LandMarkWeb/
- **Access method:** `mcp_chrome_devtools_mcp_new_page(url)` — SPA with JS routing
- **Search types:** Name, Document, Case Number, Book/Page, Consideration, Record Date, Clerk File Number, Legal
- **Records covered:** Liens, judgments, deeds, mortgages, tax deeds, lis pendens, marriage licenses, evictions, foreclosures, satisfactions, assignments
- **SPA Gotchas:**
  - Clicking Name Search icon may not update accessibility snapshot immediately
  - Direct URL navigation to `/Search/Name` returns 404 — must use JS routing
  - Quick Search dropdown has "I want to see all documents with my name on them" option
  - Use `mcp_chrome_devtools_mcp_evaluate_script()` to invoke JS functions when clicks don't reflect in snapshot
- **Akamai block (confirmed Jun 2026):** The landing page loads and the Disclaimer dialog appears. Clicking Accept navigates to a search page that returns `Access Denied` via `errors.edgesuite.net`. Same Akamai CDN block as Matrix. No automated alternative for official records search. Mark BLOCKED and recommend manual check via human-operated browser.

## New York State

### WebCivil (Civil Cases)
- **URL:** https://iapps.courts.state.ny.us/webcivil/FCASearch
- **Access:** Typically redirects to CAPTCHA on automated access
- **CAPTCHA detection:** Check URL for `webcivil/captcha` — if detected, mark as BLOCKED immediately
- **Alternative:** Manual search at same URL via human-operated browser

### NYSCEF (eFiling)
- **URL:** https://www.nycourts.gov/efs/
- **Access:** CAPTCHA protected; requires manual access
- **Not available** via automation from this environment

## Federal

### PACER (pacer.uscourts.gov)
- **Status:** Paid account required. Not accessible from this environment.
- **Covers:** Federal district/bankruptcy/appellate court dockets

## Documenting Blocks in Reports

When a source is blocked by CAPTCHA, include in the report:
```
### NY eCourts — CAPTCHA Blocked
Automated access not possible. Requires manual check via web browser.
```
