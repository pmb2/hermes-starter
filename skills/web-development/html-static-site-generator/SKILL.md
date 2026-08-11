---
name: html-static-site-generator
version: 1.0.0
description: Generate static HTML tour/landing sites from external API data using string.Template. Covers ChocoData API, Python generator pattern, and GitHub Pages deployment.
category: web-development
metadata:
  hermes:
    tags: [html-template, static-site, generator, string-template, github-pages, deployment, chocodata, zillow, tour]
    triggers:
      - generate a website from api data
      - build a tour page from listing
      - create html from template variables
      - deploy static site to github pages
      - html generator pattern
      - string template vs jinja vs fstring html
    related_skills:
      - scroll-world-hermes
      - local-service-websites
      - astro-site-rebuild
---

# HTML Static Site Generator

Pattern for generating static HTML websites from external API data using Python's `string.Template` — NOT f-strings, NOT jinja2, NOT Astro.

## Why string.Template

| Approach | Problem |
|----------|---------|
| f-strings with `"""` | HTML curly braces (`{}`) and triple-quote template delimiters conflict constantly. Syntax errors on any `}` in CSS or JS. Nearly unreadable at scale. |
| Jinja2 | Adds dependency. Overkill for single-page sites. Complicates deployment. |
| **string.Template** | Python stdlib. `$VAR` / `${VAR}` syntax avoids brace conflicts. `safe_substitute()` handles missing vars gracefully. Template lives in separate `.html` file. |

## File Structure

```
project/
  generate.py          # Python script: fetches API data → build_context → safe_substitute
  template.html        # Pure HTML with $VAR substitution markers
  output.html          # Generated result (gitignored or per-session)
```

The HTML template is a standalone file — can be opened, edited, previewed independently.
The generator only handles data fetching + context building + substitution.

## Generator Pattern

```python
import requests, string

API_KEY = "your_key"

def fetch_data(zpid: str) -> dict:
    """Fetch raw data from external API."""
    r = requests.get(f"https://api.example.com/property?api_key={API_KEY}&zpid={zpid}")
    return r.json()

def build_context(data: dict) -> dict:
    """Transform API data into flat string dict for template."""
    return {
        "TITLE": data.get("name", "").split(",")[0],
        "PRICE": f"${int(data['trade_info'][0]['price']):,}",
        "IMAGES": "|".join(data.get("images", [])),  # pipe-delimited for JS splitting
        # ... 15-30 string vars, all explicitly cast to str
    }

def generate(zpid: str) -> str:
    data = fetch_data(zpid)
    ctx = build_context(data)
    template = open("template.html").read()
    return string.Template(template).safe_substitute(ctx)
```

## Rules

1. **Template is pure HTML** — no Python in the template file. No f-strings, no jinja2 tags. Only `$VAR` for substitution.
2. **All context values are strings** — `build_context()` must convert numbers, lists, dicts to strings. No `None` values.
3. **Use safe_substitute, not substitute** — `substitute` throws `KeyError` on missing vars. `safe_substitute` leaves `$VAR` visible (easy to catch in verification).
4. **Pipe-delimited lists** — for arrays, join with `|` and have JS split them: `const imgs = document.getElementById('data').dataset.images.split('|')`
5. **No f-strings with HTML blocks** — if you're tempted to write 50 lines of HTML inside a Python f-string, you're doing it wrong. Extract to a template file.

## GitHub Pages Deployment

```bash
# Create public repo
gh repo create <name> --public --source=. --push

# Or via API when gh is logged out:
TOKEN=$(git credential-manager get <<< 'protocol=https\\nhost=github.com' | grep ^password= | sed s/^password=//)
curl -X POST -H "Authorization: token $TOKEN" \
  -d '{"name":"<repo>","public":true}' \
  https://api.github.com/user/repos

# Push
cp output.html index.html
git init && git add index.html && git commit -m "init"
git remote add origin https://github.com/pmb2/<repo>.git
git push -u origin master

# Enable Pages
curl -X POST -H "Authorization: token $TOKEN" \
  -d '{"source":{"branch":"master","path":"/"}}' \
  https://api.github.com/repos/pmb2/<repo>/pages
# URL: https://your-username.github.io/<repo>/
# First deploy takes 30-90s. Subsequent pushes cached up to 10min on Cloudflare CDN.
```

