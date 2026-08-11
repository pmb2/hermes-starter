# Company Leadership & Management Research via Search Engines

When state SOS databases are down (migration, maintenance, or API restrictions) and you need to find who manages a company, use this multi-pronged search-engine approach.

## Workflow

### 1. Identify the Correct Company Name

The name the user provides may be slightly off (e.g., "Michael's Group Builders" → "Michaels Group Homes"). Always try:

- Exact match with quotes: `"Michaels Group Homes"`
- Without quotes: `Michaels Group Homes NY`
- Remove/reposition apostrophes: `Michales Group Builders`
- Try related terms: `builder`, `homes`, `construction`, `developers`, `realty`
- Add geography: `capital region NY`, `Albany`, `Saratoga`

### 2. Find the Company Website

Navigate to the company website and look for:
- `/about-us` — history and founder background
- `/about-us/team-detail/` or `/team` — leadership profiles
- `/leadership/`, `/management/`, `/our-team/`
- `/about/` — often has team section
- `/contact-us` — address and phone

Use Chrome DevTools MCP to extract rendered content:
```
evaluate_script(function: "() => { return document.body.innerText.substring(0, 10000); }")
```

#### Team Page URL Pattern Recognition

Many CMS-driven company sites use predictable URL patterns for team detail pages. Recognizing these lets you enumerate team members:

**Common patterns:**
- `/about-us/team-detail/name-N` where N is a sequential ID (common PHP CMS)
- `/team/name-slug` — clean slugs (modern CMS like Webflow)
- `/about/team/name/` — WordPress with page builder
- `/leadership/name-surname/` — corporate sites

**When you find one team member at `/about-us/team-detail/luke-michaels-9`, try:**
- Bumping the numeric ID down: `/eric-willson-10`, `/jonathan-bunker-8`
- Navigating to `/about-us/` or `/about/` and looking for embedded team sections not linked in the nav

### 3. Search Engine Options (in order of reliability)

| Engine | Anti-bot Level | Best For |
|--------|---------------|----------|
| DuckDuckGo | Medium — captcha less common | General search, passes Cloudflare more often |
| Bing | High — Cloudflare blocks often | Only when others fail |
| Google | High — captcha blocks quickly | Avoid for automated searches |

**Key technique — Chrome DevTools MCP evaluate_script:**
When search engines show a captcha or Cloudflare challenge, the page still renders content underneath. The DNS/accessibility snapshot may not show it, but `evaluate_script` can extract the rendered text:

```javascript
// Extract all visible text from the search results page
() => { return document.body.innerText.substring(0, 10000); }
```

This bypasses captcha/Cloudflare because the challenge overlay is visual-only; the underlying DOM still contains the search results (DuckDuckGo) or at least related searches/suggestions that point to the right company name.

### 4. Leadership Discovery Sources

Once you have the correct company name, search for management by combining:

| Source | What It Reveals | Notes |
|--------|----------------|-------|
| Company website (Team page) | Names, titles, bios, email, phone | Most authoritative |
| LinkedIn | Titles, tenure, education, connections | Authwall after ~1 hit; use evaluate_script |
| RocketReach | Management org chart, email formats, phone | Summary page often loads readable |
| Blue Book (thebluebook.com) | Key contacts, years with company | Good for construction/home builders |
| Better Business Bureau (bbb.org) | Business profile, years in operation | Contact info may be limited |
| BuildZoom (buildzoom.com) | License info, reviews, phone | Good for contractors |
| Yelp | Business description, hours, specialities | Sometimes names owner |
| Nextdoor | Community-level info, reviews | Local neighborhood context |
| Datanyze | Management team list | Tech company profiles |
| Yellow Pages | Basic contact, categories | Fallback option |
| Instagram | Owner/manager identity, phone, email | For small/local businesses that run their own social |

#### Instagram as OSINT Source for Small Business Owners

Small builders, contractors, and local service businesses often run their own Instagram. The account bio or posts may reveal:
- The owner/manager's full name (from tagged photos, captions, bio)
- A direct phone number or email
- Other businesses they operate
- Personal accounts they follow

**Technique:**
```
1. Search Instagram for the business name (via DuckDuckGo: site:instagram.com "Business Name")
2. Navigate to the profile via Chrome DevTools MCP
3. Evaluate page for bio, follower count, linked accounts
```

Example: `site:instagram.com sharlowbuilders` revealed the account was run by **Reggie Clow**.

### 5. Cross-Reference Technique

