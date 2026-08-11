# Transcript Analysis: "Tricking Banks" — Guest Exo (2026)

**Source:** YouTube — "Tricking Banks Season 2" (BMG Kappo channel)
**Guest:** Exo — Bay Area (North Cal), under 18, self-taught online
**Reliability:** Medium-High — first-hand practitioner, specific tactical details, but some narrative inflation expected (interview setting)
**Date:** Early-to-mid 2026

## Methods Extracted (10 total)

### 1. Carding / Punching (Online CC Fraud)

**Core Principle:** Make the transaction look exactly like the cardholder — fraud score, proxy, user-agent, spending patterns.

**Key Details:**
- Residential proxies from premox.com ($0.35 each, ~90min lifetime)
- Check fraud score on whoer.net and scamalytics before every play
- Match user-agent (iPhone→Safari, Android→Chrome) to cardholder
- Anti-detect browsers to spoof device type
- "Stalk" victim's social media to match spending patterns (stores, gas stations)
- Build card with small transactions first, then escalate
- Cards have "algorithms" — declined at unfamiliar stores may work online

**Guest's Status:** Mostly stopped pure punching. Now only uses cards in combination with profile work.

**Where Discussed:** Telegram (guest's username: Punching), Tricking Banks YouTube

### 2. Fullz Profile / Identity Takeover (Main Method)

**Core Principle:** Obtain a full identity (ID + SSN), add your phone to their credit report, bypass KYC with face-swapped ID photos, open accounts at banks they don't use.

**Key Details:**

**Step 1 — Acquire Profile:**
- Buy from markets (Doc Shop — URL currently down)
- Or farm via rental application phishing site (his homegirl built it)
- People search services for SSN/DOB

**Step 2 — Add Phone to Credit Report (CRITICAL):**
- Method A: Apply for 3-4 credit cards (Discover, Capital One) with the new phone number → auto-added next day
- Method B: Open TransUnion/Equifax/Experian account → file a dispute → call from that phone number in 3 days
- Can also add a drop address or PO box as billing address

**Step 3 — Clean Workspace:**
- Good residential proxy matching victim's location
- Moto G Play 2024 ($150 from Best Buy)
- Mint Mobile 7-day trial SIM ($2) — enough time for profile work
- New device, new SIM, clean browser fingerprint

**Step 4 — KYC / ID Verification Bypass (Key Innovation):**
- Get victim's ID (front+back photos)
- Go to post office → get passport photo taken ($10) — professional camera, good lighting
- Photoshop the passport photo face onto victim's ID
- Print on A4 plain paper (not cardstock, not plastic)
- Scan front and back — the biometric scan checks that the face on the ID matches the live person scanning
- **Works across race/age/gender**: "80-year-old white woman with a 20-year-old black dude's face — wouldn't even matter"
- Works if victim hasn't used their ID for KYC in last 30 days (no cached facial data in bank systems)

**Step 5 — Open Accounts:**
- Check credit report first — see what banks victim already uses
- Target banks victim does NOT have: Chime, Ally, Netspend, Go-To Bank, Alliance Credit Union
- Open multiple checking accounts (3+) — some may auto-close, use the ones that survive
- Wait a few days, verify accounts don't disappear

**Step 6 — Get Loans:**
- High credit score (700+): SoFi, Avant, big lenders — reason: "personal purchase" or "large personal purchase"
- Low credit score (550+): Avant — reason: "medical emergency" or "hardship"
- Submit fake bank statements/paystubs if needed (especially SoFi)
- Try connecting via Plaid first (normal way). If fails, call/chat support
- Deposit loan proceeds directly to crypto (from drop account → crypto exchange)

**Tools/Infrastructure:**
- premox.com residential proxies
- Photoshop (or equivalent) for ID editing
- Printer (A4 paper)
- Mint Mobile $2 trial SIMs
- Moto G Play 2024 work phone
- Credit bureau accounts (TransUnion, Equifax, Experian)
- Plaid verification

**Risks:**
- Victim notices new accounts on credit report and freezes credit → profile burned
- Accounts can auto-close for no apparent reason
- Victim may have existing accounts at target bank → can't open new ones

### 3. Check Fraud (Mobile Deposit)

**Core Principle:** Cook own checks (never touch physical ATM), get routing+account numbers by combining bank statement partial info with credit report data, deposit via mobile app.

**Key Details:**
- Never dropped a check at ATM — only mobile deposit
- Only had one clip ever
- **Account number assembly:** Bank statements show last 4 digits → credit report shows all but last 4 → combine for full account number
- Check number: random numbers or blank — "it just goes through"
- Netspend "Money in Minutes" feature: pay a small fee for instant clearing (instead of 10-day hold)
- Uses Netspend virtual debit for one profile specifically

### 4. Phone Financing (iPhones)

**Two Approaches:**

**In-Store (with runner):**
- Fake physical ID (actual fake ID, not printed paper)
- Target different carrier than victim's current one
- Runner must memorize all victim details — don't read off ID
- Target young/inexperienced store employees (college-aged, female = easiest)
- Pay initial deposit in cash
- Pick up: show ID briefly to delivery driver, grab package

**Online:**
- Same as profile work — good proxy, act like victim
- Order online, intercept package at delivery address

**Tools:** Fake ID, cash for deposit, runner

### 5. CPNs (Credit Profile Numbers / Synthetic Credit)

**Core Principle:** Build synthetic credit profiles from scratch, use authorized user trade lines to boost credit across multiple CPNs simultaneously.

**Key Details:**
- Still viable in 2026 (according to guest)
- "Greener" than profiles — no real victim to notice
- But more work — requires building over months (vs profiles: open, loan, run)
- Strategy: Multiple CPNs + AU trade lines → boost each other
- Build credit over months → take loan → abandon (burn) the CPN
- Guest's recent CPN: Jan-Mar 2026 building

**Guest's Preference:** Profiles for speed, acknowledges CPNs are safer long-term

### 6. Rental Application Phishing Farm

**Core Principle:** Create a fake "free rental application" website to harvest fullz (SSN, ID, bank statements, employment history).

**Key Details:**
- His girlfriend/homegirl built the website (she doesn't code either — got the idea from finding a real phishing site)
- Market as "free application" — no $200 fee (unlike legitimate apps)
- Victims freely submit everything: SSN, photo ID, bank statements, paystubs
- Property type determines quality of victims:
  - High-rise in Manhattan → high credit score victims
  - Section 8 / low-income → lower credit scores
- "They have no idea they got fished"

### 7. SIM Swapping

**Key Details:**
- **Verizon hardest**: They have AI that blocks spoofed caller ID — if you spoof a Verizon number calling a Verizon line, the call gets blacklisted
- **T-Mobile easiest**: Multiple witnesses confirm
- **War story**: $300M crypto target — team spent a month, got account number and PIN reset via social engineering (southern white man accent on phone for 5 hours), but the wife's phone OTP stopped them — wife's line was the only other number on the account. His homegirl was on the phone with the wife pretending to be Verizon support when the husband walked in.
- Requires spoofing caller ID carefully

### 8. Account Takeovers (ATOs)

- Distinguished from punching — full login access to victim's existing accounts
- Guest considers this a "completely different thing"

### 9. Stripe Invoicing Cash-Out

- Creates verified Stripe accounts under profiles
- Sends invoices → pays out to drop account
- Can cash out other people's cards through his Stripe accounts (offering this as a service)

### 10. Document Cooking (Service)

- Makes: fake bank statements, paystubs, W2s, W9s, 1040s
- Sells them (hasn't set pricing yet, only made for himself until now)
- Background: Former graphic designer for a clothing brand agency — "raw with the cooks"

## Community Intelligence

| Vector | Details |
|--------|---------|
| **Telegram** | Primary hub. Guest handle: Punching. Channel: Tricking Banks group chat ($30-day free, then monthly fee). Bot escrow for transactions. Toncoin for instant payments. |
| **YouTube** | "Tricking Banks" channel (BMG Kappo). 18K subs. Interview-style "educational purposes" content. |
| **Markets** | Doc Shop (currently down, new URL unknown). premox.com for proxies. |
| **Phone Carriers** | Verizon hardest to social engineer, T-Mobile easiest |
| **Geographic** | Bay Area (North Cal) — emphasis on street theft culture ("Bip City"), but guest is online-only, not "from the trenches" |

## Tools & Infrastructure Map

| Tool | Purpose | Price/Access | Source |
|------|---------|-------------|--------|
| premox.com | Residential proxies | $0.35/ea, ~90min lifetime | Guest |
| whoer.net | Fraud score check | Free | Guest |
| scamalytics.com | Fraud score check | Free | Guest |
| Mint Mobile trial SIMs | Clean phone numbers | $2/7 days | Guest |
| Moto G Play 2024 | Work device | $150 (Best Buy) | Guest |
| Photoshop | ID photo editing | Subscription | Guest |
| Doc Shop | Profile market | Per-item (URL down) | Guest |
| Stripe | Card cash-out | Free to create | Guest |
| Avant (loans) | Loan for 550+ credit | "Medical emergency" story | Guest |
| SoFi (loans) | Loan for 700+ credit | Accepts fake docs | Guest |
| Netspend | Mobile check deposit | "Money in Minutes" feature | Guest |
| Plaid | Bank verification | Free | Guest |

## Key Quotes / Mindset

- "You really have to be on 10 at all times — move in the shadows"
- "Keep your profiles clean and don't burn them — that shit hurts"
- "Trial and error is the best teacher"
- "With $200 you could really work a profile"
- "You can't give up — that shit will pay off"
- "Consistency is everything"

## Intelligence Gaps

1. **Where to buy profiles now** — Doc Shop is down, what are current active markets?
2. **Stripe verification details** — How exactly does he create verified Stripe accounts? What documents pass Stripe's KYC?
3. **Phone financing specifics** — Which carriers? Current initial deposit amounts? Which phone models most commonly financed?
4. **Check cooking frequency** — How many checks before a profile's account gets flagged?
5. **Cryptocurrency cash-out** — Which exchanges? How does he avoid AML flags on loan proceeds?
6. **Authorized user trade lines** — Who provides these? Which CPN vendors are reliable?
7. **Rental application panel** — What platform/framework did she build it on?
