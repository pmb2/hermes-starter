# Infostealer MaaS Economy — Landscape Reference

> Research date: 2026-06-04
> Sources: Ransomnews Research (ransomnews.com), DuckDuckGo cross-referencing of threat intel publications (KELA 2025, Sekoia, Saptang Labs, NetGuardia, Mjolnir Security, Cyber Desserts, PI Solutions, algeriatech.news)

## MaaS Provider Pricing (2026)

Every major family runs as Malware-as-a-Service (MaaS). Dev team builds the binary and sells subscriptions to "operators" who do the infecting. Operators keep the logs.

| Provider | Monthly Cost | Tier Structure | Origin | Signature Feature |
|----------|------------|----------------|--------|-------------------|
| **Lumma Stealer** (LummaC2) | $250 - $1,000/mo | "Experienced" $250, "Corporate" $1,000 | Russian dev "Shamel" | Market leader. Anti-VM/Wireshark detection, 80+ browsers, 70+ crypto wallets, Cloudflare C2 rotation. Microsoft takedown May 2024 (2,300 domains seized) — rebuilt within weeks. |
| **RedLine Stealer** | $100 - $200/mo | Single tier (now fractured) | Russian dev "REDGlade" | Former #1 (51% of all infections 2020-2024). Hit by **Operation Magnus** Oct 2024 (Dutch Police + FBI seized infra, published source code & customer lists, 3 operators indicted, 1 arrested in Spain). Still circulating via cracked/forks. |
| **Raccoon v2** | $200 - $275/mo | Single tier | Rust-based rewrite | Specialises in MFA-bypass session cookies over saved passwords. Returned 2022 after dev arrested in Netherlands. |
| **Vidar** | ~$200/mo | Single tier | Fork of Arkei (2018) | Extremely resilient — continuous updates since 2018. Notable: legitimate cloud platforms for C2 (Telegram, GitHub, Steam profiles). |
| **Stealc** | ~$150-200/mo | Modular per-build | Russian, first seen 2023 | Gaining share by undercutting Lumma/RedLine. Modular architecture, unusually well-documented internally. |
| **Atomic (AMOS) — macOS** | $1,000 - $3,000/mo | Single tier | macOS-specific | Largest macOS infostealer. Targets Keychain + browser creds + crypto wallets. Sold on Telegram. |
| **Cthulhu — macOS** | ~$1,000/mo | Single tier | macOS-specific | Emerged mid-2024. Same target pool as AMOS. |

**Average across all providers:** ~$200/mo to be an operator.

## The Three-Layer Supply Chain

### Layer 1: Developers
- Write and maintain the binary, handle C2 infrastructure
- Revenue: subscriptions only — they **never touch the logs**
- Payout: $200-1,000/mo/subscriber × N subscribers

### Layer 2: Operators (subscribers)
- Pay the monthly subscription
- Distribute via: crack sites, YouTube tutorials, fake game cheats, SEO-poisoned downloads, malicious PyPI/npm packages, phishing with OneNote/ISO/LNK/MSI loaders
- **Keep all the logs** — profit determined by log market value minus subscription cost

### Layer 3: Brokers & Resellers
- Buy raw logs in bulk from operators (or scrape Telegram auto-shops)
- Filter and re-sell to specialized buyers (ransomware affiliates, initial access brokers, APT groups)
- Value-add: filtering — a random consumer log is worth pennies; the same log filtered as "US East Coast employee at Fortune 500 with active Okta session and VPN cookie" is worth hundreds

## Log Pricing Tiers

Not per-log pricing in the traditional sense. Value depends entirely on what's in the log.

| Log Type | Price | What's Inside |
|----------|-------|--------------|
| **Bulk/indiscriminate** | $5-15 per log | Random consumer credentials, no filtering |
| **Bulk pack (100+ logs)** | $0.50-3 per log | Volume discount, unfiltered. Sold through Telegram auto-shop subscription feeds ($10-50/mo) |
| **VIP/Filtered** | $50-500+ per log | Contains corporate VPN, M365 session, Okta cookie, or high-value crypto wallet |
| **Corporate access** | $500-5,000+ (sold as "access," not "log") | Verified working credentials for a specific company → sold to ransomware affiliates |
| **Telegram "auto-shop" subscription** | $10-50/mo | Drip feed of fresh logs as they're captured, gated behind monthly access |

