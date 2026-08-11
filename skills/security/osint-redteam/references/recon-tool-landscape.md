# Reconnaissance Tool Landscape & Build Patterns

**Source:** FOSS reconnaissance team research, May 2026
**Scope:** Comprehensive catalog of FOSS security tools for automated reconnaissance pipelines, gap analysis, and architectural patterns for building custom components.

---

## Tool Catalog by Category

### 1. Reconnaissance Automation Frameworks

| Tool | Stars | License | Lang | Last Push | API | Pipeline Notes |
|------|-------|---------|------|-----------|-----|----------------|
| **SpiderFoot** | 17,984 | MIT | Python | 2026-04 | ✅ REST API (HX) | Best all-in-one passive. 200+ modules, DB-backed, JSON output. Runs fully passive or active. |
| **Sn1per** | 10,043 | NOASSERTION | Shell | 2026-04 | ❌ CLI | Attack surface mgmt framework. Heavyweight — better standalone. |
| **ReconFTW** | 7,664 | MIT | Shell | 2026-05 | ❌ CLI | Single-command opinionated pipeline (subfinder→httpx→nuclei→gospider). |
| **Recon-ng** | 5,637 | GPL-3.0 | Python | 2024-11 | ✅ Python API | Modular framework, workspace management, 100+ modules. |
| **AutoRecon** | 6,001 | GPL-3.0 | Python | 2026-01 | ❌ CLI (config) | Multi-threaded network service enumeration. |
| **Legion** | 1,014 | MIT | Python | 2023-11 | ❌ GUI | Semi-automated Nmap→vuln scanning. GUI-only limits pipeline use. |
| **DataSploit** | 3,291 | GPL-3.0 | Python | 2025-11 | ❌ CLI | OSINT collection (email/domain/phone/social). |

### 2. Subdomain / Asset Discovery

| Tool | Stars | License | Lang | Last Push | Pipeline Notes |
|------|-------|---------|------|-----------|----------------|
| **Amass (OWASP)** | 14,636 | NOASSERTION | Go | 2026-04 | Passive+active, intel module for ASN→domain, graph DB backend |
| **Subfinder** | 13,744 | MIT | Go | 2026-05 | Fastest passive subdomain. 30+ sources, stdout pipe, JSON. |
| **Assetfinder** | 3,613 | MIT | Go | 2024-06 | Simple, pipe-friendly, stdout output. |
| **Findomain** | 3,748 | GPL-3.0 | Rust | 2026-05 | Rust, API-based, monitoring mode (`--watch`). |
| **Chaos Client** | 859 | MIT | Go | 2026-05 | ProjectDiscovery passive dataset. CDN/sonar sources. |

### 3. Technology Fingerprinting

| Tool | Stars | License | Lang | Last Push | Pipeline Notes |
|------|-------|---------|------|-----------|----------------|
| **httpx** | 9,987 | MIT | Go | 2026-05 | Swiss Army knife: probing + `-tech-detect` + screenshots + CDN. All JSON/stdout. |
| **WhatWeb** | 6,597 | GPL-2.0 | Ruby | 2026-04 | 1800+ plugins, aggressive/stealth modes, JSON output. |
| **Nuclei (tech templates)** | 28,945 | MIT | Go | 2026-05 | Tech-detection templates alongside vuln templates in same scan. |
| **wappalyzergo** | 1,043 | MIT | Go | 2026-05 | Go port of Wappalyzer logic. Embeddable as Go library. |

### 4. Vulnerability Correlation

| Tool | Stars | License | Lang | Last Push | Pipeline Notes |
|------|-------|---------|------|-----------|----------------|
| **Nuclei** | 28,945 | MIT | Go | 2026-05 | 8,500+ templates (CVE, misconfig, exposure, takeover). JS/DSL. |
| **OSV-Scanner** | 10,381 | Apache-2.0 | Go | 2026-05 | Passive CVE from dependency manifests. No NVD key needed. |
| **Trivy** | 35,246 | Apache-2.0 | Go | 2026-05 | Container/FS/repo/IaC scanning. SBOM generation (CycloneDX). |
| **Grype** | 12,309 | Apache-2.0 | Go | 2026-05 | Package-level CVE matching. Integrates with Syft for SBOM. |
| **searchsploit** | 7,854 | GPL-2.0 | Shell | (moved) | Offline ExploitDB search. GitLab: exploit-database/exploitdb. |
| **nvdlib** | 114 | MIT | Python | 2026-03 | Python wrapper for NVD CVE/CPE API. |

### 5. Attack Path / Planning

| Tool | Stars | License | Lang | Last Push | Pipeline Notes |
|------|-------|---------|------|-----------|----------------|
| **CALDERA** | 6,998 | Apache-2.0 | Python | 2026-05 | MITRE ATT&CK adversary emulation. REST API, plugins. |
| **BloodHound CE** | 3,071 | Apache-2.0 | Pwsh/C# | 2026-03 | AD attack path via Neo4j graph DB. SharpHound collectors. |
| **PentestGPT** | 13,367 | MIT | Python | 2026-05 | LLM-augmented guided pentesting. Conversational. |
| **HexStrike AI** | 9,004 | MIT | Node | — | 150+ security tools wrapped as MCP server. |
| **pentest-ai** | 560 | MIT | Python | — | 205 wrapped tools, 17 specialist agents, 60 SPA-aware probes. MCP+CLI. |
| **MCP Security Hub** | 559 | MIT | Node | — | Nmap, Ghidra, Nuclei, SQLMap, Hashcat via MCP. |

