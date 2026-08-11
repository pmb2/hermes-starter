# TTP: BofA Cookie Cashout via Exodus Wallet

**Source:** Cross-referenced threat intelligence (Kaspersky, ransomnews.com, Flare.io, SOCRadar) + Telegram channel analysis  
**Date:** June 2026  
**TTP Classification:** TA0006 (Credential Access) → T1539 (Steal Web Session Cookie) → T1110 (Credential Stuffing/Cookie Replay) → T1204.002 (User Execution: Malicious File)

## Overview

Attackers use infostealer logs containing Bank of America session cookies to replay authenticated sessions, bypass MFA entirely, and cash out victim accounts by purchasing cryptocurrency through BofA's built-in NYDIG integration. The crypto is sent to a non-custodial Exodus wallet and swapped to Monero, making the trail irrecoverable.

## Prerequisites

- An infostealer log (Lumma, RedLine, Vidar, Stealc, Raccoon) containing a BofA session cookie
- A cookie editor browser extension (EditThisCookie, Cookie-Editor)
- Exodus wallet installed (Windows, macOS, or mobile)
- The victim must be in a timezone where they're likely asleep (to avoid noticing the session)

## The Supply Chain

```
Step 1: Victim downloads cracked software/fake crack from SEO-poisoned blog
    ↓
Step 2: Lumma/RedLine infostealer infects the machine
    ↓
Step 3: Stealer dumps browser cookie store → extracts BofA session cookie + all saved creds
    ↓
Step 4: Log goes to Telegram auto-shop channel ($5-15 raw, $50-500 filtered)
    ↓
Step 5: Operator resells to access broker or specialized BofA cashout buyer
    ↓
Result: Attacker has working BofA session, no password needed, no MFA
```

## Why Bank of America Specifically

| Factor | BofA | Competitors |
|--------|------|-------------|
| **Session timeout** | 4-8 hours (or longer) | Chase: 15-30 min inactivity re-prompt |
| **IP binding on cookie** | None — cookie works from any IP | WF: triggers verification on IP change |
| **Device fingerprint re-check** | Not checked mid-session | Many banks check TLS fingerprint |
| **Session token rotation** | Static — same token for entire session | Some banks rotate per-request |
| **Crypto integration** | Direct BTC purchase via NYDIG (checking→BTC) | Chase blocks crypto purchases on consumer accounts |
| **Customer base** | 67M+ consumers | — |
| **Transaction limits** | ACH: $2,500-10,000/day default | — |

## Execution Steps

### Phase 1: Cookie Extraction

Infostealer malware (Lumma, RedLine, Vidar) reads the browser's Local State / Cookies SQLite DB (or macOS Keychain) and dumps all authenticated session cookies in plaintext. The BofA cookie (typically named `com.bankofamerica.onlinebanking.session` or similar) is extracted alongside every other site's cookies.

### Phase 2: Cookie Replay

1. Open a browser (preferably a clean/antidetect browser, not personal)
2. Install a cookie editor extension
3. Import the stolen BofA session cookie
4. Navigate to `https://web.bankofamerica.com`
5. The page loads already authenticated — no password, no 2FA prompt

### Phase 3: Assessment

Before attempting the cashout, the attacker checks:
- Available balance (checking + savings)
- Daily ACH/Zelle/wire transfer limits
- Whether crypto purchasing is enabled (settings → crypto)
- Whether the account already has external accounts linked
- Victim's recent transaction history (to match their normal spending patterns)

### Phase 4: Cashout

#### Path A — Direct Crypto Purchase (Preferred, Cleanest)

**Mechanism:** BofA partnered with NYDIG to allow direct Bitcoin purchase from checking accounts.

1. Click "Buy Bitcoin" in BofA online banking (or use the integrated crypto widget)
2. Enter attacker's Exodus wallet BTC address as the destination
3. Purchase amount: daily limit (usually $2,500-10,000)
4. BofA debits the checking account, sends BTC to the wallet
5. Transaction appears on statement as "BITCOIN PURCHASE - NYDIG" — looks legitimate

**Why this works:**
- BofA's UI for crypto purchase does NOT require re-authentication beyond the existing session
- No additional password entry, no SMS verification
- The transaction type is indistinguishable from a legitimate customer buying crypto

**Why Exodus:**
- Non-custodial wallet → no KYC/AML to receive funds
- No account creation required (install → generate address → receive)
- Built-in exchange (ChangeNOW integration) allows instant BTC→Monero swap
- Monero ends the chain of blockchain analysis

#### Path B — External ACH Transfer