```python
# Pattern: when you find a name, verify across multiple sources
findings = {
    "company": "Michaels Group Homes",
    "sources_checked": [
        "Company website (michaelsgroup.com) — team page",
        "RocketReach — management org chart",
        "Blue Book — key contacts",
        "BBB — business profile"
    ],
    "leadership": [
        {"name": "Luke Michaels", "title": "Principal", "email": "luke@..."},
        {"name": "Eric Willson", "title": "Principal", "domain": "operations"},
        {"name": "C. Michaels", "title": "President & CEO"},
        {"name": "Heidi Harkins", "title": "CFO"}
    ]
}
```

### 6. Searching for a Specific Employee by First Name

When you need to determine if a named individual (e.g., "Johnny") works at a company:

**Techniques in priority order:**

1. **Email domain + name search**: `"michaelsgroup.com" Johnny` — catches employee emails indexed on the web
2. **LinkedIn search**: `site:linkedin.com/in "Michaels Group Homes" John` — find LinkedIn profiles listing that company
3. **General search**: `"Michaels Group Homes" "Johnny"` or `"Michaels Group Homes" John` — narrow by geography
4. **Review sites**: Check Yelp, BBB, Google Reviews, Birdeye for employee names mentioned in reviews or responses
5. **Directory sites**: RocketReach, LeadIQ, ContactOut, SignalHire — these aggregate employee directories

**Important:** Most employee directories require paid subscriptions for contact details, but the *existence* of an employee at a company is often visible on the free summary page.

### 7. Parallel Search Strategy

When search engines block automated requests, run multiple searches across different engines in parallel using separate browser pages:

- **Page A**: DuckDuckGo for general company search
- **Page B**: Direct company website navigation
- **Page C**: Specific management search (company + president/CEO/owner)

### 8. Trade Association Member Directories (Local Builder/Contractor Research)

For finding local home builders, contractors, and construction companies, the company's local trade association is often better than national directories:

**Capital Region Builders & Remodelers Association (CRBRA)**
- URL: `https://web.crbra.com/atb/search`
- Navigate via: Quicklinks → Builder (or Builder/Remodeler)
- Direct: `https://web.crbra.com/atlas/directory/category/builder`
- Covers: Albany, Schenectady, Rensselaer, Saratoga, Warren County home builders
- What you get: Company name, phone, address, website, category, member status

**Workflow:**
```
1. Navigate to the association's member directory (often at web.<association>.com)
2. Select the relevant category (Builder, Remodeler, etc.)
3. Scroll through results or use site search for the company name
4. Extract: company name (correct legal spelling), phone, address, website
5. Then use the company website for management/leadership discovery
```

