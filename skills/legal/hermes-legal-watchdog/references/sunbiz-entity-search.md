# Sunbiz Entity Search — CDP Browser Workflow

FL Division of Corporations entity search via CDP browser. This is the canonical way to check LLC/corporation annual report filing status, entity standing, and registered agent info.

## URL Structure

| Page | URL | Notes |
|------|-----|-------|
| Search By Name | `https://search.sunbiz.org/Inquiry/CorporationSearch/ByName` | Preferred entry point. Direct form, no alphabetical page-through. |
| Search Results | `https://search.sunbiz.org/Inquiry/CorporationSearch/SearchResults/EntityName/{NAME}/Page1` | Auto-navigated after form submit. |
| Detail Screen | `https://search.sunbiz.org/Inquiry/CorporationSearch/SearchResultDetail?inquirytype=EntityName&...` | Aggregate ID in URL. Annual report history + status live here. |

## Search Flow (CDP Browser)

### 1. Navigate to Search By Name
```
mcp_chrome_devtools_mcp_new_page(url="https://search.sunbiz.org/Inquiry/CorporationSearch/ByName")
```

### 2. Take Snapshot & Identify Form Fields
- Entity Name textbox uid (varies per load, typically 3_15 on first visit)
- Search Now button uid (typically 3_16)

### 3. Fill Form & Submit
```
mcp_chrome_devtools_mcp_fill_form(elements=[{"uid":"3_15","value":"<you> SOLUTIONS LLC"}])
mcp_chrome_devtools_mcp_click(uid="3_16")
```

### 4. Locate Entity in Results
Take snapshot. The result list shows Corporate Name, Document Number, and Status columns. Click the entity link by uid to view detail.

| Status Value | Meaning |
|-------------|---------|
| Active | Entity in good standing |
| INACT | Dissolved or revoked — needs reinstatement |
| INACT/UA | Inactive, unavailable |
| RPEND/UA | Revocation pending, unavailable |
| CROSS RF | Cross reference filing |
| NAME HS | Name hold status |

### 5. Read Detail Screen
Key fields on the Detail screen:
- **Status** — must be ACTIVE for good standing
- **Date Filed** — formation date. Used to determine if first annual report is due yet.
- **Annual Reports section** — lists each report year and filed date. Verify current year appears.
- **Registered Agent Name & Address** — verify this is the operator's agent.
- **FEI/EIN Number** — federal tax ID for the entity.

### 6. Verify Annual Report Status
The Annual Reports table lists years in descending order. For entity formed before current year:
- Current year's report should be present with a filed date
- If current year is missing and it's after May 1: entity is late, owes $400 penalty
- If current year is missing and it's before May 1: not yet due

## Pitfalls & Edge Cases

### New LLC Exception
An LLC formed in the current calendar year (e.g., filed Jan 2026) does NOT owe its first annual report until May 1 of the following year (2027). The Annual Reports table will show no current year entry — this is normal, NOT a delinquency. Always check Date Filed before flagging.

### Same-Name Disambiguation
Multiple entities with similar names appear in search results (e.g., 40+ "Backus" entities in FL). Always verify by:
1. Document Number (unique per entity)
2. Registered Agent name (the operator M Backus or Julie Belote for the operator's entities)
3. Principal Address (matches known location)

### Duplicate Entity Table (Sunbiz Search Results Bug)
When searching an entity name that exists in exact or partial form, Sunbiz returns a paginated alphabetical list starting from the search term. The first page may show entities alphabetically adjacent to the search term. Click the entity link in the list to view detail — this is more reliable than relying on the URL path.

### Page Management
Each search opens a new browser page. After reading a detail screen, close it via `mcp_chrome_devtools_mcp_close_page(pageId=N)` to avoid accumulating tabs. Only keep the current search tab and the about:blank initial tab open.

## Entity Data for the operator's Operations

### <you> SOLUTIONS LLC
| Field | Value |
|-------|-------|
| Document Number | L07000103471 |
| FEI/EIN | 26-1222215 |
| Date Filed | 10/11/2007 |
| Status | ACTIVE |
| Registered Agent | BELOTE, JULIE |
| Principal Address | 2455 HOLLYWOOD BLVD, SUITE 204, HOLLYWOOD, FL 33020 |
| Annual Reports | Filed every year since 2008. 2026 filed 02/06/2026. |

### THE the operator LLC
| Field | Value |
|-------|-------|
| Document Number | L23000016154 |
| Date Filed | 01/06/2023 |
| Status | INACT |
| Registered Agent | BACKUS, the operator M |
| Principal Address | 4090 HODGES BLVD APT 1504, JACKSONVILLE, FL 32224 |
| Note | Inactive — reinstatement needed if still in use. |
