# Corporate Family Tree Mapping — Multi-Entity Deep Dive

Mapping the full corporate family tree for a known company or brand name. Covers parent entities, subsidiaries, sister companies, and related but separate entities that share a common founder/family/root.

## When to Use This Pattern

Use when the target is a **group of related companies** rather than a single entity. Signs you have a family-tree problem:

- The user names a company and says "they also own/have/build X"
- A website footer shows multiple distinct logos/brands under one umbrella
- Different divisions operate under different legal names but same leadership
- Same family name appears across multiple entity filings
- The company has a hospitality arm, management arm, construction arm, etc.

## Workflow

### Phase 1: Initial Reconnaissance

Start with a broad search to establish the landscape:

```
Search query: "<company name> <city/state>"
```

**What to look for in search results:**
- The **Google AI Overview** (top box) — often summarizes company size, services, and location. Read this first for orientation.
- **Official website** — check for `/about-us/`, `/our-company/`, `/leadership/` pages
- **News articles** — recent projects reveal partnerships and current activity
- **LinkedIn** — company page shows employee count, HQ, industry
- **Better Business Bureau / Chamber of Commerce** listings — confirm legal name
- **Wikipedia** (if applicable) — history and ownership structure

### Phase 2: Website Navigation (Playwright MCP)

Use the Playwright MCP browser tools for site-by-site navigation:

```bash
# 1. Navigate to company website
mcp__playwright_mcp__browser_navigate(url="https://www.company.com/")

# 2. Take snapshot to see page content
mcp__playwright_mcp__browser_snapshot()

# 3. Identify /about-us, /services, /portfolio, /leadership links from snapshot
# Open each in a new tab for parallel exploration
mcp__playwright_mcp__browser_tabs(action="new", url="https://www.company.com/about-us/")
mcp__playwright_mcp__browser_tabs(action="new", url="https://www.company.com/portfolio/")
```

**Key pages to snapshot for corporate intel:**

| Page | What It Reveals |
|---|---|
| `/about-us/` or `/about/` | Founding story, founder names, company history, number of employees, annual revenue |
| `/leadership/` or `/our-team/` | Executive names, titles, bios |
| `/services/` | What the company actually does (often reveals subsidiaries by function) |
| `/portfolio/` or `/projects/` | Past clients, project scale, geographic reach |
| Footer area | Sister company logos, links to other brands under the same umbrella |
| `/bbl-hospitality/` or similar sub-site | Separate divisions with their own branding and leadership |

### Phase 3: Multi-Tab Parallel Research

Open multiple tabs simultaneously to gather data from different sources:

```javascript
// Example: 3-tab parallel research
mcp__playwright_mcp__browser_tabs(action="new", url="COMPANY_URL_1")
mcp__playwright_mcp__browser_tabs(action="new", url="COMPANY_URL_2")
mcp__playwright_mcp__browser_tabs(action="new", url="COMPANY_URL_3")
```

**Typical sources for corporate deep dive:**
1. **Company website** — primary source
2. **Subsidiary/sister company websites** — listed in the footer
3. **News article about a recent project** — reveals decision-makers, partners, funding
4. **LinkedIn** — best for org chart and employee count (may hit authwall)
5. **Search for CEO/president name** — reveals their background and tenure

### Phase 4: Family Tree Construction

As you gather data, build the family tree:

```yaml
# Template for corporate family tree
Umbrella Parent (if any):
  - Entity 1 (the primary target)
    - Type: Construction / Hospitality / Management
    - Founded: YYYY
    - HQ: City, State
    - Revenue: ~$X
    - Employees: ~N
    - President/CEO: Name
    
  - Entity 2 (sister company)
    - Type: ...
    - Founded: YYYY
    - Key difference from Entity 1: ...
    
  - Entity 3 (related but separate)
    - Relationship: Spun off / founded by same family
    - Key note: NOT the same company despite shared name
```

### Phase 5: Founder/Leadership Deep Profile

Once you have a founder's name from the "About" page:

