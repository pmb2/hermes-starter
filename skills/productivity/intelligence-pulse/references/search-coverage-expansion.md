# Search Coverage Expansion — June 22, 2026

## Context
the operator asked to "expand the monitoring pipelines search coverage." The system had 57 cron jobs. This document captures the audit-and-expand pattern used.

## Inventory Gathered
All 57 jobs inventoried via `cronjob(action='list')`. Filtered to those with web-search capability (web in enabled_toolsets, gpt-researcher skill, or explicit search queries in prompts).

## Pipelines Expanded (7 total)

| Pipeline | Frequency | Key Additions |
|----------|-----------|---------------|
| C2C Hunter | every 4h | AI/ML Engineering, DevOps/SRE, MedTech BioTech, GovCon/FedRAMP |
| FL Real Estate Pulse | daily 7am | Spec builder intel, institutional land buying, national macro, wholesale |
| FAR/C2C Regulatory Monitor | daily 6:30am | GovCon RFP tracking, FedRAMP/CMMC, SBIR/STTR, AI regulation |
| Cyber Night Research | daily 10pm | Zero-day exploit market, infostealer, ICS/OT, supply chain |
| Local Pulse | 7am+9pm | Capital Region business, NY construction, NY GovCon, NE manufacturing |
| Consolidated Pulse Scan | every 4h | AI/ML ecosystem, MCP/agent infra, open source AI, MES tech |
| Weekly Strategy Pulse | weekly Monday | See trumpian-accounting-kb monitoring config below |

### New AI/ML Ecosystem Pulse Created
Standalone every-6h pipeline tracking: new model releases, API/provider changes (pricing, deprecations), coding tools, frameworks, security/regulation, market/funding.

## Trumpian Accounting KB — Config Expansion

The `monitoring/config.yaml` at `~/trumpian-accounting-kb/monitoring/config.yaml` was expanded from 7 to 10 categories:

### Added `fl_land_intel`
10 queries covering: property tax assessment reform, SB 1848 disclosure law, Sarasota/Charlotte county appraiser notices, North Port building permits, Port Charlotte development approvals, national builder lot acquisition trends, wholesale market, southwest Florida builder demand.

### Added `govcon_c2c_intel`
10 queries covering: FAR overhaul, CMMC 2.0 deadlines, NIST 800-171 rev 3, clearance reform NDAA, CISA directives, defense contractor cybersecurity, SAT threshold changes, DoD cloud awards, GSA IT modernization, FedRAMP updates.

### Added `opportunity_signals` (wildcard catch-all)
10 broad queries covering: AI business opportunities, side hustle/passive income, grant funding/startup accelerators, creative real estate finance, digital product marketplaces, consulting niches, unconventional money-making, emerging markets, tax lien investing, AI automation services.

### Scoring Keywords Added
`run_monitor.py` was updated with relevance keyword arrays for all 3 new categories so findings get properly scored 0-1.

### KB Chapter Stubs Created
`10-fl-land-intel.md`, `11-govcon-c2c-intel.md`, `12-opportunity-signals.md` — with descriptions and category metadata.

### Category Naming Principle Applied
Originally named `track_a_land` and `track_b_consulting` (rigid strategic-track framing). Renamed to `fl_land_intel` and `govcon_c2c_intel` (domain-descriptive) per the operator's explicit feedback: "Don't keep it so rigid between Track A and Track B. We needed more dynamics."

## Key Lessons

1. **Inventory before expanding** — Don't guess what exists. Pull the full cron list.
2. **Domain names, not track names** — Categories should describe what they search, not what strategy pillar they serve.
3. **The wildcard matters** — `opportunity_signals` catches what rigid categories miss. Every monitoring system needs one.
4. **Verify with dry-run** — Script-based monitors: always run `--dry-run` to confirm config loads.
5. **Update the pipeline prompt too** — The prompt that runs the pipeline also needs to reference the new categories or it won't cross-reference them.
