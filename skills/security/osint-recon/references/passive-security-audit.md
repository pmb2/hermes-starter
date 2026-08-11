# Passive Legal Security Audit Methodology

**Use when:** The user asks to audit one or more named entities using only legally permissible passive OSINT techniques (no active scanning, no exploitation, no unauthorized access).

**Scope:** Corporate entity identification, breach history research, technology footprint mapping, attack surface assessment from public data, legal/regulatory history, financial health analysis, leadership profiling, and structured multi-entity audit reporting.

---

## The Ten-Stage Passive Audit Pipeline

### Stage 1: Entity Identification

Identify the exact legal entities behind each named target. Multiple name variants may refer to the same entity.

**Sources:**
- Web search with variations: `"[company name]" company`, `"[company name]" technology`, `"[company name]" LinkedIn`
- Crunchbase / D&B for corporate profiles, funding, and description
- Wikipedia for established companies (history, products, structure)
- State SOS business entity search for registered legal names
- SEC EDGAR (if public company)

**Key output:**
```yaml
TAG Group: The Aspen Group (TAG) — teamtag.com — healthcare support org
ASPEN: Aspen Technology (AspenTech) — aspentech.com — industrial software
DIL: Digital Intelligence Lab SRL — digintlab.com — cyber threat intel
```

**Layering technique:** When the user says "TAG group and ASPEN and DIL" in one breath, first resolve each name independently. TAG may = The Aspen Group (teamtag.com) while ASPEN may = Aspen Technology (aspentech.com), not a subsidiary. Confirm by cross-searching combinations.

### Stage 2: Breach & Incident History

Check each entity against known data breaches, ransomware attacks, security incidents, and regulatory actions.

**Sources:**
- `"[company] data breach"` — web search for news and breach disclosures
- `"[company] CL0P OR ransomware OR MOVEit"` — targeted threat actor search
- UpGuard security reports — vendor risk ratings and breach summaries (upguard.com/security-report/[company])
- BreachSense (breachsense.com/breaches/) — structured breach reports with threat actor, date, leak size
- Class action filings — search PACER or news for lawsuits (`"[company] class action data breach"`)
- Industry-specific regulator actions (HIPAA/HHS breach portal, SEC cyber disclosures)
- HaveIBeenPwned (for known credential dumps)
- CISA alerts and Known Exploited Vulnerabilities catalog

**Breach data format:**
```
Entity: AspenTech
Date: July 14, 2023
Threat Actor: CL0P ransomware group
Vector: MOVEit Transfer zero-day (CVE-2023-34362) — SQL injection + LEMURLOOT webshell
Leak Size: Unknown (likely paid or negotiated)
Impact: Part of 2,700+ org, 93M+ individual global MOVEit campaign
```

**Passive verification:** You cannot confirm leak size without accessing dark web leak sites directly. Note "unknown" where data is not publicly confirmed and label finding as "unverified" if relying on single-source reporting.

### Stage 3: Legal & Regulatory History

This is distinct from breach history — it covers state/federal enforcement actions, consent decrees, class action settlements, and investigations that may NOT involve a data breach.

**Sources:**
- State Attorney General press releases and settlements: `site:oag.ca.gov "[company] settlement"`, `site:mass.gov "[company]"`, `site:ag.ny.gov "[company]"`
- Court records (PACER for federal, state court portals)
- Class action websites: `"[company] class action"`, `"[company] lawsuit settlement"`
- Industry-specific regulatory enforcement (HIPAA for healthcare, SEC for public companies, FTC for consumer protection)
- State corporate practice of medicine/dentistry actions (critical for healthcare DSOs)
- Multi-state AG actions (pattern of enforcement across jurisdictions = systemic issue)

**Legal timeline format:**
```
Entity: Aspen Dental Management Inc. (ADMI) / The Aspen Group
| Year | Jurisdiction | Amount | Allegation |
|------|-------------|-------|------------|
| 2015 | NY AG | $450K + $175K restitution | Corp practice of dentistry |
| 2022 | PA | $175K | Consumer protection |
| 2023 | MA AG | $3.5M | Bait-and-switch advertising |
| 2023 | Multi-state | $4.4M (settlement) | Data breach class action |
| 2026 | CA AG | $2M + $300K restitution | Corp practice + false advertising |
```

**What to look for:**
- **Pattern of repeat offenses** across multiple states — indicates systemic business practice, not isolated incidents
- **Injunctive terms** — AG settlements that restrict HOW the business operates (these are more significant than fines)
- **Private equity implications** — PE-backed DSOs face increasing scrutiny for corporate practice of medicine violations
- **Timing clusters** — multiple actions in short window suggests coordinated regulatory attention

