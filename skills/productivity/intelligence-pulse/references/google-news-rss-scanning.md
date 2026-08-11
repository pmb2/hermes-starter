# Google News RSS Scanning

**Purpose:** Aggregate local/regional news across multiple categories using Google News RSS feeds when `web_extract` or browser tools aren't available, or when you need a lightweight alternative for cron-based monitoring.

## Technique

Google News exposes an RSS feed at `https://news.google.com/rss/search` with query parameters:

```bash
curl -sL "https://news.google.com/rss/search?q=SEARCH_QUERY&hl=en-US&gl=US&ceid=US:en"
```

### Key Parameters
| Param | Description |
|-------|-------------|
| `q` | URL-encoded search query. Supports `OR`, `AND` (default), quoted phrases |
| `hl` | Language (en-US) |
| `gl` | Geolocation (US) |
| `ceid` | Country edition (US:en) |
| `after=YYYYMMDD` | **Crucial for filtering** — limits results to stories published after this date |

### Parsing (Python stdlib, no dependencies)

```python
import sys, xml.etree.ElementTree as ET
tree = ET.parse(sys.stdin)
root = tree.getroot()
for item in root.findall('.//item'):
    title = item.find('title').text or ''
    pubdate = item.find('pubDate').text or ''
    source = item.find('source')
    src = source.text if source is not None else ''
    link = item.find('link').text or ''
    print(f'  {pubdate} | {title[:80]} | {src}')
```

Or pipe directly from curl:

```bash
curl -sL "https://news.google.com/rss/search?...head -c 3000
# ...or parse fully:
curl -sL "$URL" | python3 -c "
import sys, xml.etree.ElementTree as ET
tree = ET.parse(sys.stdin)
for item in tree.findall('.//item'):
    print(item.find('pubDate').text, '|', item.find('title').text, '|', item.find('source').text if item.find('source') is not None else '')
"
```

## Date-Filtering Pattern

Without `after=`, Google News RSS returns up to ~100 results sorted by relevance (not recency). Older stories can dominate when the query isn't time-sensitive. The `after=` parameter is essential:

```bash
# Only stories AFTER June 1, 2026
curl -sL "https://news.google.com/rss/search?q=Schenectady+business&hl=en-US&gl=US&ceid=US:en&after=20260601" | python3 -c "..."
```

**Pitfall:** `after=` is not always respected. Some queries still return pre-date results. Always check `pubDate` in your parser and filter client-side for strict recency.

## Multi-Category Scanning Pattern

When scanning N categories (e.g., Local Pulse's 6 categories), **run all curl commands in parallel** (batch in one response, not sequentially):

```bash
# Batch all queries in one turn — don't serialize 6+ curl calls
curl -sL "query1_URL"
curl -sL "query2_URL"
curl -sL "query3_URL"
# ...all in the same terminal call
```

Then parse each RSS feed separately in Python to categorize results.

### Output Summary per Category

After parsing, produce a structured summary:

```
### Category Name
**Recent items (since [date]):**
- Jul 7 | Story Title | Source | [link]
- Jul 3 | Story Title | Source | [link]
```

Or when results are stale:

```
### Category Name
No recent developments. Latest: [date]
```

## Deduplication

When running multiple queries with overlapping coverage (e.g., "your city NY real estate" and "Schenectady County development"), the same story may appear in multiple feeds. Dedup by:
1. Story `title` (normalized: lowercase, trimmed)
2. Source URL domain
3. For critical dedup, resolve the Google News redirect URL to the actual article

## Pitfalls

- **No `web_extract` fallback:** This technique was developed because `web_extract` wasn't in the toolset. If web_extract becomes available, prefer it for richer content extraction. RSS gives headlines + source + date only.
- **Google redirect URLs:** Links are Google News redirect URLs (`https://news.google.com/rss/articles/CBM...`). These require an extra redirect to resolve to the actual article URL. For pulse reporting, the redirect URL is sufficient for click-through.
- **Rate limits:** Google News RSS doesn't appear to have strict rate limiting, but keep concurrent requests reasonable (5-10 simultaneous is fine).
- **`after=` parameter inconsistency:** Some queries respect it perfectly; others return stale results. Always filter client-side if strict recency matters.
- **Obituaries dominate small-region queries:** When querying a small town/county (e.g., your city NY, Scotia NY), obituaries can make up 30-50% of results. Filter them out with `grep -iv "obituary"` or in your Python parser.
- **Google's RSS use-restriction:** The feed XML includes a copyright notice restricting use to "personal feed reader for personal, non-commercial use." For agent-internal monitoring, this is in a gray area — Google hasn't enforced this against automated readers in practice.
- **No article body:** This gives you headlines + source + date only. For deeper content, combine with web search or browser extraction targeted at specific promising headlines.

## Comparison: Google News RSS vs Alternatives

| Method | Headlines | Bodies | Recency Filtering | Speed | Setup |
|--------|-----------|--------|-------------------|-------|-------|
| **Google News RSS** | ✅ | ❌ | Partial (`after=` param) | Fast (curl) | Zero |
| **Blogwatcher RSS** | ✅ | ❌ | Full (last-scan tracking) | Fast (SQLite) | Requires install + feed config |
| **Web search** (with tool) | ✅ | Via follow-up | Full (if tool supports date) | Slow (browser) | Requires browser/search tool |
| **Web extract** | ❌ | ✅ | N/A | Slow (browser) | Requires tool |

## Usage in This Codebase

Used by the **the operator's Local Pulse** cron job (7am + 9pm ET, expanded June 22, 2026) for 6-category regional news scanning across:
- your city/Schenectady core
- Capital Region business & development
- NY construction & infrastructure
- NY government contracting climate
- NE manufacturing & industrial
- Local market intel (land/property)
