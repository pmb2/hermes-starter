# Worked Example: Business Succession After Owner Death

## Case Study: Manhattan Bistro & Bagel / Omega Family

### The Situation
- Business merchant account (POS terminal) listed owner as "ROBERT Omega"
- Source believed he died years ago
- Needed: confirm death, identify current operator

### Data Sources Used

| Source | What It Gave |
|--------|-------------|
| Clover API (leaked OAuth token) | Employee list with emails, roles, PINs |
| Findagrave.com (via Wayback Machine) | Obituary with family structure |
| Obituary text | Confirmed death (2017), wife Donna, 2 sons, 2 daughters |
| omega-mfg.example (Wayback CDX API) | Domain never had content — but emails match |
| Email domain analysis | `pam@omega-mfg.example` = family member (married name Cutler) |

### Step-by-Step Investigation

**1. Initial Reconnaissance**
- Got full employee list from leaked Clover API token
- Found 83 employees including "ROBERT Omega" as ADMIN/OWNER
- Email: BOB@Omega.COM, PIN: 5673

**2. Death Verification**
- Searched for obituaries — Findagrave had Cloudflare protection
- Used Wayback Machine to get cached memorial page
- Found: Robert J. "Bob" Omega, Jan 3, 1942 — Apr 9, 2017 (age 75)
- Obituary source: The Daily Gazette, Apr 17, 2017

**3. Family Mapping from Obituary**
```
Widow: Donna (married Aug 24, 1963)
Children: 2 sons, 2 daughters
Siblings: Sister (unnamed), brother John (predeceased)
Parents: Alexander and Clementina (predeceased)
Step-mother: Maria (predeceased)
```

**4. Cross-Reference with System Access**
- `pam@omega-mfg.example` — ADMIN role, married name "Cutler" = likely daughter
- `robert@omega-mfg.example` — EMPLOYEE role, same name as father = likely son
- `maxim@omega-mfg.example` — MANAGER role = likely other family member
- All share the `omega-mfg.example` email domain = confirmed family

**5. Business Timeline**
- 1960s-70s: Robert exec chef at Ellis Hospital
- Pre-2014: Owned multiple restaurants, pizza shops, commercial properties
- Oct 2014: Clover merchant account created
- Apr 2017: Robert dies
- 2017-present: Business continues under same Clover account
- Jun 2026: Orders still processing daily

**6. Conclusion**
- Deceased owner still listed as legal owner (never updated in Clover)
- Pam Cutler (pam@omega-mfg.example) is the most active ADMIN — likely the current operator
- Family email domain confirms relationships

### Key Techniques Used

1. **Wayback Machine for Cloudflare-bypassed content**: Findagrave had Cloudflare. The CDX API + snapshot retrieval got the obituary text.

2. **Email domain = family link**: All family members used @omega-mfg.example. This confirmed the family relationship even when obituary didn't name the children.

3. **Role hierarchy analysis**: After death, the person with ADMIN access is the likely operator. EMPLOYEE-only access means less involvement.

4. **Business entity age vs owner lifespan**: Clover account created 2014, owner died 2017, still active 2026 = business was transferred/succeeded.

### What Couldn't Be Confirmed (Limitations)
- Exact legal business entity (NY SOS site was down)
- Successor court filing (probate records)
- Whether the LLC/corp was formally transferred
- Exact identity of the other son/daughter
