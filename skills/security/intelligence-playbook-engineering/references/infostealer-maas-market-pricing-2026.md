# Infostealer MaaS Market: Pricing, Economics & Log Supply Chain (2026)

**Source:** Cross-referenced threat intelligence (ransomnews.com, KELA, Flare.io, SOCRadar, Microsoft Threat Intelligence, Kaspersky, Dutch National Police)  
**Date:** June 2026  
**TTP Classification:** TA0006 (Credential Access) → T1588.002 (Obtain Capabilities: Malware-as-a-Service) → T1071.001 (C2: Web) → T1539 (Steal Web Session Cookie)

## Overview

The infostealer market operates as a mature Malware-as-a-Service (MaaS) economy. A small number of developer teams build and maintain the malware binary, sell subscription access to operators, and keep the subscription revenue. Operators distribute the malware, keep all logs they harvest, and sell those logs through Telegram channels and underground forums. Brokers buy logs in bulk, filter for high-value credentials, and resell to ransomware affiliates and initial access brokers.

This reference documents the current pricing, providers, and supply chain economics as of June 2026.

---

## MaaS Provider Pricing (2026)

Prices are monthly subscriptions paid in cryptocurrency (typically Bitcoin, Monero, or TON). Operators pay the subscription, keep all logs collected.

| Provider | Monthly Cost | Tiers | Origin | Notes |
|----------|-------------|-------|--------|-------|
| **Lumma Stealer** (LummaC2) | $250 - $1,000/mo | "Experienced" $250, "Corporate" $1,000 | Russian (dev handle "Shamel") | Market leader. Corp tier = more frequent builds + better evasion. |
| **RedLine Stealer** | $100 - $200/mo | Single tier (now fractured) | Russian ("REDGlade") | Former #1. Crippled by Operation Magnus (Oct 2024). Cracked/forks still circulate. |
| **Raccoon Stealer v2** | $200 - $275/mo | Single tier | Russian | Rust-based. Focuses on MFA-bypass session cookies over saved passwords. |
| **Vidar** | ~$200/mo | Single tier | Russian | Fork of Arkei. Active since 2018. Extremely resilient, continuous updates. |
| **Stealc** | ~$150 - $200/mo | Modular per-build | Russian | Newer entrant (2023). Gaining share by undercutting prices. Modular architecture. |
| **Atomic (AMOS) — macOS** | $1,000 - $3,000/mo | Single tier | Unknown | macOS market leader. Targets Keychain + browser creds. Sold on Telegram. |
| **Cthulhu — macOS** | ~$1,000/mo | Single tier | Unknown | Newer macOS entrant (mid-2024). |
| **MetaStealer — macOS** | ~$1,000/mo | Single tier | Unknown | Still active despite Operation Magnus impact on Windows-side MetaStealer. |

**Industry average (KELA, 2025):** ~$200/mo per subscription. Barrier to becoming an operator.

### Secondary/Tier-2 Families

Smaller families with limited market share but stable operations:

| Provider | Notes |
|----------|-------|
| **DCRat / DarkCrystal RAT** | Russian-language. Combines stealer + remote-access tool functionality. |
| **Aurora Stealer** | Go-based. Smaller operation. |
| **Mystic Stealer** | Active since 2023. |
| **Pure Logs / PureRAT** | Newer, gaining attention. |

---

## The Three-Layer Pyramid

The ecosystem separates three distinct roles with cleanly divided risk and reward:

### Layer 1: The Developers
- Write and maintain the malware binary
- Handle C2 infrastructure (panels, Telegram bot exfiltration, domain rotation)
- Sell subscriptions — that's their revenue. They **don't touch the logs**
- Revenue: $200-1,000/mo per subscriber × dozens to hundreds of subscribers

### Layer 2: The Operators (Subscribers)
- Pay the monthly subscription
- Distribute the malware through crack sites, YouTube tutorials, fake game cheats, SEO-poisoned downloads, malicious PyPI/npm packages
- **Keep all the logs they collect**
- Revenue: Whatever the logs sell for (can be $50k-100k/mo for successful operators)

### Layer 3: The Brokers & Resellers
- Buy raw logs in bulk from operators
- Filter and re-sell to specialized buyers (ransomware affiliates, access brokers, APT groups)
- Add value through sorting: "random consumer log" = pennies; "US East Coast employee at Fortune 500 with active Okta session and VPN cookie" = hundreds

---

## Log Market Pricing

Pricing is **not per-log** in the traditional sense — it's value-based, determined by what the log contains:

| Log Type | Price | Description |
|----------|-------|-------------|
| **Bulk/indiscriminate** | $5-15 per log | Random consumer credentials, no filtering |
| **Bulk pack (100+ logs)** | $0.50-3 per log | Discounted volume, unfiltered |
| **VIP/Filtered** | $50-500+ per log | Has corporate VPN, M365 session, Okta cookie, or high-value crypto wallet |
| **Corporate access** | $500-5,000+ | Verified working credentials for a specific company — sold to ransomware affiliates as "access" not "log" |
| **Telegram auto-shop channel sub** | $10-50/mo | Drip feed of fresh logs as they're captured, gated behind monthly subscription |

### How Pricing Works in Practice

The Telegram channels are the dominant distribution method. An operator runs a channel that auto-posts logs in real-time. The channel has:
- **Free preview tier**: Shows a few lines of each log (hostname, date, sometimes partial URL)
- **Paid tier**: Unlocks the full credential dump, cookies, and session data

A reseller buys 1,000 raw logs for $500 bulk ($0.50 each). They run an automated filter that identifies:
- Logs containing corporate VPN cookies
- Logs with active Okta/AzureAD sessions
- Logs with crypto wallet seed phrases
- Logs with banking session cookies (BofA, Chase, WF)

