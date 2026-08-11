"""Hardened Esplora (mempool.space) client — pure stdlib, verified July 2026.

Handles: bare plain-text /block-height responses, /txs/chain/ pagination, aggressive
rate limiting (retry + backoff), corrupt-cache self-heal. Copy standalone or point
sys.path at the toolkit version.

Usage:
    from esplora_client import address_info, address_txs, tx, block_height
    # address_txs walks backward: pass last txid of previous page
"""
import json, time, urllib.request, os, hashlib

BASE = os.environ.get("ESPLORA_BASE", "https://mempool.space/api")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")


def _get(path, cache_ttl=300):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha1(path.encode()).hexdigest()[:16]
    cf = os.path.join(CACHE, key + ".json")
    if os.path.exists(cf) and time.time() - os.path.getmtime(cf) < cache_ttl:
        try:
            return json.load(open(cf))
        except Exception:
            os.remove(cf)  # self-heal corrupt cache
    last = None
    for a in range(6):
        try:
            req = urllib.request.Request(BASE + path, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) forensics/0.1",
                "Accept": "application/json"})
            raw = urllib.request.urlopen(req, timeout=30).read()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                # /block-height/:h returns a BARE 64-hex hash, not JSON
                s = raw.decode("utf-8", "replace").strip()
                if len(s) == 64 and all(c in "0123456789abcdefABCDEF" for c in s):
                    data = s
                elif s.isdigit():
                    data = int(s)
                else:
                    raise
            json.dump(data, open(cf, "w"))
            return data
        except json.JSONDecodeError as e:
            last = RuntimeError(f"non-JSON response for {path}: {e}")
            time.sleep(3 * (a + 1))
        except Exception as e:
            last = e
            time.sleep(2 * (a + 1))
    raise RuntimeError(f"esplora failed: {path} -> {last}")


def address_info(addr): return _get(f"/address/{addr}")
def address_txs(addr, last_seen_txid=None):
    # NOTE: /address/:addr/txs/:txid 404s on mempool.space; /txs/chain/ is the pager
    p = f"/{last_seen_txid}" if last_seen_txid else ""
    return _get(f"/address/{addr}/txs/chain{p}" if last_seen_txid else f"/address/{addr}/txs")
def address_utxo(addr): return _get(f"/address/{addr}/utxo")
def block_height(h): return _get(f"/block-height/{h}")
def block_txs(hash_, idx=0): return _get(f"/block/{hash_}/txs/{idx}")
def tx(txid): return _get(f"/tx/{txid}", cache_ttl=86400)


def walk_address_txs(addr, max_pages=30, progress=None):
    """All txs for an address (newest first). Returns list. Resumable-friendly."""
    out, anchor = [], None
    for p in range(max_pages):
        txs = address_txs(addr, anchor)
        if not isinstance(txs, list) or not txs:
            break
        out.extend(txs)
        if progress: progress(p, txs)
        if len(txs) < 50 or len(out) >= 600:
            break
        anchor = txs[-1]["txid"]
    return out