```
# Search pattern for founder deep-dive
Search: "<founder name> <company name>"
Search: "<founder name> obituary" (if deceased — often reveals family)
Search: "<founder name> LinkedIn"
```

**What to extract for each key person:**
- Full name and title
- How they're connected to the founding family (son, partner, outside hire)
- Email/phone from press releases or news quotes
- Related business affiliations
- Education and professional background

### Phase 6: Disambiguation — Same Name, Different Entity

Crucially important: verify you're researching the right company.

**Red flags that indicate a DIFFERENT entity with the same name:**
- Different geographic footprint (e.g., one operates in NY, another in TX/FL)
- Different leadership team
- Different website domain (company.com vs companyco.com)
- Different founding date and history
- Different client base (local vs national)

**How to handle:**
```markdown
# Distinguish in your report
## Entity Name A (Location 1)
- Focus: ...
- Website: ...
- Leadership: ...

## Entity Name A (Location 2) — SEPARATE ENTITY
- Focus: ...
- Website: ...
- Note: Shares family root but operates independently under different management
```

## Worked Example: BBL Companies Research

### Search Query
```
"BBL builders Schenectady New York"
```

### Starting Snapshot (Google AI Overview)
- Company: BBL Construction Services
- Location: 302 Washington Avenue Ext., Albany, NY
- Phone: (518) 452-8200
- Key projects in Schenectady: 160,000 sq ft Glendale Home (your city), Wedgeway Corner Market
- Services: Healthcare, Commercial, Multifamily, Hospitality Renovation

### Tabs Opened in Parallel
1. `https://www.bblinc.com/about-us/` — "About BBL" page
2. `https://www.bblinc.com/bbl-hospitality/` — Hospitality division
3. `https://www.bblinc.com/bbl-management-group/` — Property management division
4. `https://downtownschenectady.org/...` — News article about BBL project
5. `https://bblbuildingco.com/about-us/history/` — Separate BBL entity

### Key Discoveries Through Browser Navigation

**About page snapshot revealed:**
- Founded: 1973 (as a masonry business by Don Led Duke)
- Revenue: $500M annual construction sales
- Employees: 400
- Founder: Don Led Duke (started as mason, partnered with Barry & Bette in 1982)

**Footer links revealed the umbrella family:**
- BBL Construction Services
- BBL Hospitality
- BBL Management Group
- BBL Medical Facilities
- (All under bblinc.com)

**BBL Building Company (bblbuildingco.com)** — identified as SEPARATE:
- Different leadership (Mark Lear, Ron Rollins vs Jonathan deForest)
- Different focus (multifamily in TX/FL vs design-build in NY)
- Different history (spun off from Bette & Cring, not the original BBL)
- Same family root (Bette family) but operates independently
- HQ in Plano, TX — not Albany

**BBL Building Co history page revealed the Bette Companies family tree:**
- Joe Bette (1935) → Mike Bette (1960) → Barry & Bette (1973) → BBL (1982)
- Kevin Bette → First Columbia (real estate development)
- Matt Bette → BBL Florida (1988) → Bette & Cring (1999)
- All united under **The Bette Companies** umbrella

**News article (Downtown Schenectady, Jan 2026) revealed:**
- Current president: **Jonathan deForest** (named in article quote)
- Recent $3M project: Wedgeway Building grocery store
- Active in 2026 — confirmed company is still operating

### Report Structure Used

```
# COMPANY NAME — COMPREHENSIVE OSINT DOSSIER

## 1. OVERVIEW & IDENTITY
## 2. THE ENTITIES (What They Own) — list each subsidiary with details
## 3. FOUNDERS & FAMILY TREE — generational timeline
## 4. THE UMBRELLA EMPIRE — holding structure
## 5. LOCAL CONNECTIONS — specific projects in requested location
## 6. KEY DECISION-MAKERS — table of names, titles, contact
## 7. REVENUE & SIZE
## 8. SOCIAL MEDIA PRESENCE
## 9. AWARDS & RECOGNITION
```

## Pitfalls

