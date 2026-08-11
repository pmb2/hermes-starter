# Supplement Research Database (Updated July 2026)

Condensed pricing, brand intel, and supplier data from the operator's stack build (v3 dual-tier).

## Alibaba Bulk Pricing Reference

| Supplement | Alibaba $/kg | Domestic $/kg | Premium $/unit/mo |
|---|---|---|---|
| NMN (99%) | $85-100 | $500-1000 | ~$72/mo (ND enteric tabs) |
| Glycine (food grade) | $2-5 | $8-15 | ~$30/mo (ND caps, 6/day) |
| NAC (99%) | $12-20 | $25-40 | ~$13/mo (ND caps) |
| CoQ10 (Ubiquinone) | $50-100 | $200-400 | ~$30/mo (Thorne caps) |
| Berberine HCL (98%) | $80-90 | $200-500 | ~$30/mo (Thorne caps) |
| Beta-Alanine | $3-8 | $10-20 | ~$21/mo (NOW caps, high dose) |
| Citrulline Malate (2:1) | $10-16 | $20-35 | ~$24/mo (ND caps, high dose) |
| L-Theanine (99%) | $15-25 | $40-60 | ~$5/mo (caps) |
| Creatine Monohydrate | $3-8 | $10-25 | ~$15/mo (Thorne powder) |
| Collagen Peptides | $8-15 | $18-30 | ~$28/mo (Vital Proteins) |
| Astragaloside IV (10%) | $80-150 | $250-500 | ~$40/mo (ND caps) |
| Sea Moss | N/A (gel/caps) | $15-50 | ~$50/mo (Elm & Rye caps) |
| Chlorophyll | $10-20 | $10-30 | ~$3/mo (NOW caps) |

## Dual-Tier Cost Comparison (v3, July 2026)

| Tier | Core/mo | + Training/mo | Annual (core+buf) |
|---|---|---|---|
| **Premium NSF/GMP** (Thorne, ND, LE) | ~$374 | ~$447 | ~$4,935 |
| **the operator Hybrid** (prem + budget mix) | ~$235 | ~$307 | ~$4,057 |
| **Budget GMP** (NOW, BulkSupplements) | ~$134 | ~$145 | ~$1,775 |
| **Alibaba Bulk** (raw powder) | ~$31 | ~$34 | ~$409 |

**Hybrid rules:** Premium for Creatine, Omega-3, Resveratrol, NMN, CoQ10, Berberine, Astragaloside IV, Mag Glycinate, Zennies. Budget GMP for Chlorophyll, Sea Moss, Glycine, NAC.

## Premium Capsule Brands (Top Tier)

| Brand | Best For | Cert Level | Price Tier |
|---|---|---|---|
| **Thorne** | Everything — medical-grade purity | 🧪 NSF Sport (most products) | $$$ |
| **Nootropics Depot** | Nootropics, single-ingredient purity | 🔬 HPLC every batch | $$ |
| **Life Extension** | Longevity formulations, resveratrol | 🏭 3P GMP | $$ |
| **NOW Foods** | Budget-friendly staples, simple molecules | 🏭 3P GMP | $ |
| **Elm & Rye** | Sea moss, whole-food supplements | 🔬 3rd party tested | $$ |

## Zennies Pouches (Daily Carry)

- Price: ~$7.50/can (15 pouches) = ~$0.50/pouch
- Contents: 50mg Caffeine, Alpha GPC, L-Theanine, L-Tyrosine, Lion's Mane, Cordyceps, Reishi, Taurine, Niacin
- Best buy: Walmart 2-pack ($14.99)
- Covers: nootropic/caffeine daily carry, replaces individual L-Theanine, Alpha GPC, Lion's Mane caps
- Monthly: ~$23 at 1.5 pouches/day

## Verification Script Pattern (Dual Tier)

```python
# Verify the dual-tier calculator
exec(open('scripts/cost-calculator.py').read())
assert len(tiers) == 15
pc = (pm - tp) * 30
bc = (bm - tb) * 30
ac = (am - ta) * 30
assert 300 < pc < 500    # premium core
assert 100 < bc < 200    # budget core
assert 20 < ac < 60      # alibaba core
assert 200 < hc < 400    # hybrid core
# tempfile -> run -> capture output -> os.unlink
```
