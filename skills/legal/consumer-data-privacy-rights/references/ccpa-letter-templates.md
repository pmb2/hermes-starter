# CCPA/CPRA Data Privacy Request Templates

6 standardized letter templates for exercising data rights under CCPA/CPRA.
See the SKILL.md for which template to use and when.

## Templates Included

1. **DSAR (Right to Know)** — Request a full copy of all personal information held
2. **Right to Delete** — Request deletion of all personal information
3. **Combined DSAR + Deletion (Preferred)** — One letter for both actions
4. **Right to Opt-Out of Sale/Share** — For ad-supported/broker services
5. **Request to Correct** — Fix inaccurate data found in DSAR response
6. **Follow-Up/Demand Letter** — For businesses past statutory deadlines

## Usage Pattern

For most services, use Template #3 (Combined). This sends one request that:
1. Demands a full data copy (fulfilling Right to Know)
2. Immediately requests deletion of all data upon receipt

This is the most efficient approach — one 45-day window for both actions.

## Email + Addressing for Reply Tracking

Use Gmail's +addressing feature to track which requests get responses:

```
From: youraccount2+equifax@gmail.com
```

Every response to +equifax lands in your inbox but is tagged, making it
trivial to filter, search, and prove delivery to a specific company.

Set up Gmail filters:
- `to:(+equifax)` → label "Equifax" / skip inbox / star
- `to:(+experian)` → label "Experian"

For batch generation, the personal_config.yaml approach auto-generates
these per company using `[base]+[company-tag]@gmail.com`.

## Key Fields to Fill Per Service

| Field | Source |
|-------|--------|
| Company name | Service being contacted |
| Privacy email/portal | Website footer or privacy policy |
| Customer identifiers | Account emails, usernames, order numbers |
| Full name | Legal name |
| Address | Physical address for certified mail |
| Email | +addressed email for tracking |
