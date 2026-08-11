# Federal Register API — Query Reference

## Base Endpoint
```
https://www.federalregister.gov/api/v1/articles.json
```
Works reliably via `terminal` curl in many sessions. Session-variable (may return timeouts).

## Query Parameter Reference

### Date Range Filtering
```
conditions[publication_date][gte]=2026-01-01
```
Combine `[gte]` (>=) and `[lte]` (<=) for windows. Use ISO date format YYYY-MM-DD.

### Keyword / Term Search
```
conditions[term]=artificial+intelligence+regulation
```
URL-encoded single term. For multi-word concepts use `+` (space). Complex boolean operators (OR) are handled server-side — use them sparingly; simple single-term queries are more reliable.

### Agency Filtering
The API accepts agency names directly (no ID needed):
```
conditions[agencies]=FTC
conditions[agencies]=Department+of+Labor
```

## Working Query Patterns (verified Jul 3 2026)

### AI Regulation
```
?conditions[term]=artificial+intelligence+regulation&conditions[publication_date][gte]=2026-01-01&per_page=10
```
### FTC Actions
```
?conditions[agencies]=FTC&conditions[publication_date][gte]=2026-05-01&per_page=10
```
### Independent Contractor / DOL
```
?conditions[term]=independent+contractor+classification&conditions[publication_date][gte]=2026-01-01&per_page=5
```
### Data Privacy / Breach Notification
```
?conditions[term]=data+broker+OR+data+privacy+OR+breach+notification&conditions[publication_date][gte]=2026-01-01&per_page=10
```
### FAR / Procurement
```
?conditions[term]=Federal+Acquisition+Regulation&conditions[publication_date][gte]=2026-05-01&per_page=10
```

## Parsing Results with Python

```python
curl -sL --max-time 15 "https://www.federalregister.gov/api/v1/articles.json?conditions[term]=<query>&per_page=10" | \
python3 -c "
import sys,json
data=json.load(sys.stdin)
for a in data.get('results', data.get('articles', [])):
    print(f\"{a.get('publication_date','')} | {a.get('title','')[:120]}\")
    agencies = ', '.join([ag.get('name','') for ag in a.get('agencies',[])])
    print(f'  Agencies: {agencies}')
    print(f'  URL: https://www.federalregister.gov/d/{a.get(\"document_number\",\"\")}')
    print()
"
```

## Parsing Results without Python (Cron Context — Fallback)

When `python3 -c` is unexpectedly unavailable (rare), use grep-based field extraction from saved JSON files:

```bash
# Fetch and save
curl -sL --max-time 15 "https://www.federalregister.gov/api/v1/articles.json?conditions%5bterm%5d=artificial+intelligence&per_page=20" -o fr_results.json

# Extract titles
cat fr_results.json | grep -o '"title":"[^"]*"' | head -20

# Extract abstracts (first 200 chars)
cat fr_results.json | grep -o '"abstract":"[^"]\{0,200\}' | head -5

# Extract agencies
cat fr_results.json | grep -o '"raw_name":"[^"]*"' | head -20

# Extract publication dates
cat fr_results.json | grep -o '"publication_date":"[^"]*"' | head -20

# Extract URLs (html_url for each doc)
cat fr_results.json | grep -o '"html_url":"[^"]*"' | head -20
```

**Important:** The JSON response is a single long line. Do NOT use `read_file` to inspect it directly — `read_file` treats it as one line and truncates at the buffer limit, showing only the first result. Always grep from the terminal on the saved file.

## MSYS/Windows curl URL Encoding

When running curl from git-bash/MSYS (this environment), square brackets `[` and `]` in query parameters are interpreted as glob patterns by the shell. **All square brackets must be URL-encoded:**

| Wrong (fails) | Right |
|--------------|-------|
| `conditions[term]=AI` | `conditions%5bterm%5d=AI` |
| `conditions[agencies]=FTC` | `conditions%5bagencies%5d=FTC` |
| `conditions[publication_date][gte]=2026-06-01` | `conditions%5bpublication_date%5d%5bgte%5d=2026-06-01` |

Without encoding you'll get curl exit code 3 ("URL malformed format") or empty results with exit 0 if MSYS silently drops the bracketed parameters.

## Reference Query Patterns (verified July 7 2026)

### AI Regulation — Known Agency IDs
| Agency | Name | ID (confirmed) |
|--------|------|---------------|
| FTC | Federal Trade Commission | 192 |
| DOL | Labor Department | 271 |
| EOP | Executive Office of the President | 538 |
| OFPP | Office of Federal Procurement Policy | 184 (child of 280-OMB) |
| GSA | General Services Administration | 210 |
| SBA | Small Business Administration | (TBD) |
| DOC | Commerce Department | 54 |