### Stage 4: Technology Footprint

Map the entity's technology stack and cloud infrastructure from public data.

**Sources:**
- LeadIQ / RocketReach tech stack reports (`leadiq.com/c/[company]`) — lists known technologies
- Job postings (LinkedIn, Indeed) — reveal cloud providers, tools, frameworks
  - "Senior Platform Engineer — GCP, Terraform, GKE" = GCP-primary
  - "DevOps Engineer — Azure, ARM templates" = Azure-primary
  - "Cloud Security Engineer" = active security investment
  - No cloud roles = likely on-prem or legacy
- Subdomain discovery — note patterns like `gcp.prod.[company].com`, `app.azure.[company].com`
- BuiltWith / Wappalyzer (via browser) — passive web tech detection
- DNS records (nslookup) — MX, TXT (SPF/DMARC), A/AAAA — public infrastructure data

**Tech stack data format:**
```
TAG (The Aspen Group):
  Cloud: GCP-primary (GKE, Cloud Run, Terraform)
  Secondary: Azure, Cisco
  Web: Adobe Analytics, Apache, ADP, Alcatel-Lucent
  Subdomains: gcp.prod.teamtag.com, tag-dotcom.gcp.prod.teamtag.com
```

### Stage 5: Leadership & Organizational Context

Identify the decision-makers and security maturity level. This goes beyond just security staff — the CEO/ownership structure determines whether security investment happens.

**Sources:**
- LinkedIn: `site:linkedin.com/in "[company]" CEO OR CISO OR VP OR "VP infrastructure" OR founder`
- Bloomberg / MarketScreener executive profiles — compensation, board seats, history
- Crunchbase for founder background, funding history
- News: executive awards, public appearances, controversies
- Political contributions: `site:campaignmoney.com "[name]"` and FEC filings
- Industry recognition (awards = clout; regulatory actions = liability)

**Leadership profile format:**
```
Robert A. "Bob" Fontana — Founder, Chairman & CEO of TAG
- Founded Aspen Dental 1998, Chicago-based
- 2025 Dental Titan Award recipient
- Political contributions: $8,337 (2018 cycle)
- At helm for every legal and security incident (NY 2015, MA 2023, CA 2026, data breach $4.4M)
- Currently managing ~$3B debt refinancing
- Key subordinate: David Raimondi (Security GRC Sr. Mgr), Giorgi Ghviniashvili (VP Infra)
```

**Security maturity indicators:**
| Indicator | Meaning |
|-----------|---------|
| No identifiable security staff | Minimal investment — reactive posture |
| GRC-only roles (compliance manager, audit) | Check-box compliance, not engineering |
| Cloud Security Engineer / AppSec roles | Active engineering investment |
| CISO / VP Security / CRO | Formal program, board-level visibility |
| Post-breach hiring surge | Remediation in progress — incomplete |
| No post-breach hiring found | Either confident or resigned |

**CEO tenure signal:** If the founder/CEO has been in place through multiple legal/security incidents, they bear direct accountability. This is relevant for pressure mapping.

### Stage 6: Financial Health & Ownership Structure

Financial distress directly impacts security funding. PE ownership with debt overhang = budget pressure.

**Sources:**
- **PE ownership**: `"[company] portfolio"` + PE firm name; `american-securities.com/en/companies/`
- **Debt & refinancing**: `"[company] debt OR loans OR maturing"` — Bloomberg, Reuters, WSJ
- **Private company**: PitchBook, Crunchbase, Mergr for funding rounds, valuation, exits
- **Public company**: SEC EDGAR 10-K (risk factors, debt schedule), 10-Q, 8-K earnings releases
- **Earnings pressure**: `"[company] earnings slump OR revenue decline OR losses"`
- **PE exits**: Mergr.com — `"[investor] exits [company]"` — may reveal distress sale

**Financial health format:**
```
TAG (The Aspen Group):
  Ownership: American Securities, Leonard Green & Partners, Ares Management (three PE firms)
  Debt: ~$3B maturing next year (May 2026 Bloomberg report)
  Earnings: Slumping — actively seeking new investors
  Implication: Security budget pressure despite recent breach
```

**Risk signal chart:**
| Signal | Severity | Meaning |
|--------|----------|---------|
| $1B+ debt maturing <2 years | HIGH | Restructuring risk, fire sale pressure |
| PE ownership >5 years with no exit | MEDIUM | Fund timeline pressure — cost cutting |
| Multiple PE co-owners | MEDIUM | Governance complexity, divergent incentives |
| Earnings decline + debt maturity | CRITICAL | Double squeeze — can't grow out of debt |
| Recent PE exit (trade sale) | LOW | Refresh of ownership, possible investment |
| Security hiring freeze | HIGH | Direct indicator of budget constraint |

