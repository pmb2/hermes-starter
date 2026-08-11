# Obituary Extraction via Wayback Machine

When a subject is deceased, obituaries are a goldmine of family relationships, career history, and property ownership. The problem: most sites hosting them (Findagrave, Legacy, funeral homes) use Cloudflare or CAPTCHAs that block automated access.

## The Technique

**Step 1: Find the site that has the obituary**

Search engine curl queries are blocked, so use direct site navigation. For deceased persons in the US, check:
- `findagrave.com/memorial/search?firstName=X&lastName=Y` — search page sometimes works with curl
- `legacy.com/obituaries/search?q=X+Y` — often blocks curl
- `<funeralhome>.com/obituary/X-Y` — varies, small funeral homes may not have anti-bot

**Step 2: Extract the memorial/obituary ID**

From findagrave search results, grep for the memorial URL pattern:
```bash
grep -oP '/memorial/[0-9]+/[^\"'"'"']+' response.html
# Returns: /memorial/178447396/robert-j-Omega
```

**Step 3: Check Wayback Machine for archived snapshots**

```bash
# CDX API - returns JSON array of archived timestamps
curl -s "https://web.archive.org/cdx/search/cdx?url=example.com/path&output=json&limit=5"

# For findagrave specifically:
curl -s "https://web.archive.org/cdx/search/cdx?url=findagrave.com/memorial/178447396/*&output=json&limit=3"
```

The CDX API returns rows like:
`["org","findagrave.com","/memorial/178447396/robert-j-Omega","20260618121225","https://www.findagrave.com/memorial/178447396/robert-j-Omega",...]`

The timestamp (e.g. `20260618121225`) is the archive key.

**Step 4: Load the archived snapshot**

```
https://web.archive.org/web/{timestamp}/{original_url}
```

Example:
```
https://web.archive.org/web/20260618121225/https://www.findagrave.com/memorial/178447396/robert-j-Omega
```

**Step 5: Extract obituary data**

The archived page contains the full obituary text, not just the summary. Grep for key patterns:
```bash
# Find birth and death dates
grep -oP 'Birth[^<]{0,50}' page.html | sed 's/<[^>]*>//g'
grep -oP 'Death[^<]{0,50}' page.html | sed 's/<[^>]*>//g'

# Find survivor names
grep -oP '(Surviv|wife|husband|daughter|son|sister|brother|grandchild)[^<]{0,200}' page.html | sed 's/<[^>]*>//g'
```

## Real-World Example

Target: Robert J. "Bob" Omega, Schenectady NY

```bash
# Step 1: Search findagrave (worked via curl)
curl -s "https://www.findagrave.com/memorial/search?firstName=Robert&lastName=Omega" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) ..."

# Step 2: Extract memorial ID from search results
# Found: /memorial/178447396/robert-j-Omega

# Step 3: Check CDX API
curl -s "https://web.archive.org/cdx/search/cdx?url=findagrave.com/memorial/178447396/*&output=json&limit=3"

# Step 4: Load snapshot
curl -s "https://web.archive.org/web/20260618121225/https://www.findagrave.com/memorial/178447396/robert-j-Omega" \
  -H "User-Agent: Mozilla/5.0"

# Step 5: Extract
# Found: Birth 3 Jan 1942, Death 9 Apr 2017 (age 75)
# Found: Wife Donna (married Aug 24, 1963)
# Found: 2 sons, 2 daughters
# Found: Career - executive chef at Ellis Hospital, owned restaurants
# Found: Obituary source - The Daily Gazette Co., Apr 17, 2017
```

## Backup: Funeral Home Obituaries

If the funeral home is known, check their site directly. DeMarco-Stone Funeral Home example:
```
https://www.demarcostone.com/obituary/Robert-Omega
```
These may also be Cloudflare protected. Use Wayback Machine same as above.

## Cross-Reference With Business Systems

Once you have the obituary's survivor list, cross-reference against any accessible business systems (POS, CRM, payroll) to identify who is currently running the business:

| Obituary survivor | Business system match | Conclusion |
|------------------|----------------------|------------|
| Wife (Donna) | - | May not be in POS system |
| Daughter (Pamela, married Cutler) | Pam Cutler, ADMIN, pam@omega-mfg.example | Current operator |
| Son (Robert Jr.) | Robert Omega, EMPLOYEE, robert@omega-mfg.example | Works in business |
| Other family | maxim@omega-mfg.example, MANAGER | Family member |

## Limitations

- **Funeral home sites**: often Cloudflare protected, may not have Wayback snapshots
- **Newspaper obituaries**: often behind paywalls (Daily Gazette, Times Union, etc.)
- **Recent deaths**: may not yet be archived by Wayback Machine
- **Findagrave**: memorial pages are Cloudflare protected; only the search page works via curl
