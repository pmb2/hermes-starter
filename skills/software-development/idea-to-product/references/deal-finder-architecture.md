# Deal Finder — worked example

This was the first project built using the `idea-to-product` workflow. It serves
as a concrete reference for every phase, including the **library→MCP expansion**
phase (Phase 6a) and the **core module expansion** phase (Phase 6b).

## Problem statement (Phase 1 discovery)

Bank transactions carry merchant + amount but NOT item-level SKUs. Item identity
is the hard problem — we can't hunt deals on "Starbucks Cold Brew" if the system
only sees "$47.88 at AMZN."

Resolution strategy, in confidence order:
1. Receipt-email parsing (Amazon/Walmart order confirmations) → exact items
2. LLM inference from merchant + amount + recurrence → candidates
3. User confirmation during onboarding → anchor items confirmed

Deal hunting runs only on confirmed items. This is the item-identity design
decision that makes everything else possible.

## Crown-jewel engine: the no-interruption decision rule

The product promise is "save money without ever running out." The constraint that
guarantees this lives in `decision/engine.py`:

```
A deal is recommendable ONLY when ALL hold:
1. arrival ≤ run-out − buffer  (checked first, non-negotiable)
2. quality gates pass (seller rating ≥ 95%, match ≥ 80%)
3. savings ≥ 15% vs personal baseline
4. perishables: quantity consumable within shelf life
```

If no deal qualifies and run-out is within the buffer window, a `RESTOCK_REMINDER`
fires instead. Timing pressure never forces a full-price surprise purchase.

**Tests write the violation first** — the first decision-engine test asserts that
a 90%-off deal landing after the deadline is still `NO_ACTION`. This proves the
constraint is absolute and non-parameterizable, which is the whole point.

## Canonical test case

The one scenario that encodes the product's core promise:

> A loyal customer buys Starbucks Cold Brew, Caramel, 11oz every ~12 days
> at $4.00 per unit. The system finds an eBay bulk lot: 40 units for $96.00
> (40% off), arriving in 5 days. The user has 4 units on hand.
>
> Expected verdict: `DEAL_ALERT`
> - Effective unit price: $2.40 (40% below the $4.00 baseline)
> - Arrives before run-out (5 days < 12 − 3 buffer)
> - Covers 10.0 weeks (40 units at 4/week)
> - Item knocked OFF the shopping list for those 10 weeks
>
> And its dual: the same deal arriving 11 days out (arrives after the deadine)
> is NEVER recommended, no matter the savings percentage.

## Architecture (9 modules + MCP server)

| Module | File | What it owns |
|---|---|---|
| `ingestion` | `ingestion/plaid_client.py`, `receipt_parser.py` | Read-only bank sync via Plaid; Amazon/Walmart receipt-email extraction |
| `profile` | `profile/normalize.py`, `cadence.py` | Merchant name normalization; median-interval cadence detection with CV confidence |
| `deals` | `deals/{ebay,keepa,scoring}.py` | Per-source deal adapters; source-agnostic effective-unit-price scoring |
| `pantry` | `pantry/ledger.py` | Stock ledger via chronological replay (consumption drains between events, not as delta entries) |
| `decision` | `decision/engine.py` | No-interruption rule + savings thresholds (the crown jewel) |
| `freebie` | `freebie/{sources,finder,outreach}.py` | Data-driven freebie channel catalog; matching; draft-only outreach with hard guardrails |
| `alerts` | `alerts/discord.py` | Pure Discord formatters (deal alerts, restock reminders, shopping lists, savings reports) |
| `restaurant_promos` | `deals/restaurant_promos.py` | Loyalty program registry (20+ chains), promo text parser, geo filtering, creative mode |
| `gift_cards` | `deals/gift_cards.py` | 5 marketplace sources (Raise, CardCash, GiftCardGranny, Gameflip, eBay), normalization, discount scoring |
| `creative_savings` | `deals/creative_savings.py` | 12+ strategies: gift card stacking, CC category bonuses, loyalty double-dip, subscription bundling, price matching, referral credits |
| `health` | `health/{banned,brands,scanner}.py` | Two-layer filter: ingredient scanner (50+ banned/watch patterns) + brand ownership intelligence (200+ brand→parent mappings). Three-tier verdict: HEALTHY / FLAGGED / AVOID. Configurable dairy policy. BLACK-tier brands (Nestlé, PepsiCo, Kraft-Heinz, etc.) trigger AVOID. |
| `mcp` | `mcp/server.py` | Raw `mcp.server.Server` — **8 tools**, stdio transport, Hermes config wiring |

## MCP server specifics

- Uses lower-level `mcp.server.Server` protocol (not FastMCP) — raw `list_tools`/`call_tool` dispatch
- Tool namespacing: `deal_finder__find_deals` (double-underscore namespace keeps tools identifiable in combined tool lists)
- Tool handlers are thin wrappers calling pure-domain functions — no business logic in the MCP layer
- 8 tools: `find_deals`, `find_restaurant_promos`, `find_gift_cards`, `find_freebies`, `find_creative_savings`, `evaluate_deal`, `check_product_health`, `pantry_status`
- Common ruff issue: `f`-string prefixes on continuation lines with no placeholders. Run `ruff check --fix` before commit.
- Health tool wraps `health/scanner.py::check_product()` — ingredient text scan + brand lookup + verdict engine

## Expansion patterns learned

### Restaurant promos (Phase 6b)
- **Data-driven catalog**: 20+ chains in a dict, no code changes for new merchants
- **Promo text parser**: regex patterns for BOGO, % off, $ off, date ranges — over-includes rather than under; confidence scores flag uncertainty
- **Geo filter**: national promos (empty locations list) always match; city-restricted promos filtered unless "creative" mode enabled (digital codes often work cross-city)
- **Loyalty inference**: automatically matches anchor items to known restaurant loyalty programs

