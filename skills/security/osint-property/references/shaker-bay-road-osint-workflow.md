# Shaker Bay Road OSINT — Full Workflow Reference

## The Query
> "Who owns all the houses in Shaker Bay... which families own which houses, what do they do for a living, and how much are the houses... Shaker Bay and Leatham were in Colony, New York"

## Placename Resolution

| Heard | Actual | How Resolved |
|-------|--------|-------------|
| "Shaker Bay" | **Shaker Bay Road** (residential street) | OSM Nominatim API confirmed it's a road, not a body of water |
| "Leatham" | **Latham** (hamlet in Colonie) | Wikipedia search → Latham, NY |
| "Colony" | **Colonie** (town in Albany County) | Wikipedia → Colonie is pronounced /kəˈloʊni/ |

## Tools Used

| Tool | Purpose | What It Returned |
|------|---------|-----------------|
| **OSM Nominatim API** | Location lookup | Exact coordinates, zip code (12110), road classification |
| **OSM API (v0.6)** | Road geometry | 80+ nodes along ~0.5 mile road, 2 segments |
| **Playwright MCP Browser** | Web research (Bing, Google, CountyOffice.org) | All property data below |
| **CountyOffice.org** | Aggregated property records | 41 addresses with values, taxes, specs |
| **Google AI Overview** | Owner name extraction | Hellert Family, James D. Finning, Shaker Bay Properties LLC |
| **FastPeopleSearch** | Free occupant lookup | "Shannon Older" at 2 Shaker Bay Rd |
| **FamilyTreeNow** | Free occupant lookup | "Sheila Nelson" + relatives at 31 Shaker Bay Rd |

## Blockers Encountered

| Blocker | Workaround |
|---------|-----------|
| No `web_search` tool available | Use Playwright MCP browser for all web research |
| DuckDuckGo captcha | Use Bing via Playwright instead |
| Google JS dependency | Use Playwright (renders JS) instead of curl |
| Zillow/Redfin 403 blocks | Use aggregator sites (CountyOffice.org, NeighborWho) |
| Owner names behind paywall on CountyOffice | Google AI Overview extracts names from free previews |
| OSM Overpass API 406 error | Use raw OSM API (v0.6) endpoints directly |
| Albany County portal blocked | Use third-party aggregators |

## Property Data Summary (41 addresses)

- **Median assessed market value:** ~$1.35M
- **Range:** $149,600 (vacant land at 37A) to $4,347,800 (21 Shaker Bay Rd)
- **Highest sale:** 25 Shaker Bay Rd — $6,947,500 (Aug 2012)
- **Median tax bill:** $29,409/year
- **Highest tax:** 21 Shaker Bay Rd — $73,000/year
- **Most common year built:** 2005 (cluster of construction)
- **Average lot size:** ~2.5 acres
- **Biggest lot:** 37A Shaker Bay Rd — 12.6 acres (specialized residential)
- **Largest house:** 21 Shaker Bay Rd — 15,838 sqft, 7 bed/7.5 bath, 8.35 acres

## Confirmed Families

| Address | Name(s) | Source |
|---------|---------|--------|
| 20 Shaker Bay Rd | **Hellert** — Dianne C. Hellert Revocable Living Trust | Google AI Overview |
| 29 Shaker Bay Rd | **Finning** — James D. Finning | Google AI Overview |
| 31 Shaker Bay Rd | **Nelson** — Sheila Nelson (b. Feb 1968) + relatives | FamilyTreeNow |
| 2 Shaker Bay Rd | **Older** — Shannon Older (most recent tenant) | FastPeopleSearch |
| 21 Shaker Bay Rd | **Shaker Bay Properties, LLC** (developer) | Redfin listing |
| Street-wide | Fusco, Cocca, and Connery Families | AI Overview |

## Key URLs

- CountyOffice: https://www.countyoffice.org/shaker-bay-rd-latham-ny-property-records/
- OSM Way (Shaker Bay Rd): https://www.openstreetmap.org/way/62034370
- Latham Wikipedia: https://en.wikipedia.org/wiki/Latham,_New_York
- Colonie Wikipedia: https://en.wikipedia.org/wiki/Colonie,_New_York
