# JS-Heavy Site Data Extraction — Web OSINT When Search Engines Are Blocked

> **Context:** Many commercial search engines (Google, Bing, Yahoo) and directories (Yellow Pages, Yelp, TripAdvisor) serve CAPTCHAs to automated requests. This reference documents workarounds using alternate data sources and direct site-source parsing.

## Principle: Skip the Search Engine, Go Direct

When `web_search` or `curl → Google/Bing/Yahoo` returns CAPTCHAs, pivot to **direct data sources** that serve machine-readable content.

## Technique 1: Job Board Scraping for Business Intel

Job boards (Indeed, ZipRecruiter) list businesses actively hiring, often with pay rates, schedules, and descriptions — useful intelligence even when you're not job hunting.

### Indeed Scraping Pattern

```bash
# 1. Search with targeted query + location + radius
curl -sL "https://www.indeed.com/jobs?q=server+restaurant&l=your city%2C+NY&radius=25&sort=date" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

# 2. Extract structured data with Python regex
```

**Python extraction pattern:**

```python
import sys, re
html = sys.stdin.read()

# Job titles
titles = re.findall(r'jobTitle[^>]*>.*?<span[^>]*title="([^"]+)"', html)

# Company names
comps = re.findall(r'data-testid="company-name"[^>]*>([^<]+)<', html)

# Locations
locs = re.findall(r'data-testid="text-location"[^>]*>([^<]+)<', html)

# Pay rates — note: salaries map per job card, not per title
# Each job card (CSS class containing salary-snippet) has one salary
pays = re.findall(r'salary-snippet[^>]*>([^<]+)<', html)

# Job snippets (full/part time, shift info)
snippets = re.findall(r'belowJobSnippet[^>]*>(.*?)</div>', html, re.DOTALL)
```

**Key observations:**
- Indeed renders HTML server-side with JS for interaction only — all job data is in the initial HTML
- Job titles render as `<span title="Actual Title">` inside anchor tags
- Salary data is in `<li class="salary-snippet-container">` elements
- User-Agent matters — set a modern desktop browser UA
- Sort by date with `&sort=date` to get freshest results

### Pay Rate Matching

Indeed's HTML has a ratio of ~2 title/company elements per 1 salary element (mobile + desktop card versions). Match by index:

```python
sal_idx = 0
for i in range(min(len(titles), n)):
    pay = pays[sal_idx] if sal_idx < len(pays) else 'Check posting'
    print(f'{titles[i]} — {comps[i]} | {pay}')
    if i % 2 == 0:  # Every other title-card has a salary
        sal_idx += 1
```

## Technique 2: OSM Nominatim — Block-Resistant Geocoding

OpenStreetMap's Nominatim API rarely blocks automated requests (with a polite User-Agent and rate limiting).

```bash
# Address lookup by business name + location
curl -sL "https://nominatim.openstreetmap.org/search?q=Kraverie+Saratoga+Springs&format=json&limit=1" \
  -H "User-Agent: YourAgent/1.0"

# Returns: full address, lat/lon, OSM type, display name, bounding box
```

**Get OSM tags for a node** (phone, website, hours, cuisine):

```bash
curl -sL "https://api.openstreetmap.org/api/0.6/node/{OSM_ID}" \
  -H "User-Agent: YourAgent/1.0"
# Returns XML with <tag k="phone" v="..."/> etc.
```

**Limitations:** OSM data quality varies by location. Restaurants in tourist areas (like Saratoga Springs) tend to have complete data; rural areas may be sparse.

## Technique 3: Wix Site Source Parsing

Wix sites are single-page apps with all content loaded via JS. Most data is in the initial HTML payload inside `<script>` tags. Phone numbers and addresses are often embedded in the rendered HTML template even though the interactive elements load later.

### Phone Extraction

```bash
curl -sL "https://target-site.com/" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Extract phone with regex on raw HTML
# Wix often embeds phone as: (518) 450-7423
# in rich-text spans
```