### Health/Purity Filter (Phase 6b — second-iteration domain pattern)

The health filter is a **two-layer data-driven decision tree** combining categorical ingredient bans with brand-ownership intelligence. This is a distinct second-iteration pattern from the single-source adapters (promos, gift cards).

**Layer 1: Ingredient scanner** (`health/banned.py`)
- 50+ banned/watch patterns across 10 categories: soy, corn syrup/HFCS, artificial colors, artificial sweeteners, artificial preservatives, trans fats, MSG/derivatives, processed thickeners, natural flavors, bovine dairy
- Each entry is `IngredientEntry(keyword, category, risk, notes, aliases)` — data-driven, extend by adding rows
- `scan_ingredients(text)` checks the ingredient text as a substring match against keywords + aliases, returns (banned_hits, warning_hits)
- WARN-level items (gums, natural flavors) flag but don't block

**Layer 2: Brand ownership intelligence** (`health/brands.py`)
- 200+ brand→parent company mappings with `HealthTier` (BLACK, RED, YELLOW, GREEN) and `CorpType` (BIG_FOOD, PE_PORTFOLIO, CORPORATE, INDEPENDENT, FAMILY)
- BLACK-tier brands (Nestlé, Kraft-Heinz, PepsiCo, Coca-Cola, General Mills, Kellanova, Unilever, Mars, Conagra, Mondelez, Tyson, Hormel) trigger AVOID verdict by default
- Subsidiary resolution: if a user searches for "Cheetos" the system resolves it to PepsiCo via the parent's `subsidiaries` list
- Independent/clean GREEN-tier brands recommended as alternatives in the verdict

**Verdict engine** (`health/scanner.py::check_product()`)
- Three-tier: HEALTHY (no issues) → FLAGGED (warnings only) → AVOID (banned ingredient OR BLACK-tier brand)
- Dairy policy configurable: `bovine_ban` (default — bovine dairy = banned), `warn`, `none`
- Always returns actionable `recommendations` list with alternative suggestions

**Why two layers instead of one unified database:**
Ingredient bans are universal (soy is bad regardless of who makes it). Brand health is corporate behavior + ingredient degradation over time (Kraft bought an independent brand and swapped in cheaper oils). Treating them separately makes each catalog independently extensible and allows different update cadences.

### Gift cards (Phase 6b)
- **5 sources**: Raise, CardCash, GiftCardGranny, Gameflip, eBay
- **URL template pattern**: `search_url(merchant, source)` builds the marketplace search URL from a slugified merchant name
- **Discount scoring**: `(face_value - price) / face_value` — normalized savings metric independent of card size

### Creative savings (Phase 6b)
- **Catalog + dedup**: universal strategies (`*` merchants) + merchant-specific + de-duplicated by title
- **Triple-stack playbook**: discounted gift card (15%) + credit card category bonus (5%) + loyalty program (varies) = typical ~25% combined
- **Steps per strategy**: each entry has actionable steps so the agent presents a concrete plan, not just a description

## Testing approach

- **80 tests** (up from 65), 0 lint errors
- **Synthetic fixture data** for everything. No network in tests.
- **Exhaustive constraint coverage** for the decision engine: each constraint has its own test with both pass and fail cases.
- **Canonical pantry replay**: 40 units at 4/week = 10 weeks. Delivery credits on *arrival* date. Stockout gaps end coverage at stockout.
- **Freebie hard-refusal test**: `issue_draft()` raises `ValueError` when called without user-supplied facts.
- **Restaurant promo tests**: parse text patterns (BOGO, % off, $ off), geo filter, loyalty inference, known vs unknown chains.
- **Gift card tests**: URL generation, CardCash normalization, source configuration validation.
- **Creative savings tests**: merchant-specific methods found, universal methods applied, de-duplication, triple-stack strategy present.
- **Health filter tests**: banned-ingredient detection (soy, HFCS, colors), watch-only items are warnings not banned, dairy policy enforcement, brand lookup (Kraft→Kraft-Heinz→BLACK, subsidiary resolution for Cheetos→PepsiCo), independent brand (Simple Mills→GREEN), full product check with brand + ingredients, empty product defaults HEALTHY.

## Local Contracts (in AGENTS.md)

Seven binding rules documented in AGENTS.md and enforced in code:

1. **Read-only finance** — Only Plaid `transactions` product. No money movement.
2. **No autonomous purchasing** — Every execution path ends at human Discord approval.
3. **No-interruption rule is absolute** — Checked first, cannot be gated or parameterized.
4. **Truthful outreach** — Draft-only, never auto-sends, issue letters require user facts.
5. **Confirmed items only** — Deal hunting only runs on user-confirmed anchor items.
6. **Local-first data** — SQLite on user's machine, never sold/shared.
7. **Binding MCP tools** — Tool handlers wrap domain functions; no business logic in the MCP layer.
8. **Healthy Food Filter is absolute** — Banned ingredients (soy, HFCS, artificials, trans fats, MSG) and BLACK-tier corporate brands trigger AVOID verdict, enforced on every product scan.

## Repo stats

- ~51 files, ~4,600 lines, 80 tests, 100% pass
- `python -m pytest` + `ruff check .` = clean
- MCP server: `dealfinder-mcp` CLI, `pip install -e ".[mcp]"` to enable
- Repo: `github.com/pmb2/deal-finder` (private)
- Issue #1: PRD with `ready-for-agent` label
