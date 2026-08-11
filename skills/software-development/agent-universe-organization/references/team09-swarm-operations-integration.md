# Team 09 — Swarm Operations Integration Record

## Source
The ShadowForge Swarm framework at `teams/04-fraud-operations/new/` (428 files, 12 categories).

## Destination Teams & Agents Created (14 total)

### Team 02 — Offensive Security (8 new agents)
| Agent | Source Module | Python Files | Role |
|-------|-------------|--------------|------|
| red-c2-framework | c2/ | 13 | Multi-protocol C2 (HTTP, DNS, SMB, WebSocket), listener manager, profile manager, web UI |
| red-evasion | evasion/ | 8 | AMSI/ETW bypass, sandbox detection, TLS/JA3 spoofing, browser fingerprint, cipher profiles |
| red-exploit | exploit/ | 7 | CVE matching, credential attacks, hashcat rules, scanner integration |
| red-lateral-movement | lateral/ | 5 | WinRM, SSH pivot, pass-the-hash, movement automation |
| red-payload | payload/ | 8 | AMSI/ETW payloads, DLL gen, encryption, packing, polymorphic code, VBA macros |
| red-persistence | persistence/ | 6 | Bootkit simulation, COM hijack, kernel modules, PAM backdoor |
| red-phish-advanced | phishing/ | 6 | Campaign management, email engine, landing page server, template library |
| red-engagement | engagement/ | 5 | Operations manager, finding templates, integrations, report generator |

### Team 09 — Swarm Operations (6 new agents)
| Agent | Source Design Docs | Role |
|-------|-------------------|------|
| swarm-orchestrator | 01-EXECUTIVE-CREW/ | Executive crew — orchestrator + legal-political intelligence |
| swarm-production | 02-PRODUCTION-CREW/ | Identity lifecycle — procurement, generation, nurturing |
| swarm-financial | 03-FINANCIAL-CREW/ | Proceeds orchestration — Monero, CoinJoin, P2P |
| swarm-infrastructure | 04-SECURITY-INFRASTRUCTURE-CREW/ | Network ops — comms, worming, monitoring, switchboarding |
| swarm-evolution | 05-EVOLUTION-RESEARCH-CREW/ | R&D — self-improvement, capability evolution |
| swarm-opsec | 00-OPERATOR-FORTRESS/ | OPSEC — physical/legal/financial isolation |

## Build Matrix Verdict Summary

| Category | ✅ Build | ⚠️ Reframe | ❌ Won't Build | Total |
|----------|---------|------------|---------------|-------|
| MCP Servers | 0 | 5 | 7 | 12 |
| Skills | 0 | 3 | 11 | 14 |
| Tools | 5 | 11 | 4 | 20 |
| Frameworks | 6 | 0 | 0 | 6 |
| Infrastructure | 4 | 2 | 0 | 6 |
| Architecture Docs | 1 | 4 | 1 | 6 |
| **Core** | **0** | **3** | **10** | **13** |
| **Total** | **16** | **28** | **36** | **80** |

## Common Integration Pitfalls
- Agents placed under `agents/` subdirectory instead of team root (fix: `mv`)
- `__pycache__` dirs and `.pyc` files copied into tooling (already gitignored)
- `src.swarm.base` import paths don't resolve in new location (need package stubs)
- Multiple subagents writing the same INDEX.md or AGENT_UNIVERSE.md (assign one)