**Pattern to try:**
```python
phones = re.findall(r'\(?\d{3}\)?[.-]?\s*\d{3}[.-]?\s*\d{4}', html)
```

**Key insight:** Even though the page is JS-rendered, Wix stores text content (phone, address, hours) in the static HTML as `<span>` elements inside `wixui-rich-text__text` classes. Search the **raw HTML source**, not a rendered DOM.

### Meta Description Extraction

Wix pages load `<meta>` tags server-side:

```python
desc = re.findall(r'<meta name="description" content="([^"]+)"', html)
og_title = re.findall(r'<meta property="og:title" content="([^"]+)"', html)
```

## Technique 4: Facebook Embed Data for Business Profiles

Facebook's Page plugin (used for embedded timelines) sends a JSON payload with the page's full business profile — including phone, category, description, follower count, and price range.

### How to Find the Facebook Page ID

Look for the page URL pattern: `facebook.com/people/...` or check any reference to `pageID` in embed code. The Facebook Graph API call for the Page plugin is:

```bash
# Not directly callable without access token, but the embed page source
# contains the business data in the React component payload
```

### Extract from Embed HTML

When you request `https://www.facebook.com/plugins/page.php?href=...`:

1. The response HTML contains a `<script>` block with the PagePluginV2.react component props
2. Search for `pagePhone`, `pageDescription`, `pageCategory`, `pagePriceRange`, `followerCountFormatted`, `pageName`
3. These are in a `{"define":[[...]]}` JSON structure inside a `new ServerJS()` call

**Extraction pattern:**
```python
# Phone
phone = re.findall(r'"pagePhone":"([^"]+)"', html)

# Description
desc = re.findall(r'"pageDescription":"([^"]+)"', html)

# Category
cat = re.findall(r'"pageCategory":"([^"]+)"', html)

# Price range
price = re.findall(r'"pagePriceRange":"([^"]+)"', html)

# Follower count
followers = re.findall(r'"followerCountFormatted":"([^"]+)"', html)
```

**Why this works:** Facebook's embed plugin is designed for third-party websites and is publicly accessible. The page data is injected into the initial JS payload, not loaded asynchronously.

## Technique 5: Wayback Machine — Archived Contact Pages

When a live site is blocked or JS-rendered, check the Wayback Machine:

```bash
# Check if any snapshot exists
curl -sL "https://web.archive.org/web/20250000000000if_/https://target-site.com/contact"
```

**Limitations:**
- Many JS-heavy sites (Wix, Squarespace) aren't captured well
- POST forms (like state SOS search) can't be replayed
- Returns CAPTCHA on Google-cached pages for the same IP

## Multi-Source Consolidation Pattern

Combine findings from multiple sources into a complete business profile:

```python
profile = {
    "business_name": "...",
    "address": "From OSM, Wix meta, or Facebook",
    "phone": "From Wix source or Facebook embed",
    "hours": "From Wix source text",
    "description": "From meta tags or Facebook",
    "category": "From Facebook page category",
    "price_range": "From Facebook embed",
    "follower_count": "From Facebook embed",
    "hiring": {
        "positions": "From Indeed",
        "pay": "From Indeed posting",
        "schedule": "From Indeed posting",
        "requirements": "From Indeed snippet"
    }
}
```

Each source independently confirms or augments the others.

## Pitfalls

1. **Indeed salary matching**: The 2-to-1 ratio of titles to salaries shifts unpredictably. Always test the parse on a fresh page load.
2. **Wix phone false positives**: Raw HTML may contain phone-like numbers from tracking pixels, CDN URLs, or API tokens. Validate by checking context (presence of "PHONE" header text nearby).
3. **Facebook embed rate limits**: The plugin page may be rate-limited on rapid repeat requests. Add 1-2 second delays between calls.
4. **OSM data staleness**: Business hours, phone numbers, and websites on OSM can be years out of date. Cross-validate with other sources.
5. **No single source is complete**: Indeed has pay/job data but no phone. Facebook has phone/category but no pay. OSM has address but often no phone. You need ALL three.