### 6. Stealth / Evasion

| Tool/Technique | License | Pipeline Integration |
|----------------|---------|---------------------|
| **ProxyChains-ng** | GPL-2.0 | Wrap any tool through Tor: `proxychains subfinder -d target` |
| **Tor** | BSD | SOCKS5 proxy for all egress traffic. |
| **Interlace** (by Codingo) | BSD | Task multiplexer with concurrency/rate control. |
| **Axiom** (by pry0cc) | MIT | Dynamic distributed infra — ephemeral VMs per scan. |
| **ExRecon** | MIT | TOR-routed Nmap automation with firewall evasion. |

### 7. Reporting & Vuln Management

| Tool | Stars | License | Lang | Last Push | Pipeline Notes |
|------|-------|---------|------|-----------|----------------|
| **Faraday** | 6,499 | GPL-3.0 | Python | 2026-05 | Vuln management. REST API + CLI, 80+ tool integrations. |
| **PwnDoc** | 2,823 | MIT | JS | 2026-05 | Pentest report generator. Template-based, REST API. |
| **PwnDoc-ng** | 454 | MIT | JS | 2025-10 | Fork of PwnDoc with renewed development. |
| **Dradis CE** | 807 | GPL-2.0 | Ruby | 2026-05 | Collaboration + evidence tracking + report templates. |

---

## Pipeline Architecture: How Tools Compose

```
PASSIVE PHASE (no target contact):
  Amass intel / Subfinder / Chaos / Assetfinder
       ↓ (subdomain list)
  httpx -tech-detect -status-code -title
       ↓ (live hosts + tech stack)
  WhatWeb / Nuclei tech-detect templates
       ↓ (fingerprinted targets)
┌──────────────────────────────────────────────────────────────┐
│ DECISION POINT: Branch based on passive findings              │
├──────────────────────────────────────────────────────────────┤
│ STAY PASSIVE:                                                 │
│   OSV-Scanner (dependency scanning)                           │
│   Trivy/Grype (if container images/repos found)              │
│   → Store in knowledge graph for correlation                  │
│                                                               │
│ GO ACTIVE (stealth mode):                                     │
│   slow-roll-proxy → nmap -T1 (extreme rate limit)            │
│   slow-roll-proxy → gobuster/ffuf (throttled jitter)         │
│   slow-roll-proxy → httpx/nuclei (limited probe set)          │
│   → Validate through minimal confirmatory probes              │
└──────────────────────────────────────────────────────────────┘
       ↓
VULNERABILITY CORRELATION:
  tech-to-cve → NVD API + OSV.dev + ExploitDB + Nuclei tmpl
       ↓ (scored CVEs by confidence)
KNOWLEDGE GRAPH:
  PostgreSQL/Neo4j: services → CPEs → CVEs → exploits → paths
       ↓
ATTACK PLANNING:
  BloodHound (if AD) / CALDERA / custom attack path queries
       ↓
REPORTING:
  Faraday (vuln mgmt) / PwnDoc (report generation)
```

---

## Critical Gaps in the FOSS Ecosystem

### GAP A: Slow-Roll / Organic Traffic Proxy
**No FOSS tool implements organic-traffic recon as a first-class feature.**

What's missing is a proxy that sits between any recon tool and the target and adds:
- Gaussian jitter (μ=15s, σ=5s configurable) between requests
- Real browser User-Agent rotation (rotated from a real user agents database)
- Non-empty Referer chain that mimics actual browsing history
- Session persistence (cookie jar, keep-alive across a session)
- Tor / SOCKS5 proxy rotation with configurable circuit lifetime
- Exponential rate decay (N/min → N/2 → N/4 over windows)
- Piped stdin/stdout mode for wrapping any tool

**Closest things**: ExRecon (21★, Nmap-only), Interlace (concurrency control only). Everything else optimizes for speed.

### GAP B: General Service→CPE→CVE Correlator
**No production-grade FOSS tool provides general-purpose version-to-CVE matching.**

What's missing is a tool that:
- Takes any list of `{tech_name, version_string}` from httpx/WhatWeb/SpiderFoot
- Generates CPE 2.3 URIs from version strings (e.g., `nginx 1.24.0` → `cpe:2.3:a:nginx:nginx:1.24.0:*...`)
- Queries NVD API + OSV.dev API for matching CVEs (rate-limited)
- Compares versions semantically (>=, <, ranges, affected)
- Cross-references ExploitDB, Nuclei template database for exploit availability
- Assigns confidence scores (0.0–1.0) based on match precision

**Closest things**: WPScan (WP-only), Retire.js (JS-only), nvdlib (low-level wrapper only).

### GAP C: Infrastructure Knowledge Graph
**No production-grade FOSS project provides a general infra knowledge graph for recon data.**

