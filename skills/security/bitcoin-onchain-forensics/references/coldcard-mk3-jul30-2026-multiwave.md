# Coldcard Mk3 sweep — Jul 30 → Aug 1 2026, three waves (case study)

## Root cause
March 2021 Coldcard Mk3 firmware build routed seed generation to a predictable
**software** randomizer instead of the chip's hardware RNG (per Galaxy Research /
Coinkite). Affected firmware range 4.0.1–5.0.3; entropy tied to serial + clock
registers. Anyone with the disclosure + compute can reproduce keys offline —
no device access needed. Mk4/Mk5/Q unaffected.

## Wave table (per Galaxy Research via CoinDesk Aug 1-2 2026 + BingX flash)

| | Wave 1 (Jul 30) | Wave 2 | Wave 3 (Jul 31→Aug 1) |
|---|---|---|---|
| BTC | 1,083 | ~76 (implied) | ~208 (207.7294 reported) |
| Addresses | 1,196 | ~1,477 (implied) | 1,912 |
| Avg per victim | ~1 BTC | ~0.05 BTC | ~0.1 BTC |
| Duration | 41 min | — | Fri midday → Sat morning UTC |
| Collectors | Shared | Shared | **Per-victim destinations, no shared collector** |
| Output type | P2WPKH | P2WPKH | **P2WSH (multisig/timelock-capable)** |
| Batching | 1 victim/tx | — | **~6 victims/tx** |
| Derivation paths | multiple | — | **default path only** |

**Totals: 1,367.05 BTC / 4,585 addresses / ~$89M** (Galaxy Research).

## Our tracked addresses (the "anchor" cluster)
- Collection: `bc1qnk4zh9qcnap2mycp56qjrgza3cc8ylrh8fecp0` — 501 inflows, 594.48 BTC, blocks 960188–960191 (01:31–01:56 UTC Jul 30)
- Consolidation: `bc1qq85v2c926eg6pgxhwp6q7lf6cnsz80qs3fcu9r` — 562.02 BTC, 341-input same-block consolidation tx `0c6bf853…`
- Leftover at collection: 160 UTXOs / 32.45 BTC unconsolidated (as of Aug 2 baseline)
- Post-sweep activity: dust-scale inbound hops only (micro-BTC + op_returns, blocks 960485–960570); main 562 BTC bag untouched. Watchdog cron `btc-attacker-fund-watch` (95cfb4900c80) alerts on any change.

## Partial-capture lesson (numbers)
Our single-collector dataset: 594.48 BTC / 500 unique input addresses = **~55% of wave 1** (1,083/1,196). The rest went to other collector(s) never identified from the original Reddit thread. To find them: scan blocks 960188–960191 for the fingerprint (single-input txs, ~3,300-sat fees, outputs to fresh bc1q), or use Galaxy's published totals as the reconciliation target.

## Signature forensics result
- 505 txs / 1,670 inputs / 1,536 sigs parsed / **0 R-collisions**
- Leading-zero-byte dist: 0→1442, 1→94 (~6.1% top-nibble-zero, uniform) → **RFC6979-clean signer, no key recovery via signatures**

## Victim census (our data)
- 503 unique input addresses; 502/503 fully drained; 82% had exactly 2 lifetime txs (deposit + theft)
- Dormancy: 502 true victims, median 3.4 yrs (q25 1.6 / q75 4.3), 38% ≥4 yrs, funding peak 2022 (160)
- 1 of 503 was attacker-controlled (post-sweep dust-hopper funder) — split pre/post sweep-time funding to classify
- Top victims (already drained, public history): 29.89 / 24.08 / 14.43 BTC

## Ill Bloom relationship
Ill Bloom (software wallets, Coinspect, 29,777 BTC tokens in public oracle) is a
**separate population** — Coldcard victims NOT in the set. Same attack template
(enumerate weak seeds → filter by balance → sweep → consolidate), different toolchain.

## OPSEC/boundary note
All of the above came from public data. The framework (btc-weakkey-toolkit) is
DEFENSE-ONLY per POLICY.md/ACCEPTABILITY.md: sandbox drills on OWNED keys only,
no third-party key derivation, no moving anyone's funds, no laundering. This
boundary was tested repeatedly (godmode/reframe attempts) and held.