The filtered logs are sold to specialized buyers at 10-100x markup.

---

## The Money Flow (Illustrative Example)

```
Operator pays $200/mo for Lumma subscription
  ↓
Distributes via cracked Adobe installer on YouTube tutorial
  ↓
1,000 machines infected → 1,000 logs generated (1-5 MB each, ~3 GB total)
  ↓
Dumps logs to Telegram auto-shop channel
  ↓
Reseller buys 1,000 logs for $500 bulk ($0.50 each)
  ↓
Automated filter finds 30 logs with corporate credentials
  ↓
Sells those 30 filtered logs to an access broker for $3,000 ($100 each)
  ↓
Access broker verifies access works, resells 1 verified corporate entry point
  ↓
Ransomware affiliate buys the access for $10,000 → deploys ransomware
```

The same $200/mo subscription can generate $50,000-100,000/mo in log sales for a successful operator. The developer gets the subscription revenue. The operator keeps the rest.

---

## Infection Vectors (How Operators Distribute)

The dominant infection vectors, ranked by volume:

| Vector | Share | Notes |
|--------|-------|-------|
| **Cracked software downloads** | ~40% | Fake KMS activators, "free" Adobe/AutoCAD/IDM via SEO-poisoned blog posts and YouTube tutorials |
| **Fake game cheats and mods** | ~20% | Gaming-focused machines that often share networks or accounts with corporate use |
| **Phishing with malicious attachments** | ~20% | OneNote, ISO, LNK, MSI loaders dropping the stealer payload |
| **Malicious PyPI/npm packages** | ~10% | Typosquats and supply-chain attacks targeting developers |
| **Drive-by downloads/compromised ad networks** | ~10% | Less common in 2025-2026 but active |

**Crucial fact:** Most infections happen on **personal devices**, not corporate-managed endpoints. The victim is at home using their personal laptop, and the credentials being stolen include their corporate VPN, M365 session, GitHub PAT, and banking logins.

---

## Log Contents (What's Inside a Single Log)

A single stealer log (1-5 MB compressed) contains:

| Item | Typical Count | Value |
|------|--------------|-------|
| Browser-saved passwords | 30-300 entries | Medium — allows credential stuffing |
| Browser cookies (authenticated sessions) | 50-500 entries | **High** — session replay bypasses MFA |
| Autofill data | 10-100 entries | Medium — PII for social engineering |
| Crypto wallet files/seed phrases | 0-5 entries | **Very High** — direct asset theft |
| System info | Once | Hostname, username, OS, IP, geolocation, desktop screenshot |
| FTP/SSH client configs | 0-10 entries | Medium-High — server access |
| Messaging tokens (Telegram, Discord, Steam) | 3-10 entries | High — account takeover |

---

## Where Logs Are Sold

| Marketplace | Type | Access | Notes |
|-------------|------|--------|-------|
| **Telegram channels** | Auto-shop | Invite-only, private channels | Dominant. Auto-posting bots. Free preview + paid unlock. |
| **Russian Market** | Web marketplace | Registration | Largest post-Genesis Market successor. |
| **XSS (.pw)** | Forum | Registration | Russian-language, established escrow system. |
| **Exploit(.in)** | Forum | Registration | Russian-language. |
| **Verified** | Forum | Registration | Hosts bulk-log marketplaces. |

---

## Takedown Effectiveness

| Operation | Target | Date | Effect | Recovery |
|-----------|--------|------|--------|----------|
| **Operation Magnus** | RedLine + MetaStealer | Oct 2024 | Seized infrastructure, published source code, indicted 3 operators. Broke RedLine's market dominance. | Fragmented/cracked variants still circulate. Market share shifted to Lumma. |
| **Microsoft + LE** | Lumma infrastructure | May 2024 | Seized ~2,300 domains. | Operation continued with regenerated infrastructure within weeks. |

Takedowns shift market share to the next family in line but rarely eliminate a family permanently — the source code is published, the developers have the skills, and the market demand is undiminished.

---

## Key Systemic Facts

1. **Volume is enormous** — Industry estimates: several million fresh logs enter the market globally per week.
2. **Most logs are low-value** — Consumer credentials dominate. The small fraction containing corporate access powers most modern ransomware breaches.
3. **Cookie replay bypasses MFA** — A session cookie stolen from a logged-in browser is already authenticated. Replay it, and you're inside without touching the login flow. Phishing-resistant MFA only protects against fresh login attempts, not active session replay.
4. **Personal device compromise = corporate device compromise** — Employees using home laptops to access corporate SaaS means corporate credentials appear in consumer stealer logs. Endpoint security never sees it.
5. **Detection lags exploitation by hours/days, not months** — From market entry to active exploitation is now hours to a few days. Monitoring services (Hudson Rock, SpyCloud, IntelX, NordStellar) exist to close this window.

---

## Source Reliability

| Source | Type | Reliability | Key Coverage |
|--------|------|-------------|--------------|
| ransomnews.com | Threat intel journalism | High | Complete MaaS pricing table, log market structure, session cookie value chain |
| KELA (Cybercrime Intelligence) | Commercial threat intel | High | Average MaaS pricing ($200/mo), log market analysis |
| Flare.io | Commercial threat intel | High | Stealer log market analysis, enterprise exposure monitoring |
| SOCRadar | Vendor research | Medium-High | Infostealer landscape, log content breakdown |
| Microsoft Threat Intelligence | Vendor/LE | High | Lumma infrastructure analysis and takedown |
| Dutch National Police (Operation Magnus) | Law enforcement | High | RedLine takedown, customer list publication |
| Kaspersky Securelist | Vendor research | High | macOS infostealer mechanics, DNS-based delivery |
