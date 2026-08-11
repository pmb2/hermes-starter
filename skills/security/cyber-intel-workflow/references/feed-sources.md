# Cyber Intel Feed Sources

Reliability-tested sources for the nightly research and morning briefing pipeline. Last tested: Jun 20, 2026.

## Tier 1 — RSS Feeds (unreliable from cron)

These frequently time out or return errors when run as background cron jobs. Always retry once, then fall back.

### The Hacker News
```
curl -sL "https://feeds.feedburner.com/TheHackersNews" --max-time 15
```
Parse: XML RSS, extract `<item>` elements (title, link, pubDate, description).
Status: Frequently unreachable from cron (timeout). Good when it works.

### BleepingComputer
```
curl -sL "https://www.bleepingcomputer.com/feed/" --max-time 15
```
Parse: XML RSS, same structure as THN.
Status: Same reliability as THN.

## Tier 2 — Structured Data Feeds

### NVD Modified Feed (preferred)
```
curl -sL "https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-modified.json.gz" --max-time 30 | gunzip
```
Parse: JSON, key is `CVE_Items[]`. Each item has `cve.CVE_data_meta.ID`, `impact.baseMetricV3.cvssV3.baseScore`, `cve.description.description_data[0].value`.
Filter: Only items with CVSS >= 7.0 to reduce noise. 5K+ items in modified feed.
Status: Large download (~10MB compressed). Slower but comprehensive.

### NVD Recent Feed
```
curl -sL "https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-recent.json.gz" --max-time 30 | gunzip
```
Parse: Same format as modified. Smaller (last 30 days).
Status: Easier to process but less complete.

### CISA KEV
```
curl -sL "https://www.cisa.gov/known-exploited-vulnerabilities-catalog" --max-time 15
```
Parse: HTML. Look for `2026-06-2*` date patterns near CVE mentions.
Status: Frequently times out from cron. Page layout changes periodically.

### GitHub API (CVE search)
```
curl -sL "https://api.github.com/search/repositories?q=CVE-2026&sort=updated&order=desc&per_page=15" --max-time 15
```
Rate limit: 60 unauthenticated requests/hour. Use sparingly.
Output: JSON with `items[].full_name`, `description`, `updated_at`, `stargazers_count`.

## Tier 3 — Resilient Fallbacks (most reliable)

### PoC-in-GitHub (primary fallback)
```
curl -sL "https://raw.githubusercontent.com/nomi-sec/PoC-in-GitHub/master/README.md" --max-time 15
```
Format: Markdown. Each CVE has a heading `### CVE-2026-XXXXX` with description and bullet-point PoC links.
Parsing: `grep -A3 "CVE-2026-"` or Python regex to extract CVE IDs, descriptions, and PoC URLs.
Status: Very reliable. Almost never fails. No rate limit. Use this as the primary PoC source.
CVE count from raw.githubusercontent.com: ~1235 entries for CVE-2026 as of Jun 20, 2026.

### Packet Storm
```
curl -sL "https://packetstormsecurity.com/files/tags/exploit/page1" --max-time 15
```
Parse: HTML, extract `<a href="/files/..."` links.
Status: Moderately reliable. Carries exploit files and advisories.

## Feed Reliability Matrix

| Source | Cron Reliability | Coverage | Freshness | Notes |
|--------|-----------------|----------|-----------|-------|
| THN RSS | Low | High | High | Best when available |
| BleepingComputer RSS | Low | High | High | Same as THN |
| NVD Modified | Medium | Full | 24h lag | Large, slow |
| NVD Recent | Medium | 30 days | 24h lag | Snappier |
| CISA KEV | Low | KEV only | High | Format changes |
| GitHub API | Medium | CVE repos | Real-time | Rate limited |
| PoC-in-GitHub (raw) | High | CVEs with PoCs | Real-time | Best fallback |
| Packet Storm | Medium | Exploits | Real-time | HTML parsing needed |

## Recommended Sweep Order

1. PoC-in-GitHub (raw) — fast, reliable, zero rate limit
2. NVD Modified Feed — comprehensive CVE coverage
3. RSS feeds (THN + BC) — best editorial coverage when available
4. GitHub API — supplementary PoC freshness check
5. CISA KEV — only for KEV-specific deadlines

## Agent web_search Overnight Gap Pattern

For the morning briefing's 9-hour gap sweep (10PM→7AM), supplement feeds with targeted web_search calls using the current date:

```
web_search(query="new CVEs published [Mon DD] 2026 critical severity", limit=5)
web_search(query="cyber security breach ransomware news today [Mon DD] 2026", limit=5)
web_search(query="[specific CVE ID] update [Mon DD]", limit=5)
```

These catch items published in the overnight window that wouldn't appear in programmatic feeds. See SKILL.md Phase 2 Quick Freshness Sweep for the full pattern.

## Tier 4 — Browser Navigation Fallback (no web_search tool)

When `web_search` is not available in the toolset, use Playwright MCP to navigate directly to news sites. Tested targets (Jul 2026):

### BleepingComputer (most reliable)
```
browser_navigate(url="https://www.bleepingcomputer.com/")
browser_snapshot()
```
- Lists ~20 latest articles on page 1 with timestamps (HH:MM AM/PM) and bylines
- Article heading: `heading "...title..." [level=4] [ref=eN]` in snapshot
- Timestamp immediately adjacent: `time [ref=eN]: July DD, 2026`
- Description in adjacent `paragraph` element
- Freshness filter: articles from today or yesterday evening are new
- Pagination available via `link "2" [ref=eN]` for more coverage

### CISA Alerts & Advisories (authoritative for KEV)
```
browser_navigate(url="https://www.cisa.gov/news-events/cybersecurity-advisories")
browser_snapshot()
```
- Lists alerts by date, most recent first
- Each entry: `article [ref=eN]` containing `time [ref=eN]: Jul DD, 2026` and `heading "CISA Adds..." [level=3] [ref=eN]`
- KEV additions tagged with "Alert" badge in `generic [ref=eN]`
- Filters available but default view (by release date) is sufficient

### The Hacker News (tertiary)
```
browser_navigate(url="https://thehackernews.com/")
browser_snapshot()
```
- Article structure differs — uses `<heading>` elements with narrative paragraphs
- Less structured than BleepingComputer; harder to scan programmatically
- Use when BleepingComputer coverage is thin and you need alternative angles

### Threatpost (stale content warning)
```
browser_navigate(url="https://threatpost.com/")
browser_snapshot()
```
- Significant caveat: observed returning 2022-era articles as "latest" (tested Jul 2026)
- May not reflect current events. Use only as last resort.
- The "Featured News" section at the top appears freshest; "Latest News" below may be months old.

### Extraction Notes for Browser Snapshots

- Playwright snapshots return YAML accessibility trees; parse visually in the IA output
- Locate articles by scanning for `heading "..." [level=2|3|4]` elements
- Adjacent `time` elements show publication date — this is your freshness signal
- BleepingComputer snapshot also shows `paragraph` descriptions after each heading
- CISA uses `article [ref=eN]` wrappers with `time` and `heading` children
