# Florida Sunbiz Entity Search

Florida Sunbiz (Sunbiz.org) is the Florida Department of State's Division of Corporations business entity search portal. This reference covers efficient lookup of FL-registered entities, status interpretation, and batch-search technique.

## Direct Search URL

Construct the search URL directly without navigating the homepage form:

```
https://search.sunbiz.org/Inquiry/CorporationSearch/SearchResults/EntityName/{URL_ENCODED_NAME}/Page1
```

**Examples:**
```
AG REAL ESTATE GROUP LLC → AG%20REAL%20ESTATE%20GROUP%20LLC
MT&T REALESTATE LLC      → MT%26T%20REALESTATE%20LLC
D&T BAILEY ENTERPRISES   → D%26T%20BAILEY%20ENTERPRISES%20LLC
```

## Status Codes on Sunbiz

| Status Shown | Meaning |
|---|---|
| **Active** | In good standing |
| **INACT** | Inactive / Dissolved |
| **InActive** | Inactive (same as INACT, different formatting) |
| **INACT/UA** | Inactive — Unavailable (usually final dissolution) |
| **NAME HS** | Name history — name was changed or the entity had a different name previously; the current active name may differ |
| **RPEND/UA** | Revocation Pending / Unavailable |

Note: Sunbiz uses multiple inconsistent casing/spellings for the same status (`INACT`, `InActive`, `INACT/UA`). Treat all variations ending in INACT/InActive as "Inactive."

## Fuzzy Matching Behavior

Sunbiz search is **very fuzzy** — it will match partial names and return entities sharing a common prefix. For example, searching "LINCOLNSHIRE ESTATES LLC" returns all entities starting with "LINCOLNSHIRE". **Always verify exact match** between the searched name and the first column in results.

**Name variations you may see:**
- Comma differences: `Z REAL ESTATE INVESTMENTS , LLC` vs `Z REAL ESTATE INVESTMENTS LLC`
- Extra spaces: `TDF REAL  ESTATE INVESTMENTS LLC` (double-space before ESTATE)
- Punctuation: `MT&T REALESTATE, LLC` vs `MT&T REALESTATE LLC`
- Plural/singular: `MATOS REAL ESTATES INVESTMENTS LLC` vs `MATOS REAL ESTATE INVESTMENTS LLC`

Treat minor punctuation/whitespace differences as the same entity. Treat word differences (ESTATE vs ESTATES, INVESTMENT vs INVESTMENTS) as potentially different entities and flag them.

## Efficient Batch Search (Chrome DevTools MCP)

When checking many entities (10+), use the Chrome DevTools MCP's `evaluate_script` tool instead of taking full page snapshots. This extracts the table data in a single call:

### Workflow

1. **Open individual pages** for each entity:
   ```
   mcp_chrome_devtools_mcp_new_page(url="https://search.sunbiz.org/.../{ENCODED_NAME}/Page1")
   ```

2. **Extract table data via evaluate_script** (faster than snapshot):
   ```javascript
   () => {
     const table = document.querySelector('table');
     if(!table) return 'no table';
     const rows = table.querySelectorAll('tr');
     const results = [];
     rows.forEach(row => {
       const cells = row.querySelectorAll('td, th');
       if(cells.length >= 3) {
         results.push(
           cells[0]?.textContent?.trim() + '||' +
           cells[1]?.textContent?.trim() + '||' +
           cells[2]?.textContent?.trim()
         );
       }
     });
     return results.join('\n');
   }
   ```

3. **Select page** before evaluating:
   ```
   mcp_chrome_devtools_mcp_select_page(pageId=N)
   ```

### Pitfall: Iteration / Tool Call Limits

Each entity requires at minimum 2 tool calls (new_page + evaluate_script or select_page + evaluate_script). For 32 entities, this means ~64 tool calls just for lookup, plus the compilation of results. If other work is happening in the same session, the total tool call limit may be reached before completion.

**Mitigation:**
- Batch entities into manageable groups (10-15 per session)
- If using CDP MCP, close pages after reading them to reduce memory/state
- For very large batches (50+), consider a terminal-based approach using curl to hit Sunbiz's underlying API if available, or a Python script that submits form searches

## Verification Steps

After each entity search:
1. Check the first row in the results — does its name match your search target?
2. If matched, read the Status column (3rd column)
3. If the first page has no match but results exist, check the "Next List" link — the entity may be on page 2+
4. Record: Entity Name, Document Number, Status