### Assuming Same Name = Same Company
- **PITFALL**: BBL Construction Services (Albany) and BBL Building Company (Plano, TX) share the "BBL" name but are different entities with different leadership.
- **SOLUTION**: Before reporting, confirm: same HQ city? same leadership names? same website domain?
- **WORKAROUND**: Check the About/History pages of each — different founding stories confirm they're separate.

### Trusting a Single Source
- **PITFALL**: LinkedIn says 9,200 followers; About page says $500M revenue. Neither may be current.
- **SOLUTION**: Cross-reference company's own About page with news articles, LinkedIn, and Chamber listings.

### Missing the Umbrella Structure
- **PITFALL**: Reporting on one subsidiary without identifying the parent umbrella.
- **SOLUTION**: Scroll to the website footer — sibling company logos are almost always listed there.

### Over-relying on AI Overview
- **PITFALL**: Google's AI Overview summarizes but can conflate separate entities.
- **SOLUTION**: Only use AI Overview for initial orientation. Confirm every claim by navigating to primary sources.

### Tab Management Overload
- **PITFALL**: Opening too many tabs without tracking which is which.
- **SOLUTION**: Use `browser_tabs(list)` to check open tabs, and note the index of each meaningful page.

### CEO vs President Misidentification
- **PITFALL**: News articles often quote the President in project announcements, making it seem like they're the top decision-maker. The CEO may be a different person who doesn't appear in press.
- **SOLUTION**: Always check the company's own Leadership/Team page for the actual org chart. The person quoted in news may be the public-facing President while the CEO runs the overall strategy.
- **WORKAROUND**: Navigate to `website.com/about-us/leadership-team/` or similar to see the full hierarchy. The CEO typically appears first or has "CEO/Principal" in their title.

## Extracting Photos for Visual Identification

Corporate OSINT often includes identifying what key people look like — essential for meeting them in person (networking, events, hotels, etc.).

### Technique: JavaScript Eval for Image URL Extraction

Most corporate leadership pages use `<img>` tags for headshots. Extract all photo URLs by evaluating JavaScript in the page:

```javascript
// In the Playwright MCP browser, on any leadership/profile page:
mcp__playwright_mcp__browser_evaluate(
  function: "() => { 
    const imgs = document.querySelectorAll('img');
    const results = [];
    imgs.forEach(img => {
      // Exclude logos, awards, icons
      if(img.src && !img.src.includes('logo') && 
         !img.src.includes('award') && 
         !img.src.includes('seal') &&
         !img.src.includes('icon'))
        results.push(img.src);
    });
    return results.join('\\n');
  }"
)
```

**What this reveals:**
- Direct URLs to headshot photos (often `.jpg` or `.png` in a `/uploads/` directory)
- Photos are typically named `firstname-lastname.jpg` or initials-based
- BBL pattern: `https://www.bblinc.com/wp-content/uploads/2025/01/firstname-lastname.jpg`

### Technique: Google Image Search for Unlisted Executives

For key people who don't have a photo on the company website (e.g., founders with separate real estate companies):

```bash
# Use Google Images search via Playwright
mcp__playwright_mcp__browser_navigate(
  url: "https://images.google.com/search?q=First+Last+Company&udm=2"
)
```

**Sources of executive photos:**
- Company leadership/team pages (most reliable)
- LinkedIn company page posts (event photos often show multiple execs)
- News articles (pulled quotes often come with press photos)
- Chamber of Commerce event galleries
- Industry award announcements

### Building a Visual Recognition Sheet

After collecting photo URLs, compile them into a quick-reference format:

```markdown
## VISUAL RECOGNITION SHEET

### Person Name — Title
- **Photo**: https://company.com/path/to/photo.jpg
- **Distinctive features**: (age, hair, glasses, build)
- **Where to spot them**: (HQ, job sites, events, clubs)
- **How to address**: (if they walk in, this is what you say)
```

## Extracting Private Company Revenue Estimates

Most companies you'll investigate are private — no SEC filings, no public financials. Revenue estimates vary wildly across data sources.

