# Reference Case: JailAI Project

## Overview
Investigation of Securus Technologies / JPay (Aventiv Technologies) correctional communications platform, identification of security gaps in their monitoring infrastructure, construction of an automated LLM-powered messaging POC, and a business proposal for selling AI threat detection back to Securus.

## Repo
https://github.com/pmb2/JailAI

## Workflow Applied (Session 1 — Platform Analysis + POC)

| Phase | Action | Key Details |
|-------|--------|-------------|
| Investigate | Curl marketing site, find real app | securustechnologies.com (Next.js) → securustech.online (Angular SPA) |
| Access | Login with credentials | Handled TOS v3.1 modal, dismissed chat widget |
| Map routes | Document SPA structure | #/my-account, #/products/emessage/inbox, compose, contacts |
| Identify gaps | No AI-based detection | Keyword-only monitoring, manual review of <1% traffic |
| Build POC | Python package | securus_bridge, llm_agent, safety_filter, message_pipeline |
| Write proposal | Security report | Gap analysis, solution architecture, market sizing, pricing, GTM |
| Package repo | GitHub | README, 3 docs, research sources, code, .env.example |
| Two-track | Product + Pitch | Track 1: JailAI automated comms. Track 2: Detection sell to Securus |

## Workflow Applied (Session 2 — API Reverse Engineering)

| Phase | Action | Key Details |
|-------|--------|-------------|
| API Capture | List network requests via CDP | 79+ requests captured from login through inbox navigation |
| Auth Mapping | Extract auth mechanism | JWT (idtoken) + tokenid + contactid triple-header auth |
| Endpoint Discovery | Examine each API call | 15+ endpoints mapped across ffws/ API base path |
| Headless SDK | Build Python API client | No browser needed — direct HTTP with JWT auth |
| Infrastructure | Read config/env.json | AWS AppSync, us-east-1, OPENID_CONNECT, ThreatMatrix |
| Documentation | Write api-reference.md | Full request/response formats for every endpoint |

## Key Technical Findings

### Platform Architecture
- Securus Online is an Angular SPA with in-memory auth tokens
- Page reload destroys the session; must navigate via SPA links
- Backend API base path: `/ffws/` on the same origin
- App version: 10.5.0, Angular Material Design

### Authentication System
- **Login:** `POST /ffws/api/user/authenticate/v2` with `{"pass":"...","loginUname":"..."}`
- **TOS Acceptance:** `POST /ffws/api/user/consent` with version, template, timestamp
- **Response headers include:** `idtoken` (JWT), `tokenid`, `contactid`, `tokenexpirationtimestamp`
- **All subsequent requests need:** `TokenId`, `ContactId`, `Authorization: Bearer <jwt>`, `X-DeviceId`
- **Session timeout:** ~30 minutes from `tokentimestamp`

### eMessaging API
| Endpoint | Purpose |
|----------|---------|
| `GET /ffws/services/eMessage/user/details/v2/{userId}` | Stamp balance, unread count |
| `GET /ffws/services/eMessage/messages/headers/{userId}/messageType/INBOX?count=10&page=1` | Inbox messages (paginated) |
| `GET /ffws/services/eMessage/inmate/{userId}?requestType=compose` | Inmate contacts for sending |
| `GET /ffws/services/eMessage/messages/draft/{userId}` | Draft messages |
| `POST /ffws/services/eMessage/messages/send` | Send message (needs stamps) |
| `GET /ffws/api/account/details/v1/{accountId}?accountType=EMESSAGE&relationShipId=1` | Account balance/status |

### Infrastructure (from config/env.json)
- **AWS AppSync GraphQL:** `https://appsync.messaging.securustech.net/graphql`
- **AWS Region:** `us-east-1`
- **Auth type:** OPENID_CONNECT (JWT)
- **File upload:** `https://file.dc.securustech.net`
- **UCL API (inmate lookup):** `https://api.dc.securustech.net`
- **Chat widget:** `https://cb.securustech.online/Amelia/ui/aventivClient/chat`
- **Anti-fraud:** ThreatMatrix / Thales via `https://valcontent.securustech.net/fp/tags.js`
- **Load balancers:** HAProxy (inthapxy, songinx)

### Key Identifiers (the operator's Account)
- contactId: 158190074
- eMessage accountId: 46730133
- Facility: NYS DOCCS Inmate Services
- Inmates: MANUEL QUEZADA (23B1811, Wallkill CF), MASON CZABAN (26R0846, Gouverneur CF)
- Stamp cost: $1.00/message, max message length: 20,000 chars
- 0 stamps available, 42 days inactive

### SPA Navigation Trick
- Angular stores auth in JavaScript memory only
- Full page reload (changing URL in address bar) DESTROYS session
- Solution: change only the hash fragment:
  ```javascript
  window.location.hash = '#/products/emessage/compose'
  ```
  This preserves in-memory auth state

## Demo Output

The safety filter demo (`python -m src.main --mode demo`) shows:
- Benign messages pass cleanly
- Escape planning blocked
- Contraband requests escalated  
- Coded language ("going fishing", "package") slips through regex but would be caught by LLM

This is the critical finding that proves the need for AI-based detection.

## Key Required Headers

Every authenticated request to the Securus API needs these headers:
```
TokenId: <tokenid from auth response>
ContactId: <contactId from auth response>
Authorization: Bearer <idtoken JWT>
X-DeviceId: <persistent UUID>
DeviceType: web
MobileAppVersion: 11.2.0.5
PrevPage: <current angular route>
```

## Business Model

- SaaS at $0.50-2.00/inmate/month
- FCC Oct 2025 ruling permits passing AI costs to end users
- Target: Aventiv/Securus as white-label or direct-to-DOC
- Revenue at 10% US penetration: $11M-45M/year

## Files Created

| File | Purpose |
|------|---------|
| `docs/platform-analysis.md` | Full tech stack analysis of Securus/JPay |
| `docs/security-report.md` | Business proposal for AI threat detection |
| `docs/architecture.md` | JailAI system architecture |
| `docs/api-reference.md` | Complete reverse-engineered API reference |
| `src/securus_bridge.py` | Browser automation layer |
| `src/api_client.py` | Headless API client (no browser needed) |
| `src/llm_agent.py` | LLM integration for message understanding |
| `src/safety_filter.py` | Multi-layer content safety screening |
| `src/message_pipeline.py` | Full orchestration pipeline |
| `src/main.py` | CLI entry point with demo mode |
