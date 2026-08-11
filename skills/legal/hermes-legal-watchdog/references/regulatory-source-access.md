# Regulatory Source Access Guide

## Source Access Matrix

| Source | URL | Access Method | Parse Strategy | Gotchas |
|--------|-----|--------------|----------------|---------|
| IRS Newsroom | irs.gov/newsroom | CDP browser new_page | Snapshot (full) reads list of IR-YYYY-XX releases | Drupal site — works well in browser |
| FL Admin Register | flrules.org | CDP browser only | Snapshot; /gateway/recentIssue.asp returns PDF | Cloudflare blocks curl entirely |
| FL Senate Bills | flsenate.gov/Session/Bills | CDP browser or curl | Snapshot for full bill list; curl with grep for quick search | 942+ Senate bills in 2026; paginated (19 pages) |
| Lee County Ordinances | leegov.com/bocc/ordinances | CDP browser only | Snapshot lists year; year filter uses JavaScript | SharePoint — curl returns unrendered HTML |
| Laws of Florida | laws.flrules.org | CDP or curl | PDF download | Hosted separately from main flrules.org |
| Lee County Codified | library.municode.com/fl/lee_county/codes/code_of_ordinances | CDP browser | Snapshot + navigation | Searchable, up-to-date codification |

## Lee County Ordinance Numbering Convention

- **YY-NN** format: `26-01` = first ordinance of 2026, `25-10` = 10th ordinance of 2025
- **89-02** = The Lee Plan (comprehensive plan) — this is the foundational land-use document that CPA (Comprehensive Plan Amendment) ordinances modify
- **LDC** = Land Development Code (codified in County Code Chapters 1-34+)
- **CPA** = Comprehensive Plan Amendment — modifies 89-02
- **CDD** = Community Development District

### Key LDC Chapters for Real Estate
| Chapter | Subject |
|---------|---------|
| Ch. 2 | Administration & Procedures |
| Ch. 6 | Impact Fees & Building Regulations |
| Ch. 10 | Planning & Community Regulations |
| Ch. 12 | Environmental & Mining Regulations |
| Ch. 14 | Public Facilities |
| Ch. 22 | Parks & Recreation |
| Ch. 26 | Docks, Boat Ramps, Shoreline Structures |
| Ch. 30 | Signs |
| Ch. 33 | Zoning |
| Ch. 34 | Land Development Code definitions & general provisions |

## Session Timing Notes

| Jurisdiction | Cycle | Key Dates |
|--------------|-------|-----------|
| FL Legislature | Annual regular session | Jan-Mar (2026 ended 3/13) |
| US Congress (OBBB) | 2026 | One, Big, Beautiful Bill enacted — implementing guidance rolling out |
| Lee County BOCC | Year-round meetings | Ordinances pass throughout year |
| IRS Guidance | Continuous | Newsroom releases weekly during tax season |

## proven URL Search Patterns

### FL Senate Bills by Keyword
```
https://www.flsenate.gov/Session/Bills?SearchText=real+estate&SessionYear=2026&Chamber=senate&SearchOnlyCurrentVersion=true
```

### Most Recent FAR Issue
```
https://flrules.org/gateway/recentIssue.asp
```

### Lee County Ordinances by Year (appends to URL via JS)
```
https://www.leegov.com/bocc/ordinances
```
Then select year from dropdown. Current year shows all YY-XX ordinances.

### Federal Register — Agency ID Reference & Full-Text Extraction

### Agency IDs
**⚠️ WARNING — This file previously had conflicting agency IDs (77/83/179/85) here that did not match the confirmed-working IDs in the main SKILL.md and `references/federal-register-api-ids.md`.** Use `references/federal-register-api-ids.md` as the authoritative agency ID reference. Convenience summary of confirmed-working IDs:

| Agency | agency_id | Verified |
|--------|-----------|----------|
| FTC | 192 | ✓ Jul 2026 sweep — returned FTC AI statement |
| GSA | 210 | ✓ Jul 2026 sweep — returned FAR overhaul docs |
| DOL | 271 | Listed in federal-register-api-ids.md (139 tested, 0 results) |
| SBA | (see federal-register-api-ids.md) | Not verified via ID filter |
| OFPP | 184 | Child of OMB=280 |
| DoD | 103 | From SKILL.md |

**Working curl example — FTC AI rules:**
```bash
curl -sL --max-time 15 "https://www.federalregister.gov/api/v1/articles.json?conditions%5Bagency_ids%5D%5B%5D=192&conditions%5Bpublication_date%5D%5Bgte%5D=2026-01-01&conditions%5Bterm%5D=AI&order=newest&per_page=5"
```