What's missing is:
- Schema for domains → hosts → services → technologies → CVEs → attack paths
- Auto-ingestion from SpiderFoot JSON, httpx JSON, Nmap XML, Nuclei JSON
- Graph traversal queries for attack path analysis
- PostgreSQL (JSONB) or Neo4j backend
- Change detection across scan cycles

**Closest things**: BloodHound CE (AD-only), Recon-ng (flat files). KuzuDB is archived.

### GAP D: AI Orchestration Layer
**No FOSS project combines LLM orchestration with persistent recon state, slow-roll scanning, CVE correlation, and scheduling in one pipeline.**

---

## Build Patterns for Custom Components

### Pattern: Hermes Agent as Recon Orchestrator

Hermes Agent excels as the brain because of:
- **delegate_task** — Spin up parallel sub-agents for Phase 1 (passive), Phase 2 (active), Phase 3 (CVE match), Phase 4 (planning). Each runs independently in an isolated terminal session.
- **cronjob** — Schedule recurring passive recon sweeps. Daily: SpiderFoot passive scan. Weekly: diff against previous results.
- **skill system** — Package each phase as a reusable skill. Skills load tool configs, install deps, and follow a documented procedure.
- **MCP client** — Wire recon tools as MCP servers (HexStrike, pentest-ai, custom tools).

### Pattern: Slow-Roll Proxy in Python

```python
# Pseudo-architecture for a slow-roll stdin→stdout proxy
class SlowRollProxy:
    def __init__(self, config):
        self.jitter = GaussianTiming(config.mean, config.stddev)
        self.ua_pool = RealUserAgentDB()
        self.proxy_pool = ProxyRotator(config.proxy_chain)
        self.session_store = CookieJar()
        self.rate_limiter = DecayingRateLimiter(config.start_rate, config.decay)
    
    def wrap_http_request(self, method, url, headers=None, data=None):
        """Sit between tool and target, apply stealth transforms."""
        # 1. Apply jitter delay (Gaussian)
        time.sleep(self.jitter.next_delay())
        
        # 2. Rotate User-Agent and add referer chain
        headers['User-Agent'] = self.ua_pool.random()
        headers['Referer'] = self.referer_chain.next()
        
        # 3. Apply rate limit (may sleep more)
        self.rate_limiter.wait_if_needed()
        
        # 4. Route through proxy
        proxy = self.proxy_pool.next_circuit()
        
        # 5. Maintain session cookie jar
        session = self.session_store.get_or_create(proxy)
        
        return requests.request(method, url, headers=headers, 
                                cookies=session.cookies, proxies=proxy)
```

### Pattern: Tech→CVE Correlation

```python
# Core CVE correlation flow
cpe_ecosystem_map = {
    'nginx': 'Packagist', 'php': 'Packagist', 'python': 'PyPI',
    'node': 'npm', 'jquery': 'npm', 'react': 'npm',
    'openssh': 'cpe', 'apache httpd': 'cpe', 'mysql': 'cpe',
}

def correlate_tech_to_cve(tech_name, version, confidence=0.5):
    # 1. Map to CPE or ecosystem
    ecosystem = cpe_ecosystem_map.get(tech_name.lower(), 'cpe')
    
    if ecosystem == 'cpe':
        cpe = f"cpe:2.3:a:{tech_name}:{version}"
        return query_nvd_by_cpe(cpe, confidence)
    else:
        return query_osv_by_ecosystem(ecosystem, tech_name, version)
```

---

## License Compatibility Notes

| License | Permissive? | Can bundle with MIT? | Notes |
|---------|------------|---------------------|-------|
| **MIT** | ✅ | ✅ Yes | Most permissive. SpiderFoot, Subfinder, httpx, Nuclei, Chaos, PwnDoc |
| **Apache-2.0** | ✅ | ✅ Yes | OSV-Scanner, Trivy, Grype, CALDERA, BloodHound CE |
| **GPL-2.0** | ⚠️ | ❌ No (viral) | WhatWeb, Faraday — must keep separate distribution |
| **GPL-3.0** | ⚠️ | ❌ No (viral) | Recon-ng, AutoRecon, DataSploit, Findomain — separate container |
| **BSD** | ✅ | ✅ Yes | Nmap, Metasploit |

GPL tools can still be used in a pipeline — they just can't be linked into the same binary/distribution. Container-based isolation (Docker Compose services) avoids license contamination.

---

## Key Takeaways

1. **ProjectDiscovery stack dominates** — Subfinder → httpx → Nuclei is the backbone. All MIT, Go binaries, pipe-friendly JSON.
2. **SpiderFoot is the best passive orchestrator** — 200+ modules, REST API, DB-backed. The only "big picture" tool.
3. **Faraday + PwnDoc cover reporting** — Faraday for vuln management, PwnDoc for human-readable reports.
4. **Critical gaps exist** — No FOSS tool provides organic slow-roll proxying, general CPE-to-CVE correlation, or infrastructure knowledge graphs.
5. **Hermes Agent is the ideal orchestrator** — delegate_task for parallel phase execution, cron for scheduling, skills for packaging, MCP for tool integration.