### Stage 7: Attack Surface Assessment (Passive Only)

Evaluate the entity's exposure using ONLY passive, public-source techniques.

**Passive checks (LEGAL at all times):**
| Check | Method | What It Reveals |
|-------|--------|----------------|
| SSL/TLS cert inspection | crt.sh query | Expiry date, issuer, SANs, subdomain discovery |
| HTTP response headers | curl -I | Server version, security headers (HSTS, CSP, XFO) |
| Login page response | Browser GET | 200 = exposed, 302/301 = redirects, 403 = blocked but exists |
| Subdomain enumeration | Common prefix DNS check | vpn., mail., owa., okta., admin., remote., sftp. |
| Email security | nslookup TXT | SPF/DMARC/DKIM presence and configuration |
| Page source analysis | view-source: | API keys, third-party integrations, JS endpoints, comments |
| Breach data correlation | Web search | Historical incidents, threat actor attribution |
| Job posting analysis | LinkedIn/Indeed search | Infrastructure details, cloud providers, security team size |

**Label system:**
```
LIVE [200] — Endpoint accessible, responds with content
LIVE [302] — Endpoint exists, redirects (still recon value)
LIVE [403] — Endpoint exists but access blocked
LIVE [401] — Auth required (exists)
DOWN [err] — No response / NXDOMAIN
```

**Attack surface data format:**
```
TAG Group:
  - gcp.prod.teamtag.com — LIVE [200] — GCP environment exposed
  - teamtag.com — LIVE [200] — Main site, HIPAA context
  - Cloud Security Engineer role (active hiring) — post-breach remediation in progress
```

### Stage 8: Threat Actor Attractiveness Assessment

Who would want to target this entity and why. This helps the user prioritize defensive or offensive interest.

**Attractiveness factors:**
| Factor | High Value | Low Value |
|--------|-----------|-----------|
| Data type | PHI, PII, credit cards, OT access | Generic marketing data |
| Industry | Healthcare, energy, finance, defense | Low-regulation B2B |
| Size | 1,000+ employees, multiple brands | Small shop |
| Known vulnerability | Recent breach = known attacker access point | No history |
| Supply chain value | Software vendor used by critical infra | Consumer-facing only |
| Controversy | Legal/regulatory targets = reputational hit | Clean record |

**Attractiveness format:**
```
TAG Group: HIGH attractiveness
- PHI/SSN data (breach already proven)
- Healthcare = #1 ransomware target sector
- Multiple brands = wider attack surface
- $3B debt = less security investment likely

AspenTech: HIGH attractiveness
- OT-adjacent software in energy/chemicals/pharma
- MOVEit breach proved they can be hit
- Supply chain leverage over critical infrastructure

DIL: MEDIUM attractiveness
- Cyber intel platform = valuable client data
- Small/startup = less security investment
- But: they ARE security — may be harder target
```

### Stage 9: Cross-Entity Comparison

Compare entities side-by-side across all risk factors for prioritization.

**Comparison matrix:**
```markdown
| Risk Factor       | TAG Group           | AspenTech           | DIL              |
|-------------------|---------------------|---------------------|------------------|
| Known Breaches    | YES (2023, $4.4M)   | YES (2023, CL0P)    | None found       |
| Data Sensitivity  | PHI (HIPAA)         | OT/IP (critical inf)| Client intel     |
| Primary Risk      | PHI exposure, class | OT supply chain     | Intel aggregator |
| Post-Breach Resp  | Active (hiring)     | Published docs      | N/A              |
| Legal/Regulatory  | HIGH (multi-state)  | LOW (one incident)  | NONE             |
| Financial Stress  | CRIT ($3B debt due) | LOW (public co)     | Unknown (small)  |
| CEO Continuity    | Founder since 1998  | Multiple CEOs       | Early stage      |
| Threat Attract    | HIGH (PHI, debt)    | HIGH (OT access)    | MEDIUM (intel)   |
```

### Stage 10: Structured Report

Compile findings into a clear, tiered report:

```markdown
## PASSIVE LEGAL SECURITY AUDIT — [Date]

### Identified Entities
[Entity table with names, domains, sectors]

### Entity 1: [Name]
**Corporate Profile** — structure, size, key personnel
**Known Breach History** — incidents, threat actors, impact, resolution
**Legal & Regulatory History** — AG actions, class actions, consent decrees
**Financial Health** — ownership, debt, earnings, implications
**Technology Footprint** — cloud, web, infrastructure
**Attack Surface Observations** — passive findings with verification labels
**Leadership** — CEO profile, security maturity indicators
**Threat Attractiveness** — who would target this entity and why
**Key Observations** — qualitative assessment

### Entity 2: [Name]
...

### Comparative Risk Summary
[Cross-entity comparison table]

### Recommended Follow-Up
[Suggestions for deeper OSINT on specific attack vectors]
```