### Technique: Triangulation Across Multiple Sources

Private company revenue data on aggregators is often outdated, estimated algorithmically, or based on employee count * industry average. Never trust a single source.

**Data sources with typical reliability:**

| Source | Reliability | Notes |
|--------|-------------|-------|
| **AI Overview (Google)** | Medium-High | When it says "between $X and $Y," those ranges often come from multiple indexed biz databases |
| **BizJournals Company Profile** | Medium-High | Often subscriber-only, but the AI Overview may surface the key number. Usually the most reliable for regional firms |
| **RocketReach** | Low-Medium | Algorithmic estimates. Good for a floor but often low |
| **ZoomInfo** | Medium | Better for employee count and org chart than revenue |
| **Growjo** | Low | Often dramatically low — uses opaque estimation models |
| **LinkedIn** | Low | Only shows employee count range, not revenue |
| **Company website** | Varies | May state revenue proudly ($500M!) or stay vague ("over $X") |
| **News articles** | Medium | May cite "sources familiar" or analyst estimates for larger firms |

**Methodology:**

```markdown
1. Gather all available estimates (usually 3-5 different numbers)
2. Discard obvious outliers (Growjo's $7M vs BizJournals' $400M = one is wrong)
3. Note the spread and explain why it exists:
   - Diversified companies (real estate + logistics + oil) have wider ranges
   - Pure-play companies (construction only) have tighter ranges
   - Revenue ≠ profit — construction margins are 3-8%, real estate margins are higher
4. State the range with confidence qualifier:
   - "Estimates range from $X to $Y, with BizJournals being the most reliable source"
5. If the user asks "are they rich/billionaires?" — do the math:
   - $500M revenue × 5% margin = $25M profit
   - Split across multiple owners = $5-15M per person annually
   - Over 20-40 year career = $10-50M net worth per person (not billionaires)
```

**Example output:**
```
BBL Construction Services:
- Revenue: ~$500M/yr (company stated, most reliable)
- Construction margins: 3-8% typical
- Estimated profit: $15-40M/yr
- Split among multiple principals/owners
- Individual net worth: $10-50M per person (very rich, not billionaire)

Galesi Group:
- Revenue: $80-400M range (depends on data source, oil prices swing it)
- Diversified across real estate + logistics + oil & gas (11,500 barrels/day)
- Oil alone at $70/barrel = ~$800K/day gross
- Net worth: $250M+ company level, founder likely $200M+ individually
```

### Technique: Wealth Benchmarking (The "Reality Check")

When a user asks "are they billionaires?" or "how big is this really?" — provide context by comparing to known benchmarks:

```
# The Hierarchy

| Company | Revenue | Type |
|---------|---------|------|
| DR Horton (national homebuilder) | $36 Billion | Public, national |
| Your Target Company | $X | Private, regional |
| Local Competitor | $Y | Private, local |

# The Reality Check
- Construction is high-revenue, low-margin (3-8%)
- Wealth is spread across multiple family members and generations
- They're "old money" in their region, not global elite
- Upper-crust local wealthy: nice homes, private clubs, good schools
- But not: private jets, superyachts, billion-dollar deals
```

## Building a Visual Recognition Sheet

When the user needs to recognize key people in person (e.g., at their workplace, networking events, or because these people own/run the hotel/building they work at), compile a recognition sheet.

### Photo Extraction from Leadership Pages

Most corporate leadership pages use `<img>` tags for headshots. Extract all photo URLs by evaluating JavaScript in the page:

```javascript
// In the Playwright MCP browser, on any leadership/profile page:
mcp__playwright_mcp__browser_evaluate(
  function: "() => { 
    const imgs = document.querySelectorAll('img');
    const results = [];
    imgs.forEach(img => {
      if(img.src && !img.src.includes('logo') && 
         !img.src.includes('award') && 
         !img.src.includes('seal') &&
         !img.src.includes('icon'))
        results.push(img.src);
    });
    return results.join('\\n');
  }"
)
```

