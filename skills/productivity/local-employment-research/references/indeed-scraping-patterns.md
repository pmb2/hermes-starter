# Indeed Scraping Patterns

Verified working as of June 2026 against Indeed's SSR HTML.

## URL structure

```
https://www.indeed.com/jobs?q=KEYWORDS&l=CITY%2C+STATE&radius=MILES&sort=date&start=0
```

- `start=0` → page 1, `start=10` → page 2
- Only ~20 results per page even when metadata says more

## Key regex patterns

### Job titles
```python
titles = re.findall(r'jobTitle[^>]*>.*?<span[^>]*title=\"([^\"]+)\"', html)
```
Captures the actual job title text from the span inside the h3.jobTitle element.

### Company names  
```python
companies = re.findall(r'data-testid=\"company-name\"[^>]*>([^<]+)<', html)
```
Uses the semantic testid attribute.

### Locations
```python
locations = re.findall(r'data-testid=\"text-location\"[^>]*>([^<]+)<', html)
```

### Job snippets
```python
snippets = re.findall(r'belowJobSnippet[^>]*>(.*?)</div>', html, re.DOTALL)
```

### Salaries
```python
pays = re.findall(r'salary-snippet[^>]*>([^<]+)<', html)
```
This is fragile — only ~1/3 of job cards have salary shown. The rest show "Check posting".

## User-Agent requirements

Indeed blocks simple curl. Use a realistic Mozilla/Chromium UA:
```
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)
```
Windows UAs also work.

## Sites that DON'T work with curl

- **ZipRecruiter** — full JS render, no SSR content
- **SimplyHired** — full JS render, owned by Indeed
- **Glassdoor** — paywalled after 1-2 views

## Sites that DO work

- **Indeed** (SSR for first ~20 cards)
- **Craigslist job boards** (`https://albany.craigslist.org/search/fbh` for food/bev/hospitality) — clean HTML, easy to parse