---

## Legal Boundary Reminder

Every technique in this pipeline must be:
- Available to any person with a web browser
- Non-intrusive (zero unsolicited packets sent to target servers)
- Sourced from public databases, indexes, or search engines
- Verifiable via documented public sources

**Do NOT** include in a passive audit:
- Port scans (nmap, masscan)
- Vulnerability scans (Nuclei, OpenVAS)
- Directory brute-forcing (gobuster, ffuf)
- Any login attempts or password testing
- Automated crawling/scraping against target sites
- Exploitation of any kind

**Document every finding source** — if challenged, you should be able to say "Here is the public URL/search query I used."

---

## Common Pitfalls

### Entity Name Ambiguity
- **PITFALL**: "TAG group" could = The Aspen Group, Total Automation Group, or TAG International.
- **SOLUTION**: Resolve each name independently before connecting them. Cross-search combinations.
- **WORKAROUND**: Check session history for prior mentions of the same entities by the user.

### Settlements vs. Admissions
- **PITFALL**: A settlement often says "without admitting wrongdoing" — but the payment and injunctive terms are still facts.
- **SOLUTION**: Report the settlement amount AND terms, not just the headline. The injunctive terms tell you what was really wrong.
- **WORKAROUND**: Read the actual consent decree / assurance of discontinuance when available (AG press releases link to them).

### Partial-View Financial Data
- **PITFALL**: Private company financial data is rarely complete.
- **SOLUTION**: Treat Bloomberg reports as directional. Combine debt size, PE ownership duration, and earnings trend for a fuller picture.
- **WORKAROUND**: Use PitchBook/Crunchbase for funding round sizing, news for additional color.

### Correlation vs. Causation in Legal Patterns
- **PITFALL**: Multiple state AG actions against one company may indicate systemic issues OR coordinated multi-state enforcement.
- **SOLUTION**: Check if actions were simultaneous (coordinated) or sequential (pattern).
- **WORKAROUND**: Look for references to other states' actions in AG press releases — if they name-check each other, it's coordinated.

### CEO Accountability Assumptions
- **PITFALL**: Assuming the CEO knows about and approved every legal/security incident.
- **SOLUTION**: Report the CEO as the accountable executive by position, not as personally culpable.
- **WORKAROUND**: Distinguish between "founder/CEO who built the culture" (higher accountability) vs. "professional CEO hired post-PE" (mandated by owners).

---

## Threat Actor / Attacker Motivations Context

When assessing why an attacker might target each entity, consider:

- **Healthcare (HIPAA)**: PHI is the most valuable data on black markets ($50-200/record vs $1-10 for credit cards). Ransomware groups specifically target healthcare for maximum leverage (life safety pressure).
- **Industrial Software (OT-adjacent)**: Access to energy/chemical/pharma OEM software enables supply chain attacks on critical infrastructure. Nation-state actors value this highly.
- **Cyber Intel Platforms**: Client lists and intelligence data are high-value for competitive intelligence or targeting the platform's clients.

---

## Session Worked Examples

### Example 1: Multi-Entity Corporate Security Audit
See the session dated June 23, 2026 (query: "passive legal security audit of TAG group and ASPEN and DIL") for a complete worked example covering:
- Entity resolution for three disparate targets
- Breach history discovery across healthcare, industrial software, and cyber intel
- Legal/regulatory deep-dive (NY 2015, MA $3.5M 2023, CA $2.3M 2026 multi-state pattern)
- Financial stress discovery ($3B debt restructuring at TAG)
- CEO profile (Bob Fontana — founder/CEO since 1998, present for every incident)
- Tech stack inference from job postings and web presence
- Attack surface observations from purely passive sources
- Threat actor attractiveness assessment per entity
- Comparative risk matrix and prioritization

### Example 2: Leadership Deep-Dive
See the session dated June 23, 2026 (follow-up query: "what about Robert Bob Fontana of the Aspen Group?") for a focused executive profile covering:
- Founder/CEO with 28-year tenure and complete accountability for all legal/security history
- Political contributions and industry recognition data
- Cross-reference between executive awards (2025 Dental Titan) and regulatory actions (CA 2026, MA 2023)
- Security team composition reporting to the CEO
- Connection between CEO accountability and organizational pressure points