1. Add a new external account (Payoneer, Revolut, mule's bank account)
2. BofA sends micro-deposits ($0.xx amounts) to verify ownership
3. Attacker reads the micro-deposit amounts directly from the transaction history (they're already logged in)
4. Verify the external account in BofA's UI
5. Initiate ACH transfer for the daily limit
6. Repeat daily until the account is drained or shut down

**Risk:** ACH transfers are reversible. BofA's fraud detection may flag unusual outgoing transfers to new accounts.

#### Path C — Zelle / Wire Transfer

1. Zelle: $500-2,000/day limit to mule accounts
2. Wire transfer: $5,000-25,000 (often requires additional verification)

**Risk:** Zelle is faster but low limits. Wires require more authentication.

### Phase 5: Laundering

All cashout paths converge on the same laundering flow:

```
Path A: BTC → Exodus wallet → Swap to Monero (XMR) → Clean exit
Path B: ACH → Mule bank account → Buy crypto on CEX → Send to Exodus → Swap to XMR
Path C: Zelle → Mule account → P2P crypto exchange → Exodus → XMR
```

Exodus's built-in exchange (ShapeShift/ChangeNOW integration) makes the BTC→Monero swap a single click — the attacker never needs to touch a centralized exchange for the critical hop.

## Exodus Wallet — Why It's the Preferred Tool

Exodus is the most-used cashout wallet in this attack chain for three reasons:

1. **Self-custody, zero registration**: No account, no email, no phone number, no KYC. Install the binary and generate a wallet — that's it.
2. **Built-in exchange aggregation**: Exodus integrates with ChangeNOW and other no-KYC swap services. BTC received can be swapped to XMR (Monero) inside the wallet UI in <2 minutes.
3. **Cross-platform + headless-ready**: Available on Windows, macOS, Linux, iOS, Android. Can be run headless via CLI for automated cashout workflows (unattended batch processing of multiple logs).

## The "Exodus Stealer" Variant (Complementary Attack)

There is a distinct malware family called **Exodus Stealer** (also tracked as ExoTickler) that targets this ecosystem from the opposite direction:

- The malware scans the infected machine for an existing Exodus wallet installation
- It **replaces** the legitimate Exodus binary with a trojanized version
- When the victim opens their wallet and enters their seed phrase to unlock it, the trojan captures the seed and exfiltrates it via Discord webhook or Telegram bot
- The attacker imports the seed phrase into their own Exodus instance and drains every asset
- If the victim has BofA logged in AND Exodus installed, the attacker can drain both simultaneously

Kaspersky documented this specific delivery mechanism (January 2024): fake macOS app "activators" for cracked Adobe/Final Cut Pro installers that fetched malicious payload from DNS TXT records. The backdoor replaced Exodus and Bitcoin wallet binaries with trojanized versions.

## Detection & Countermeasures

### For Banks
- **Bind session cookies to IP address** — reject sessions from IPs that differ from the initial login
- **Rotate session tokens periodically** — every 15-30 minutes, issue a new cookie and invalidate the old one
- **Require re-authentication for high-value actions** — crypto purchase, ACH setup, external transfer should trigger a fresh MFA prompt
- **Device fingerprint mid-session checks** — verify TLS fingerprint, screen resolution, timezone against the established session profile
- **Alert on first-time crypto purchases** — flag BTC purchases from accounts with no crypto history

### For End Users
- **Use a password manager** — don't save bank passwords in browser autofill (reduces credential exposure but doesn't prevent cookie theft)
- **Log out of banking sessions** when done (invalidate the cookie)
- **Use session-specific browsers** — a dedicated browser or browser profile only for banking, never for downloads
- **Don't download cracked software** — this is the primary infection vector
- **Use a hardware wallet** (Ledger, Trezor) instead of software wallets like Exodus for significant holdings
- **Check bank statements daily** for small crypto purchases you didn't make

### For Security Teams
- Monitor stealer log marketplaces (Telegram channels, Russian Market) for your domain's credentials
- Use services like Hudson Rock, SpyCloud, or Flare.io for continuous domain monitoring
- Enforce FIDO2/WebAuthn hardware-bound credentials — phishing-resistant MFA still protects against fresh login attempts (but not against active session replay)
- Implement conditional access policies that check device posture before granting access to financial portals

## Source Reliability Notes

| Source | Type | Reliability | Key Coverage |
|--------|------|-------------|--------------|
| ransomnews.com | Threat intel journalism | High | MaaS pricing, log market structure, session cookie value chain |
| Kaspersky Securelist | Vendor threat research | High | Exodus Stealer DNS-based delivery mechanism |
| Flare.io | Commercial threat intel | High | Stealer log market analysis |
| SOCRadar | Vendor threat research | Medium-High | Infostealer landscape, log market pricing |
| KELA | Commercial threat intel | High | MaaS pricing baseline ($200/mo average) |
| Microsoft Threat Intelligence | Vendor/LE | High | Lumma infrastructure takedown (May 2024) |
| Dutch National Police (Operation Magnus) | Law enforcement | High | RedLine takedown, published source code and customer lists |

## Intelligence Gaps

1. **Current BofA session cookie format** — cookie names and values may have changed since this research
2. **Which antidetect browsers evade BofA's session fingerprinting** — the attacker needs residential IP matching the victim's metro area
3. **NYDIG purchase limits per transaction** — exact daily/weekly caps for crypto purchases via BofA
4. **Effectiveness of BofA's cross-session anomaly detection** — how many transactions before the bank's fraud model catches cookie replay behavior
5. **Market price for "BofA VIP" logs** — what premium do filtered logs with confirmed BofA session cookies command on Telegram channels
