# FOSS Research: Legal AI Agent Team (Team 05)

> Research conducted May 29, 2026 during legal team provisioning session.
> Captures all existing FOSS tools identified for each agent role.

## Core Infrastructure (MIT/Apache/BSD/CC0)

| Tool | What It Provides | License | For Agent |
|------|-----------------|---------|-----------|
| **CourtListener** (freelawproject/courtlistener) | Full federal + state case law, PACER dockets, citation analysis, RSS + REST API | BSD-3 | Legal Coordinator, Cybercrime Defense, Criminal Defense Intel |
| **Harvard CAP** (case.law) | 6.4M case texts (1658-2020), citation graph | MIT/CC0 | Legal Coordinator |
| **python-congress** (unitedstates/python-congress) | Congress.gov full API: bills, amendments, committees | CC0 | Legal Coordinator |
| **fr-notices** (unitedstates/fr-notices) | Federal Register API: proposed rules, final rules | CC0 | Financial & Regulatory |
| **uscode XML** (unitedstates/uscode) | Full US Code in structured XML | CC0 | All agents |
| **gpo-congress** (unitedstates/gpo-congress) | Full bill text, Congressional Record, Public Laws | CC0 | Legal Coordinator |
| **edgartools** (edgartools/edgartools) | SEC EDGAR filings: 10-K, 10-Q, 8-K, XBRL | MIT | Corporate & Entity, Financial & Regulatory |
| **feedparser** | Universal RSS/Atom parsing | BSD-2 | Legal Coordinator |
| **LexNLP** (LexPredict/lexnlp) | Legal NLP: citation parsing, entity extraction, statute recognition | Apache 2.0 | All agents (NLP pipeline) |
| **openstates** | All 50 state legislatures: bills, votes, committees | GPL-3.0 | Legal Coordinator |
| **Legal-BERT** (nlpaueb/legal-bert-base-uncased) | Pre-trained legal text transformer | MIT | Privacy & Evidence |
| **CaseHold** (reglab/casehold) | Legal holding identification model | Apache 2.0 | Cybercrime Defense |
| **DPV** (w3c/dpv) | Data Privacy Vocabulary — privacy law ontology | MIT | Privacy & Evidence |
| **Arelle** (Arelle/Arelle) | XBRL parser and SEC filing analyzer | Apache 2.0 | Corporate & Entity |
| **SupremeCourtDB** | SCOTUS case data, justice voting patterns | CC0 | Criminal Defense Intel |
| **OpenCorporates** | Corporate registry data (global) | AGPL | Corporate & Entity |
| **Huginn** | Self-hosted agent automation: scrape, monitor RSS, trigger actions | MIT | Orchestration layer |

## Data Sources (Free, No Tool Needed)

- GovInfo.gov API (GPO) — US Code, Federal Register, Congressional Record
- Congress.gov API — Bills, laws, congressional proceedings
- SEC EDGAR Full-Text Search — Corporate filings
- DOJ Press Releases RSS — Enforcement actions, indictments
- regulations.gov — Public comments, docket tracking
- SCOTUS opinions — Free HTML/PDF

## Key Gaps (No Mature FOSS — Must Build)

- CCPA/CPRA real-time amendment tracker — no FOSS tracks state privacy law amendments
- BOI/CTA automated compliance — FinCEN has no API, Selenium-based only
- Jurisdiction routing decision engine — no decision tree for entity formation state selection
- Criminal statute-specific case monitor (CFAA, RICO, wire fraud) — build atop CourtListener filtering 18 USC § citations
- DOJ enforcement trend analyzer — no structured DB of DOJ criminal actions
- Multi-state privacy law comparison engine — no unified schema across state laws

## Paid Upgrade Recommendations

| FOSS Option | Paid Upgrade | When Worth It |
|-------------|-------------|---------------|
| OpenStates (free) | OpenStates Pro ($199/mo) | Real-time webhooks for state bill changes |
| CourtListener (free) | Donation tier | Higher API limits |
| RECAP (crowd-sourced) | PACER fee account (~$0.10/page) | Complete federal docket access |
| OpenCorporates API | OpenCorporates Pro | Bulk entity search, corporate tree |
| CAP citation graph | Shepard's (LexisNexis)/KeyCite (Westlaw) | Validity flags (overruled/distinguished) |
| Boomi/FileForms (none) | FileForms (~$50-200/entity) | Automated BOI/CTA filing |
