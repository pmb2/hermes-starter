# bip_utils 2.x API + ECDSA DER signature parsing (verified with 2.12.1)

## bip_utils 2.12.x — level-based API (NOT the old Derive-chain)

Install: `uv venv .venv && uv pip install --python .venv/Scripts/python.exe bip_utils requests`
(Hermes venv has no pip on this box.)

### Gotchas that cost real time
1. **`Bip32Slip10Kdf` is NOT a top-level export** — `ImportError: cannot import name`.
2. **`DeriveDefaultPath()` returns ADDRESS depth** (m/84'/0'/0'/0/0) in 2.12.x. Calling
   `.Change()` on it raises `Bip44DepthError: Current depth (5) is not suitable for
   deriving change`.
3. **`Change()` takes a `Bip44Changes` enum, not an int** — `Change(0)` raises
   `TypeError: Change index is not an enumerative of Bip44Changes`.
4. `FromSeedAndPath(seed, "m/84'/0'/0'/0/0")` DOES work for direct key derivation.

### Working derivation pattern
```python
from bip_utils import (Bip39SeedGenerator, Bip39MnemonicGenerator, Bip44, Bip44Coins,
                       Bip49, Bip49Coins, Bip84, Bip84Coins,
                       Bip32Slip10Secp256k1, Bip44Changes)

def mnemonic_from_entropy(eb):          # deterministic 12-word mnemonic
    return Bip39MnemonicGenerator().FromEntropy(eb[:16].ljust(16, b"\x00"))

def addrs(cls, coins, seed, n):         # m/..'/0'/0'/0/i  (chain: 0 = external)
    acc = cls.FromSeed(seed, coins).Purpose().Coin().Account(0)
    chg = acc.Change(Bip44Changes.CHAIN_EXT)
    return [chg.AddressIndex(i).PublicKey().ToAddress() for i in range(n)]

def addresses_from_mnemonic(mnem, n=5):
    seed = Bip39SeedGenerator(mnem).Generate()
    return {"84": addrs(Bip84, Bip84Coins.BITCOIN, seed, n),
            "49": addrs(Bip49, Bip49Coins.BITCOIN, seed, n),
            "44": addrs(Bip44, Bip44Coins.BITCOIN, seed, n)}

def privkey_at_path(mnem, path="m/84'/0'/0'/0/0"):
    return Bip32Slip10Secp256k1.FromSeedAndPath(
        Bip39SeedGenerator(mnem).Generate(), path).PrivateKey().Raw().ToHex()
```
Verify output formats: 84 → `bc1q...`, 49 → `3...`, 44 → `1...`.

## ECDSA DER signature parsing (from Esplora tx JSON)

DER layout: `0x30 len 0x02 rlen r 0x02 slen s`. r/s can carry a leading `0x00` sign byte
(high bit set); strip it with `lstrip(b"\x00")`.

```python
def der_rs(der_hex):
    der = bytes.fromhex(der_hex)
    if not der or der[0] != 0x30: return None
    i = 2
    if der[1] & 0x80:              # long-form length (rare for sigs)
        i = 2 + (der[1] & 0x7f)
    if der[i] != 0x02: return None
    rl = der[i+1]; r = der[i+2:i+2+rl].lstrip(b"\x00"); i += 2 + rl
    if der[i] != 0x02: return None
    sl = der[i+1]; s = der[i+2:i+2+sl].lstrip(b"\x00")
    return r.hex(), s.hex()
```

Where to find sigs in Esplora JSON:
- P2WPKH (bc1q): `vin[].witness` = `[der_sig_hex, pubkey_hex]`
- Legacy (1...): `vin[].scriptsig` = `<der_sig> <pubkey>` — split with regex
  `[0-9a-fA-F]{40,}`

## Nonce-bias sanity math (R distribution)
Count leading zero nibbles of the parsed R hex:
- P(top NIBBLE == 0) = 1/16 ≈ 6.25% (94/1536 = 6.1% observed → uniform ✓)
- P(top BYTE == 0, i.e. R < 2^248 → 62-hex R) ≈ 1/256 (4/1536 observed ≈ expected 6 ✓)
- Any meaningful excess over these rates = weak nonce entropy → candidate for lattice
  key-recovery.
R-collision rule: same R in two sigs over different messages ⇒ both private keys
recoverable. Test across ALL txs a signer produced (sweep + consolidation + dust).