Do NOT use cloudflared tunnel for demo hosting — background processes die on this Windows git-bash setup. GitHub Pages is permanent and reliable.

**Social share card (og:image):** when image generation APIs are unavailable or the
card must match the site design exactly, render an HTML card via headless Chrome at
1200x630 and screenshot it — see `references/og-card-headless-chrome.md`.

## Verifying an Update to an Already-Live Pages Site (stale CDN)

After pushing an update to a site already on GitHub Pages, the live URL serves the
PREVIOUS build for 30-90s (sometimes minutes) while Pages rebuilds. A plain 200 proves
nothing about your new content. Correct verification order:

1. **Repo truth first** (bypasses CDN):
   ```bash
   curl -sL "https://raw.githubusercontent.com/<owner>/<repo>/main/<path>" | grep '<marker-from-your-change>'
   ```
   If raw has your new content, the push landed; live URL lag is build time, not a bad push.
2. **Poll the build until built AND the commit matches your push**:
   ```bash
   gh api repos/<owner>/<repo>/pages/builds --jq '.[0] | .status + " | " + .commit'
   # "building" -> "built" (~30-90s); loop sleep 10 up to ~8 checks
   ```
3. **Cache-bust the final live check**: `curl -sL "https://<user>.github.io/<repo>/<path>?v=$(date +%s)"`
4. Only then report "live". Compare content markers (title tag, unique string), never status codes alone.

**Deploy-script relative-path pitfall:** a script copying site files into a sibling
deploy repo must use the correct `../` depth. `/proj/<name>/../deploy-repo` resolves to
`/proj/deploy-repo`, NOT `/deploy-repo` (one level too shallow) — the script silently
copies into the wrong directory and pushes nothing while reporting success. Verify with
`readlink -f "<path>/../deploy-repo"` before trusting it.

## ChocoData Zillow API Data Shape

### Property Endpoint
```
GET /property?api_key={key}&zpid={zpid}&country=us
```

Key fields and types:

| Field | Type | Notes |
|-------|------|-------|
| `name` | str | `"451 Ballston Road, your city, NY, 12302"` |
| `description` | str | Full listing description |
| `images` | list[str] | Array of Zillow CDN URLs — NOT objects with captions |
| `main_image` | str | First image URL |
| `listing_agent` | str | `"Name, Brokerage"` — split on `", "` |
| `trade_info` | list[dict] | `[{"price":"399900","beds":4,"baths":2,"living_area":1880}]` |
| `rooms` | list[dict] | `[{"room_type":"bedroom","count":4}, ...]` |
| `lot_size` | str | Sqft; divide by 43560 for acres |
| `url` | str | Full Zillow URL |
| `year_built` | int | |
| `home_status` | str | `FOR_SALE`, `FOR_RENT`, `SOLD` |

### Zillow Image URL Gotcha

`_bd.jpg` variant **often 404s.** Never upgrade `_d`→`_bd`. Strip `_bd`→`_d`:
```python
def img_hd(url):
    return url.replace("_bd.jpg", "_d.jpg")
```

### Agent name parsing
```python
parts = agent_raw.split(", ")
agent_name = parts[0] if len(parts) > 0 else ""
agent_broker = parts[1] if len(parts) > 1 else ""
```

### Search endpoint returns ZPID-only
```
GET /search?api_key={key}&location=12302&status=for_sale&country=us
```
Results have only `zpid`. Fetch each via property endpoint. Rate limit ~300ms.
**Location quirk:** `"your city,NY"` returns Westchester. Use zip `"12302"` for your city.

## Pitfalls

- **Windows bg processes die** — `cloudflared tunnel --url http://127.0.0.1:7895` exits with code 15 after 20-60s in Hermes background mode. GitHub Pages is the only reliable deployment method on this machine.
- **gh auth expires** — The `gh` CLI token expires periodically. Use `git credential-manager get` to extract the cached token for API calls instead of re-authenticating.
- **Private repo raw URLs 404** — `raw.githubusercontent.com` only serves public repos. For private repos, use the API or make the repo public.
- **`string.Template` vs `Template`** — Import from `string` module: `from string import Template`. Always call `safe_substitute()`, never `substitute()`.