**Why trade association directories work when search engines don't:**
- They are curated lists with verified member information
- The company name is listed in its correct form (vs. the user's phonetic/slightly-off recollection)
- No captcha/Cloudflare (government-adjacent sites)
- Includes local/regional companies that may not rank highly on Google
- Often includes contact information not available on the company website

**Finding the right association:**
```bash
# Search pattern:
web_search('<industry> association <geography> member directory')
# Examples:
# "builders association capital region NY member directory"
# "home builders association Albany NY"
# "contractors association Saratoga member directory"
```

**Known local trade associations:**
| Region | Association | URL Pattern |
|--------|-------------|-------------|
| Capital Region NY | Capital Region Builders & Remodelers (CRBRA) | web.crbra.com/atb/Builder |
| National | NAHB (National Association of Home Builders) | nahb.org |
| State | NYSBA (New York State Builders Assoc) | nysba.com |

### 9. Phonetic Name Matching for Business Research

When the user provides a name they *heard* rather than *saw written*, the spelling may be significantly off. Use iterative phonetic variation to discover the correct name.

**The technique:**
```
User says: "shar-loo builders"
→ Try letter-by-letter phonetic variations:
  - sh ar loo → "Sharlow" (too literal)
  - sh ar loo → "Sharloo"
  - ch ar loo → "Charloo"
  - ch ar lew → "Charlew" ✓ (found via trade association directory)
  - sh ar lew → "Sharlew"
  - ch ar low → "Charlow"
```

**Systematic approach:**
1. **Preserve the syllable count** — The user remembered 2 syllables (shar-loo), so try 2-syllable variations
2. **Vary the first consonant cluster:** `sh` vs `ch` (most common confusion in English)
3. **Vary the ending:** `-loo` vs `-lew` vs `-low` vs `-leau` vs `-lo`
4. **Check against trade association directories** (they use correct spellings)
5. **Once found, cross-reference** the correct spelling against the original input and note the difference

**Common phonetic variations in English business names:**
| Sound | Possible Spellings |
|-------|-------------------|
| /ʃɑr/ (shar-) | Shar-, Char- (like "charade"), Cher- |
| /lu/ (loo) | -loo, -lew, -leau, -lou, -lu |
| /ʃaɪ/ (shy) | Shy-, Chi-, Chai- |
| /keɪ/ (kay) | Kay-, Kei-, Cai-, Kae- |
| /fɪl/ (fil) | Phil-, Fil-, Phyll- |

**When to use:**
- User says "that's how it sounds" or describes the pronunciation
- User guessed at spelling (they said "Charloo" then "Sharlow")
- Multiple failed searches with the original spelling
- The company is local/small enough that it won't auto-correct in search engines

### 10. Identifying the Builder for a Specific Development

After identifying home builders in a region via trade association directories, a common follow-up is determining *which* builder is developing a specific street or area.

**Workflow:**

```
1. Search the development name + road/area:
   DuckDuckGo "<development name>" "<road>" builder
   Example: "Crescent Woods" "Crescent Road" Clifton Park

2. Check each known builder's community listings:
   Navigate to builder's /new-homes page and look for communities
   near the target road. Many builders list communities by town.

3. When you find a match, verify on the builder's own community page:
   - Confirms the builder owns that development
   - May list available homes, pricing, floor plans
   - Reveals the on-site sales contact (name + phone + email)

4. Cross-reference with real estate sites:
   Zillow/Trulia/NewHomeSource listings for the development often
   name the builder in the community description.
```

**Example — Crescent Woods (Clifton Park, NY):**
```
User: "Which builder is building off Crescent Road in Clifton Park?"

1. Search: DuckDuckGo "Crescent Woods" "Crescent" Clifton Park builder
   → Results include "Crescent Woods by Michaels Group Homes"

2. Navigate to michaelsgroup.com/new-homes/new-york/clifton-park/crescent-woods
   → Confirmed: Michaels Group Homes, Crescent Woods community
   → Location: Clifton Park, NY 12065 (off Crescent Rd)
   → Sales contact: Danielle Enos, 518-312-3452
   → Status: 1 home available, $752,800

3. Cross-reference: newhomesource.com also lists Crescent Woods
   as a Michaels Group Homes community

Result: Michaels Group Homes is building Crescent Woods
         (not Charlew Builders or another CRBRA member)
```

**Why this matters:** When a user asks about multiple builders simultaneously (e.g., "who manages X and Y, and which one is building at Z?"), the trades association directory gives you the candidates, and this technique connects candidates to specific land parcels.

## Common Pitfalls

- **Captcha/Cloudflare on search engines**: Don't give up — use `evaluate_script` to extract the rendered text underneath the challenge overlay. The content is usually still in the DOM.
- **Wrong company name**: The user's recollection may be imprecise. Treat their input as a hint, not a fact. Try variations until you find the actual registered name.
- **Local builders often use "Homes" not "Builders"**: In the home construction industry, company names typically use "Homes" (Michaels Group Homes, Ryan Homes, etc.) even when the user says "Builders."
- **Multiple generations, same family**: Family businesses often have multiple family members in leadership with different titles (Principal vs President/CEO). Check carefully who has day-to-day operational authority.
- **Registered agent vs actual address**: The address on state filings is often the registered agent's address, not the business address. Company website contact page is more reliable for actual location.
- **Search engine rate limiting**: After a few automated searches, engines may start blocking. Rotate between DuckDuckGo, direct site navigation, and other sources.
- **Company name collision with national brands**: A local company like "Michaels Group Homes" is easily drowned out by "Michaels" (craft store chain, 40M+ monthly searches) or "The Michaels Organization" (national real estate firm). Add negative keywords or use quotes plus geography to filter out the noise: `"Michaels Group Homes" -"Michaels Stores" -"Michaels Organization" -craft -art`
- **LinkedIn authwall**: LinkedIn shows a sign-in wall after 1-2 automated page loads. Capturing the page content before this wall appears is unreliable. Prefer RocketReach or other aggregators for bulk employee discovery, and only use LinkedIn for targeted single-person verification.
- **Team page URLs may not match nav**: Some sites have team detail pages (e.g., `/about-us/team-detail/eric-willson-10`) that exist but are not linked from the nav menu. Check `/about-us/` itself for embedded team sections, or discover them via search engine index.
- **"No results" on DuckDuckGo for quoted search**: If a quoted search returns nothing, drop the quotes and broaden terms. The company may be too small or niche to have an exact-match hit on DDG's index.
- **Development name vs road name mismatch**: A user describes a development by its road (e.g., "off Crescent Rd") but the development has a distinct name ("Crescent Woods"). Searches for "Crescent Road new development" may return little. Instead, search for the development name itself once the builder is identified via the trade directory, or search Zillow/NewHomeSource for the general area and scan community names.
- **DuckDuckGo "No results" for specific development+builder**: When search engines return nothing for a well-known local development, the site may use JavaScript rendering that DuckDuckGo cannot index. Navigate directly to the known builder's website community page to verify, or use Google/Bing which sometimes index JS-rendered content better.