**Note:** `conditions[agency_ids][]=N` uses numeric ID and is precise. `conditions[agencies]=Name` uses name matching which may be more flexible. Try name-based first, fall back to ID-based if name gives broad results.

## Individual Article Detail Endpoint

### Correct URL Pattern
```
https://www.federalregister.gov/api/v1/articles/{document_number}
```
Use the bare document ID — no date path, no `.json` suffix.

**Example — Fetch FTC AI Accuracy Policy Statement detail:**
```bash
curl -sL --max-time 20 "https://www.federalregister.gov/api/v1/articles/2026-13628" | \
python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'Title: {d.get(\"title\",\"\")}')
print(f'Comments close: {d.get(\"comments_close_on\",\"N/A\")}')
print(f'Abstract: {d.get(\"abstract\",\"\")[:300]}')
print(f'Action: {d.get(\"action\",\"\")}')
print(f'Regs.gov: {d.get(\"comment_url\",\"N/A\")}')
"
```

### Wrong URL Patterns (Return 404 or Trigger Blocks)
- `/api/v1/articles/2026/07/07/2026-13628.json` — date-based path returns 404
- `/api/v1/articles/2026-13628.json` — the `.json` suffix may trigger a Cloudflare/Turbo challenge

### Key Fields on Individual Articles
| Field | Description | Example |
|-------|-------------|---------|
| `publication_date` | FR publication date | `2026-07-07` |
| `comments_close_on` | Comment deadline (ISO date) | `2026-07-31` |
| `effective_on` | Effective date (null for proposals) | `null` |
| `action` | Rule type label | `Proposed policy statement; request for comments.` |
| `abstract` | Summary text | `The Federal Trade Commission...` |
| `comment_url` | Link to regulations.gov docket | `http://www.regulations.gov/commenton/FTC-2026-0859-0013` |
| `html_url` | FR full-text page | `https://www.federalregister.gov/documents/2026/07/07/2026-13628/...` |
| `document_number` | FR document ID | `2026-13628` |
| `citation` | FR volume/page | `91 FR 41638` |
| `dates` | Human-readable dates section | `Comments must be received on or before Friday, July 31, 2026.` |
| `full_text_xml_url` | **Full document text URL (XML)** | `https://www.federalregister.gov/documents/full_text/xml/2026/07/07/2026-13628.xml` |

**Important:** Use `comments_close_on` to get the comment deadline — the field `comment_date` does not exist in the API response.

### Full-Text Extraction via full_text_xml_url

When the API `abstract` is too generic (common for FTC consent orders where every abstract says "consent agreement settles alleged violations of Federal law"), use `full_text_xml_url` to extract the complete document.

The XML URL **bypasses the FR HTML page CAPTCHA** and returns the full regulatory text including SUPPLEMENTARY INFORMATION, policy analysis, statutory references, and enforcement rationale.

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

This extracted the full FTC AI Accuracy Policy Statement details (Jul 2026) including state-law preemption discussion, E.O. 14319/14365 references, Colorado AI Act revision notes, and the Section 5 application framework — none of which appeared in the API abstract alone.

**Workflow for deep document extraction:**
1. Search FR API for relevant articles
2. Filter by title/publication date for articles of interest
3. Fetch individual article detail: `curl /api/v1/articles/{doc_number}`
4. Extract `full_text_xml_url` from the response
5. Fetch the XML URL and parse with python3 as above

## Known Pitfalls
- **Single-article endpoint with `.json` suffix** (`/api/v1/articles/{document_number}.json`) may trigger a Cloudflare challenge — use the bare endpoint without `.json` instead. The bare `/api/v1/articles/{document_number}` works reliably via `terminal` curl.
- **`comments_close_on` field** — the comment deadline is stored in this field, NOT in `comment_date` which doesn't exist in the API. Use `d.get('comments_close_on', 'N/A')` when parsing article detail.
- **The `results` key may be absent** if the query returns zero matches — guard with `.get('results', data.get('articles', []))` as above.
- **FTC press releases** often have generic abstracts ("consent agreement settles alleged violations of Federal law"). Look for company names in titles to identify enforcement targets.
- **Response is paginated** — default `per_page=10`. Bump to `per_page=100` for full sweeps.
- **MSYS/Windows curl:** Square brackets in query params must be URL-encoded as `%5b`/`%5d` or curl fails with exit code 3.
- **read_file cannot parse single-line JSON:** The API response is a single JSON line — read_file shows only the first ~1000 chars. Use `grep -o` from terminal on saved file instead.