**What this reveals:**
- Direct URLs to headshot photos (often `.jpg` or `.png` in a `/uploads/` directory)
- Photos are typically named `firstname-lastname.jpg` or initials-based
- BBL pattern: `https://www.bblinc.com/wp-content/uploads/2025/01/firstname-lastname.jpg`
- Galesi Group pattern: `https://www.galesi.com/wp-content/uploads/2024/10/GG-Leadership-0824_INITIALS-N.png`

### Google Image Search for Unlisted Executives

For key people who don't have a photo on the company website:

```bash
# Use Google Images search via Playwright
mcp__playwright_mcp__browser_navigate(
  url: "https://images.google.com/search?q=First+Last+Company&udm=2"
)
```

### Visual Recognition Sheet Format

```markdown
## VISUAL RECOGNITION SHEET

### Person Name — Title
- **Photo**: https://company.com/path/to/photo.jpg
- **Distinctive features**: (age range, hair color, glasses, build, typical attire)
- **Where to spot them**: (HQ, job sites, specific properties they visit, events, private clubs)
- **Connection to you**: (why they matter — they're your boss's boss, they built your hotel, etc.)
- **Conversation starter**: (what to say if you meet them — reference a project, compliment the company, etc.)
- **Likely schedule**: (daytime vs evenings, weekdays vs weekends, quarterly reviews at your location)
```

**Example entries:**

```
### Kevin Gleason — CEO/Principal, BBL Construction Services
- **Photo**: https://www.bblinc.com/wp-content/uploads/2025/01/kevin-gleason.jpg
- **Features**: Older guy, 60s, gray hair, suits at formal events
- **Where**: Corporate HQ (302 Washington Ave Ext, Albany), black-tie charity events
- **Connection**: Top of the whole $500M company. Not likely at your hotel.
- **Conversation**: "Been with BBL since '81 — that's 40+ years. You've built something incredible here."

### Stephen Obermayer — CFO/Principal + BBL Hospitality President
- **Photo**: https://www.bblinc.com/wp-content/uploads/2025/01/steve-obermayer.jpg
- **Features**: Middle-aged, professional, glasses
- **Where**: HQ + property visits. MOST LIKELY to visit YOUR hotel for management reviews.
- **Connection**: He's the one who signs off on everything at your property. Numbers guy.
- **Conversation**: Mention you're building your own business on the side (he's CFO — respects hustle).

### Francesco Galesi — Chairman, Galesi Group
- **Photo**: https://www.galesi.com/wp-content/uploads/2024/10/GG-Leadership-0824_FG-2.png
- **Features**: Elderly Italian gentleman, 80s, distinguished
- **Where**: Rare appearances at Mohawk Harbor (his office is at 220 Harborside Dr). If you see an older Italian guy with younger suits around him, that's him.
- **Connection**: Founder. His company owns the land your hotel sits on.
- **Conversation**: "Mr. Galesi, I work at the Hyatt House. Thank you for what you've built here at the Harbor."
```

## Extracting Social & Habitat Intel from News Articles

News articles about a company's projects often reveal more than just the project details — they contain clues about where key people spend their time socially.

**What to scan for:**

| Signal | Where It Appears | What It Reveals |
|--------|-----------------|-----------------|
| Charity events quoted | "Held at X Club" | Private club membership |
| Event co-sponsors | "In partnership with Y" | Business/social networks |
| Quote from leader | "John said at Z event" | Speaking/public appearance venues |
| Project location | "Built at 123 Main St" | Geographic area they frequent |
| Award ceremonies | "BBL won at Gala" | Industry events they attend |
| Partner organizations | "Working with N" | Professional affiliations |

**Extraction technique:**

After reading a news article snapshot, scan for:
1. **Venue names** — private clubs (Guan Ho Ha Fish and Game Club, Country Clubs, etc.) indicate where they network
2. **Partner names** — co-developers, financiers, architects (identify their business circle)
3. **Government bodies** — which county/city officials they work with (local political connections)
4. **Date patterns** — recurring events (annual golf outings, galas = reliable spotting opportunities)
