# New York State Business Entity Search

## Status (June 2026)

The NY Department of State has migrated from the legacy `appext20.dos.ny.gov` system to a new platform. The old direct search URL (`/corp_public/CORPSEARCH.INPUT`) is permanently shut down and returns a "page unavailable" redirect.

## Current Access Paths

### 1. DOS Corporation & Business Entity Database

**URL:** https://www.dos.ny.gov/corporation-and-business-entity-database

This is the current landing page for business entity searches. From here you can access the search portal. Note: this page may occasionally redirect or be unavailable during the ongoing migration.

### 2. UCC E-Filing Portal (Separate System)

**URL:** https://ucc-efiling.dos.ny.gov

This portal handles UCC financing statements (liens, secured transactions). It uses the "Cenuity Online" platform. It has a public search function for debtor names. Even when the corporation database is down, this system may be operational since it runs on a different platform.

**What UCC filings reveal:**
- The exact legal entity name of the debtor
- Secured party (lender) information
- Equipment loans, leases, and supply agreements
- Business addresses

### 3. NY Open Data (Socrata Portal)

**URL:** https://data.ny.gov

The state maintains various business-related datasets. The correct API endpoint for a given dataset can be found by searching data.ny.gov for the dataset name. Common datasets include:

- **Corporation/Business Entity Data** - Search for "corporation" or "business entity" on data.ny.gov to find the current dataset ID
- **Food Service Establishment Licenses** - Dataset ID varies, contains DBA names and business entities for restaurants
- **Sales Tax Registrants** - Contains registered business names and addresses

**API Query Pattern:**
```bash
# After finding the correct dataset ID (e.g., "abcd-1234"):
curl -s "https://data.ny.gov/resource/abcd-1234.json?%24limit=10"

# Search by name:
curl -s "https://data.ny.gov/resource/abcd-1234.json?entity_name=MANHATTAN+BISTRO"

# The Socrata SODA API uses SoQL (Socrata Query Language):
# %24where=clause  — WHERE clause
# %24limit=N       — limit results
# %24q=term        — full-text search
```

### 4. County Clerk Records (Alternative)

When the state database is unavailable, check the county clerk in the business's operating county. Business certificates (Doing Business As / DBAs) and assumed name filings are registered at the county level.

**For Schenectady County (example):**
- Schenectady County Clerk's Office
- 620 State Street, Schenectady, NY 12307
- Online records portal may be available through the county website

## Failover Strategy

If all NY DOS paths are blocked:

1. **OpenCorporates** — Requires API key for automated access, but web searches may work from a browser
2. **Better Business Bureau** — www.bbb.org — Business profiles include years in operation, ownership contact
3. **Facebook Business Page** — Check about section for business history and ownership
4. **Google Maps/Business Profile** — Often lists ownership, hours, and years established
5. **MerchantCircle / Yelp / other directories** — May have owner names
6. **Secretary of State in formation state** — If the business is an LLC/Corp formed in Delaware (common), check Delaware first
7. **County property records** — If the business owns real estate, the tax bill shows the owner name
