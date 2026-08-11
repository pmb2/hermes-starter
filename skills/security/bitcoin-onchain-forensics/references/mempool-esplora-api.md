# mempool.space / Esplora API field notes (verified July 2026)

All endpoints under `https://mempool.space/api`. blockstream.info/api is a compatible
esplora host but differs in pagination semantics — pick ONE host per investigation.

## Verified quirks (each one broke a run this session)

1. **`/block-height/:height` returns BARE PLAIN TEXT** — `<discord-channel-id>1...` with NO
   JSON quotes. `json.loads` fails: `JSONDecodeError: Extra data: line 1 column 2 (char 1)`.
   Fix: try `json.loads`, on failure accept a stripped 64-hex string (or int if all digits).
   This error is NOT a rate limit and NOT a corrupt cache — it's the response format.

2. **`/address/:addr/txs/:last_seen_txid` → HTTP 404** on mempool.space. The working
   paginator is **`/address/:addr/txs/chain/:last_seen_txid`** (pass the LAST txid of the
   previous page; page size 25, newest-first ordering). Base `/txs` returns **50** txs.
   Note: blockstream.info's `/txs/chain/:txid` walks the OTHER direction (anchor onward) —
   verify direction empirically per host before looping.

3. **Funding txid is at the VIN level**: `vin[].txid` + `vin[].vout` identify the spent
   output. `vin[].prevout` contains ONLY the output fields (`scriptpubkey_address`, `value`,
   `scriptpubkey_type`, ...) — no txid inside. `prevout` can also be `null` or omit fields.

4. Blocks are huge (~5-6.6k txs). `GET /block/:hash/txs/:index` = 25/page offset pagination.
   NEVER enumerate whole blocks to find drain txs — paginate the collection ADDRESS's own
   tx list instead (~10 calls vs 1,000+).

5. Rate limiting is aggressive after ~50-100 rapid calls. Pattern that survived:
   retry with exponential backoff (up to 6 tries, sleep 2-18s), disk cache keyed by
   sha1(path), validate JSON BEFORE caching, self-heal corrupt cache files on read.

## Address stats fields (chain_stats)
- `funded_txo_sum` / `spent_txo_sum` (sats) → current balance = funded − spent
- `tx_count` — total txs touching the address. `tx_count == 2` = one deposit + one spend
  (textbook dormant victim profile)
- `funded_txo_count` / `spent_txo_count` → live UTXO count

## Tx JSON fields used in forensics
- `txid`, `status.block_height`, `status.block_time` (unix), `fee` (sats)
- `vin[].txid` (funding tx), `vin[].vout`, `vin[].prevout.scriptpubkey_address`, `vin[].prevout.value`
- `vin[].witness` — P2WPKH: `[der_sig_hex, pubkey_hex]`
- `vin[].scriptsig` — legacy P2PKH: `<der_sig> <pubkey>` (regex `[0-9a-fA-F]{40,}` to split)
- `vout[].scriptpubkey_address` — match against collection addresses

## Useful known-good client
See `scripts/esplora_client.py` (copy used in the July 2026 investigation; pure stdlib).