### Full-Text Extraction via full_text_xml_url

**Problem:** The FR API article abstracts are often generic (especially for FTC consent orders, which all say "consent agreement settles alleged violations of Federal law"). The FR HTML pages (`federalregister.gov/documents/...`) are also CAPTCHA-blocked from automated access.

**Solution:** The API returns a `full_text_xml_url` field on individual article responses (e.g. `https://www.federalregister.gov/documents/full_text/xml/2026/07/07/2026-13628.xml`). This XML URL bypasses the HTML page CAPTCHA and returns the complete document text including the full SUPPLEMENTARY INFORMATION section.

**When to use:**
- API abstract is too generic (common for consent orders)
- You need the full regulatory text, policy details, or specific statutory references
- You're tracking an AI policy lifecycle and need the full document context

**Usage pattern:**
```bash
curl -sL --max-time 20 "https://www.federalregister.gov/documents/full_text/xml/2026/07/07/2026-13628.xml" | python3 -c "
import sys, re
content = sys.stdin.read()
text = re.sub(r'<[^>]+>', '\n', content)
text = re.sub(r'\n\s*\n', '\n', text)
lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 20]
for l in lines[:80]:
    print(l[:200])
"
```

**How to get the URL:** Fetch the individual article endpoint, extract `full_text_xml_url`:

```bash
curl -sL --max-time 20 "https://www.federalregister.gov/api/v1/articles/2026-13628" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('XML URL:', d.get('full_text_xml_url', 'NOT FOUND'))
print('HTML URL:', d.get('html_url', 'NOT FOUND'))
print('Abstract:', (d.get('abstract') or '')[:300])
"
```

**Field reference:** The individual article API response includes these detail fields beyond the search results:
- `full_text_xml_url` — XML full text (bypasses FR HTML CAPTCHA)
- `html_url` — FR HTML page (often CAPTCHA-blocked)
- `action` — Rule type label (e.g. "Proposed policy statement; request for comments.")
- `comment_url` — Link to regulations.gov docket
- `dates` — Human-readable dates section
- `citation` — FR volume/page citation

### FTC Press Releases (CDP browser target)

The FTC press releases page loads reliably via CDP browser (no CAPTCHA, no Cloudflare):

URL: `https://www.ftc.gov/news-events/news/press-releases?field_press_release_date_value=2026`

Access via:
1. `mcp_chrome_devtools_mcp_new_page(url="...")`
2. `mcp_chrome_devtools_mcp_take_snapshot()` reads titles, dates, and preview text

Key enforcement types to watch for legal sweep:
- **AI enforcement** — Cox Media Group "Active Listening" settlement (May 2026, $930K): deceptive AI marketing claims
- **Data security** — Illuminate Education order (June 2026): student data security failure
- **Noncompete** — Rollins Inc. (June 2026): noncompete ban enforcement
- **Consumer privacy** — TAKE IT DOWN Act warning letters (May 2026)

## CDP Browser Workflow for Source Checking

1. Open page: `mcp_chrome_devtools_mcp_new_page(url="https://...")`
2. Read content: `mcp_chrome_devtools_mcp_take_snapshot()`
3. For interactive sites (filters, dropdowns):
   - Use `mcp_chrome_devtools_mcp_take_snapshot()` to find element UIDs
   - Use `mcp_chrome_devtools_mcp_fill(uid=..., value=...)` for dropdowns
   - Use `mcp_chrome_devtools_mcp_click(uid=...)` for buttons/links
4. Keep pages open for the session — the CDP browser persists across calls

## curl Fallback (when browser is unavailable)

```bash
# Always set a real browser User-Agent
curl -sL --max-time 15 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# IRS curl — returns enough HTML to grep for news items
curl -sL --max-time 15 -A "Mozilla/5.0" "https://www.irs.gov/newsroom" | grep -i "IR-2026"

# FL Senate bills — works with curl
curl -sL --max-time 15 -A "Mozilla/5.0" "https://www.flsenate.gov/Session/Bills/2026"

# DuckDuckGo lite — simplest search fallback
curl -sL --max-time 15 "https://lite.duckduckgo.com/lite/?q=site:irs.gov+real+estate"
```

## Tools That May Be Unavailable

- `web_extract` — not present in all agent configurations
- `web_search` — not present in all agent configurations
- `browser_navigate` — may fail with "CDP WebSocket connect refused"; use `mcp_chrome_devtools_mcp_new_page` instead
- `browser_snapshot` — same CDP dependency; use CDP MCP tools instead