**What's in a single log** (1-5 MB compressed ZIP):
- Browser-saved passwords (decrypted from DPAPI/Keychain — typically 30-300 entries)
- Authenticated session cookies (MFA-bypass material — SaaS, banks, corporate VPNs)
- Autofill data (names, addresses, card info)
- Crypto wallet seed phrases (MetaMask, Phantom, Exodus — ~2-5% of logs have these)
- System info (hostname, IP, geolocation, desktop screenshot)
- FTP/SSH client creds (FileZilla, WinSCP, OpenSSH)
- Telegram/Discord/Steam session tokens

## Money Flow Example

```
Operator pays $200/mo for Lumma subscription
  ↓
Distributes via cracked Adobe installer on YouTube tutorial
  ↓
1,000 machines infected → 1,000 logs (~3GB)
  ↓
Operator dumps logs to Telegram auto-shop channel
  ↓
Reseller buys 1,000 logs for $500 bulk ($0.50 each)
  ↓
Automated filter → finds 30 logs with corporate credentials
  ↓
Sells 30 filtered logs to access broker for $3,000 ($100 each)
  ↓
Access broker verifies access, resells 1 verified corporate entry point
  ↓
Ransomware affiliate buys access for $10,000 → deploys ransomware
```

**Result:** A $200/mo subscription can generate $50,000-100,000/mo in log sales for a successful operator.

## Where Logs Are Sold

| Platform | Type | Access |
|----------|------|--------|
| **Telegram channels** | Dominant distribution | Private channels + invite-only public channels. Auto-posting bots. "Russianmarket" is the largest post-Genesis Market successor. |
| **Russian forums** | Established marketplaces | XSS (.pw), Exploit(.in), Verified — host bulk-log marketplaces |
| **Specialized resellers** | Brokered deals | Buy bulk → filter → resell to ransomware affiliates and initial access brokers |

## Key Statistics

- **3.9 billion credentials** stolen from **4.3 million devices** in 2024 alone (KELA/algeriatech.news data)
- **~$200/mo** is the average MaaS subscription cost (KELA 2025)
- **Several million** fresh logs enter the market per week globally
- **75%+** of enterprise credential exposure comes from three families: Lumma, RedLine, Vidar
- **~2-5%** of logs contain crypto wallet seed phrases
- **~Hours to days** from log publication to active exploitation (ransomware affiliates monitor feeds continuously)
- **Session cookies bypass MFA** — the authenticated cookie is already past the login flow. Short session lifetimes and continuous re-authentication are the only defenses.
- **Most infections happen on personal devices**, not corporate-managed endpoints. The victim logs into work SaaS from their home laptop, and the stealer captures both.

## Law Enforcement Actions

| Operation | Date | Target | Impact |
|-----------|------|--------|--------|
| Operation Magnus | Oct 2024 | RedLine + MetaStealer | Infrastructure seized, source code published, customer lists leaked, 3 indicted, 1 arrested in Spain. RedLine market share destroyed but cracked forks persist. |
| Microsoft takedown | May 2024 | Lumma | ~2,300 domains seized. Lumma regenerated infrastructure within weeks and returned as market leader. |

**Lesson:** Takedowns shift market share temporarily. Lumma displaced RedLine after Operation Magnus. Within weeks of any takedown, the next family absorbs the volume.

## Fragment.com / Anonymous Telegram Numbers

> Full research from 2026-06-04. Fragment is secondary-market only.

- **All 136,566 numbers sold out** in the original mint (December 2022) at ~10 TON each (~$5-15)
- **No new numbers will ever be minted** — supply is strictly finite
- **Secondary market floor: ~1,684 TON (~$2,860)** as of June 2026
- **Cheapest auction buy-it-now:** ~1,684 TON on fixed-price listings; auctions end around 1,800 TON+
- The market behaves like domain name speculation — vanity patterns (repeating digits, low digit counts, 888 prefixes) trade at 2-10x floor
- **Practical alternative to Fragment for anonymous Telegram:** SMS activation services (sms-activate.org, 5sim.net) at $0.50-3 per verification with Monero, or prepaid SIM bought with cash ($5-15 one-time for a permanent number you can recover)

## Cross-References

- `osint-threat` — Operational threat intelligence for IOC analysis (this skill)
- `intelligence-pulse` — The pulse system that checks for new intelligence items
- `daily-pulsar-summarizer` — AFK summarization and unseen backlog management
